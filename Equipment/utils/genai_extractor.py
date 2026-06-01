"""
utils/genai_extractor.py -- Gemini-powered JSON extraction from raw scraped text
Uses the new `google-genai` SDK (google.genai)
Fixes:
 - Enforces valid JSON by parsing *inside* the tenacity retried function (guarantees retries on JSONDecodeError)
 - Uses Gemini's native Structured Output response_mime_type="application/json"
 - Proper exception handling for google.genai ClientError (rate limits)
 - Truncates input text to 6000 chars max
"""
import json
import re
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from config import GEMINI_API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)

# Delay between Gemini calls to avoid rate limiting (free tier = 15 RPM)
_CALL_DELAY = 2.0
# Max input chars sent to Gemini (keeps tokens low)
_MAX_INPUT_CHARS = 6000


# ── Pydantic Structured Output Schemas ─────────────────────────────────────

class ManufacturerSchema(BaseModel):
    name: str = Field(description="The formal brand/manufacturer name")
    country: Optional[str] = Field("", description="The country of headquarters, or empty if unknown")
    website: Optional[str] = Field("", description="The website homepage domain name only (e.g. atlascopco.com)")

class ModelSchema(BaseModel):
    model_name: str = Field(description="The model number or alphanumeric identifier")
    series: Optional[str] = Field("", description="The series/product lineage name (e.g. GA Series)")
    product_url: Optional[str] = Field("", description="The direct URL link to this model page if found")

class ManufacturerListSchema(BaseModel):
    manufacturers: List[ManufacturerSchema] = Field(description="List of discovered manufacturers")

class ModelListSchema(BaseModel):
    models: List[ModelSchema] = Field(description="List of discovered compressor models")

class TechnicalSpecsSchema(BaseModel):
    capacity_cfm: Optional[float] = Field(None, description="Flow capacity in Cubic Feet per Minute")
    capacity_m3_hr: Optional[float] = Field(None, description="Flow capacity in Cubic Meters per Hour")
    pressure_psi: Optional[float] = Field(None, description="Operating pressure in Pounds per Square Inch")
    pressure_bar: Optional[float] = Field(None, description="Operating pressure in bar")
    power_kw: Optional[float] = Field(None, description="Motor power rating in kilowatts")
    power_hp: Optional[float] = Field(None, description="Motor power rating in horsepower")
    motor_type: Optional[str] = Field(None, description="Type of motor (e.g. induction, PM, VSD, fixed speed)")
    motor_speed_rpm: Optional[float] = Field(None, description="Motor rotation speed in RPM")
    cooling_type: Optional[str] = Field(None, description="Cooling system (e.g. air-cooled, water-cooled)")
    lubrication_type: Optional[str] = Field(None, description="Lubrication classification (e.g. oil-free, oil-injected)")
    drive_type: Optional[str] = Field(None, description="Drive transmission mechanism (e.g. direct-drive, belt-drive, gear-drive)")
    stage_count: Optional[int] = Field(None, description="Number of compression stages")
    noise_level_db: Optional[float] = Field(None, description="Acoustic noise level rating in dB(A)")
    weight_kg: Optional[float] = Field(None, description="Net weight in kilograms")
    weight_lbs: Optional[float] = Field(None, description="Net weight in pounds")
    dimensions_mm: Optional[str] = Field(None, description="Outer measurements / dimensions format width x depth x height in mm")
    tank_size_liters: Optional[float] = Field(None, description="Receiver tank volume in liters")
    tank_size_gallons: Optional[float] = Field(None, description="Receiver tank volume in gallons")
    voltage: Optional[str] = Field(None, description="Electrical voltage level rating (e.g. 230V, 460V)")
    frequency_hz: Optional[float] = Field(None, description="AC grid frequency rating in Hz")
    phase: Optional[str] = Field(None, description="Electrical grid phase count (e.g. 3-phase, single-phase)")
    certifications: Optional[List[str]] = Field(None, description="List of engineering certifications (e.g. CE, UL, ISO)")
    warranty_years: Optional[float] = Field(None, description="Product warranty period in years")
    oil_capacity_liters: Optional[float] = Field(None, description="Internal lube fluid capacity in liters")
    outlet_size_inch: Optional[float] = Field(None, description="Discharge air outlet pipe dimension in inches")
    inlet_size_inch: Optional[float] = Field(None, description="Inlet air intake pipe dimension in inches")
    efficiency_percent: Optional[float] = Field(None, description="Energy or pump operating efficiency factor in percentage")
    operating_temp_min_c: Optional[float] = Field(None, description="Minimum allowed operating temperature limit in C")
    operating_temp_max_c: Optional[float] = Field(None, description="Maximum allowed operating temperature limit in C")
    duty_cycle: Optional[str] = Field(None, description="Continuous or intermittent operational duty cycle ratio limit")
    pump_life_hours: Optional[float] = Field(None, description="Design pump service life in operating hours")


def _clean_json(raw: str) -> str:
    """Strip markdown code fences if Gemini wraps output in ```json ... ```"""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _should_retry(exc: Exception) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, genai_errors.ClientError):
        msg = str(exc).lower()
        return any(k in msg for k in ["429", "rate", "quota", "resource_exhausted",
                                       "503", "500", "unavailable"])
    return isinstance(exc, (json.JSONDecodeError, TimeoutError))


@retry(
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=2, min=10, max=60),
    retry=retry_if_exception(_should_retry),
)
def generate_json(prompt: str, schema=None) -> dict | list:
    """Call Gemini with Pydantic response schema guidance, clean response, parse, and return."""
    time.sleep(_CALL_DELAY)  # polite rate-limit buffer
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        raw_text = response.text
        cleaned = _clean_json(raw_text)
        return json.loads(cleaned)
    except Exception as e:
        if isinstance(e, json.JSONDecodeError):
            print(f"  [Gemini JSON Error] Failed to parse JSON: {e}")
            print(f"  [Gemini Raw Text Debug]:\n{raw_text}\n-------------------")
        else:
            print(f"  [Gemini API Error] {type(e).__name__}: {e}")
        raise e


def _truncate(text: str) -> str:
    """Truncate input to safe length for Gemini."""
    return text[:_MAX_INPUT_CHARS]


def extract_manufacturers(compressor_type: str, subtypes: list, text: str) -> list[dict]:
    """
    Extract manufacturer list from scraped text using schema guides.
    """
    subtype_str = ", ".join(subtypes) if subtypes else "general"

    prompt = f"""You are a technical data extraction assistant.
From the scraped content below, extract up to 20 well-known manufacturers matching:
Compressor Type: {compressor_type}
Subtypes: {subtype_str}

Text:
{_truncate(text)}"""

    res = generate_json(prompt, schema=ManufacturerListSchema)
    return res.get("manufacturers", []) if isinstance(res, dict) else []


def extract_models(manufacturer: str, compressor_type: str, text: str) -> list[dict]:
    """
    Extract model list for a manufacturer from scraped text using schema guides.
    """
    prompt = f"""You are a technical data extraction assistant.
From the scraped content below, extract up to 10 actual product models made by {manufacturer}.
Compressor Type: {compressor_type}

Text:
{_truncate(text)}"""

    res = generate_json(prompt, schema=ModelListSchema)
    return res.get("models", []) if isinstance(res, dict) else []


def extract_attributes(
    manufacturer: str,
    model_name: str,
    compressor_type: str,
    text: str,
) -> dict:
    """
    Extract technical specs sheet dictionary from specifications text using schema guides.
    """
    prompt = f"""You are a technical specifications compiler.
From the specifications text below, extract ALL measurable mechanical, electrical, and physical specifications.

Manufacturer: {manufacturer}
Model: {model_name}
Compressor Type: {compressor_type}

Text:
{_truncate(text)}"""

    return generate_json(prompt, schema=TechnicalSpecsSchema)


def enrich_manufacturer_info(manufacturer: str, compressor_type: str) -> dict:
    """
    Ask Gemini directly (without scraping) to provide known manufacturer info.
    Used as a fallback when web scraping yields no results.
    """
    prompt = f"""Provide factual information about the compressor manufacturer: {manufacturer}
Compressor type context: {compressor_type}

Return ONLY a valid JSON object with these keys:
{{
  "name": "{manufacturer}",
  "country": "HQ country",
  "website": "domain only",
  "founded_year": number or null,
  "description": "1-2 sentence company description"
}}

JSON:"""

    return generate_json(prompt)


def embed_text(text: str) -> list[float] | None:
    """
    Generate a 768-dimensional vector embedding for the input text using Gemini's text-embedding-004.
    Used for semantic deduplication (RAG).
    """
    try:
        response = _client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embedding.values
    except Exception as e:
        print(f"  [Embedding Error] Failed to generate embedding: {e}")
        return None
