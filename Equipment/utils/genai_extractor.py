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
def generate_json(prompt: str) -> dict | list:
    """Call Gemini, clean the response, parse as JSON, and return."""
    time.sleep(_CALL_DELAY)  # polite rate-limit buffer
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
                response_mime_type="application/json",
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
    Extract manufacturer list from scraped text.
    Returns: [{"name": str, "country": str, "website": str}, ...]
    """
    subtype_str = ", ".join(subtypes) if subtypes else "general"

    prompt = f"""You are a data extraction assistant.
From the text below, extract a JSON array of compressor manufacturers.

Compressor Type: {compressor_type}
Subtypes: {subtype_str}

Rules:
- Return ONLY a valid JSON array of objects, no markdown fences or preambles.
- Each item must have exactly these keys: "name", "country", "website"
- "website" should be just the domain (e.g. "atlascopco.com"), or "" if unknown
- "country" should be the HQ country, or "" if unknown
- Include only real, well-known manufacturers -- no generic text
- Return at most 10 manufacturers

Text:
{_truncate(text)}

JSON array:"""

    return generate_json(prompt)


def extract_models(manufacturer: str, compressor_type: str, text: str) -> list[dict]:
    """
    Extract model list for a manufacturer from scraped text.
    Returns: [{"model_name": str, "series": str, "product_url": str}, ...]
    """
    prompt = f"""You are a data extraction assistant.
From the text below, extract a JSON array of compressor models made by {manufacturer}.

Compressor Type: {compressor_type}

Rules:
- Return ONLY a valid JSON array of objects, no markdown fences or preambles.
- Each item must have exactly these keys: "model_name", "series", "product_url"
- "series" is the product family/series name (e.g. "GA Series"), or "" if unknown
- "product_url" is the full URL to the product page, or "" if not found
- Include only actual model names/numbers -- not categories or marketing text
- Return at most 10 models

Text:
{_truncate(text)}

JSON array:"""

    return generate_json(prompt)


def extract_attributes(
    manufacturer: str,
    model_name: str,
    compressor_type: str,
    text: str,
) -> dict:
    """
    Extract full technical attributes from a product page.
    Returns a flat dict of attribute key -> value.
    """
    prompt = f"""You are a technical data extraction assistant.
Extract ALL technical specifications from the product page text below.

Manufacturer: {manufacturer}
Model: {model_name}
Compressor Type: {compressor_type}

Rules:
- Return ONLY a valid JSON object (not array), no markdown fences or preambles.
- Include every measurable attribute you can find. Common attributes include:
    capacity_cfm, capacity_m3_hr, pressure_psi, pressure_bar,
    power_kw, power_hp, motor_type, motor_speed_rpm,
    cooling_type, lubrication_type, drive_type, stage_count,
    noise_level_db, weight_kg, weight_lbs,
    dimensions_mm, tank_size_liters, tank_size_gallons,
    voltage, frequency_hz, phase,
    certifications, warranty_years, oil_capacity_liters,
    outlet_size_inch, inlet_size_inch, efficiency_percent,
    operating_temp_min_c, operating_temp_max_c,
    duty_cycle, pump_life_hours
- Use null for any attribute you cannot find
- Use numeric types for numbers (not strings)
- "certifications" should be a list of strings

Text:
{_truncate(text)}

JSON object:"""

    return generate_json(prompt)


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
