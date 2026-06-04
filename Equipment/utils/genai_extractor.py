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
import config

_client = None

def get_genai_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client

# Delay between Gemini calls to avoid rate limiting (free tier = 15 RPM)
_CALL_DELAY = 2.0
# Max input chars sent to Gemini (keeps tokens low)
_MAX_INPUT_CHARS = 6000


# ── Pydantic Structured Output Schemas ─────────────────────────────────────

class ManufacturerSchema(BaseModel):
    name: str = Field(description="The formal manufacturer name")
    country: str = Field("", description="The country of headquarters, or empty if unknown")
    website: str = Field("", description="The website homepage domain name only (e.g. atlascopco.com)")

class ModelSchema(BaseModel):
    model_name: str = Field(description="The model number or alphanumeric identifier")
    series: str = Field("", description="The series/product lineage name (e.g. GA Series)")
    product_url: str = Field("", description="The direct URL link to this model page if found")
    subtype: str = Field("", description="The classified equipment subtype/technology from the page text (e.g., Rotary Screw, Centrifugal, Scroll, Simplex, Duplex)")

class ManufacturerListSchema(BaseModel):
    manufacturers: List[ManufacturerSchema] = Field(description="List of discovered manufacturers")

class ModelListSchema(BaseModel):
    models: List[ModelSchema] = Field(description="List of discovered equipment models")

# ── Equipment-Class Technical Specifications Schemas ───────────────────────
# Each schema captures the attributes most relevant to that equipment master
# category. extract_attributes() selects the right schema at runtime via
# SPECS_SCHEMA_MAP so Gemini is guided toward the correct fields.

class CompressorTechnicalSpecsSchema(BaseModel):
    """Specification schema for Compressor equipment (air, gas, refrigeration, etc.)."""
    capacity_cfm: Optional[float] = Field(None, description="Free-air delivery / flow capacity in Cubic Feet per Minute")
    capacity_m3_hr: Optional[float] = Field(None, description="Free-air delivery / flow capacity in Cubic Meters per Hour")
    pressure_psi: Optional[float] = Field(None, description="Maximum working pressure in Pounds per Square Inch")
    pressure_bar: Optional[float] = Field(None, description="Maximum working pressure in bar")
    power_kw: Optional[float] = Field(None, description="Motor / shaft power rating in kilowatts")
    power_hp: Optional[float] = Field(None, description="Motor / shaft power rating in horsepower")
    motor_type: Optional[str] = Field(None, description="Type of motor (e.g. induction, PM, VSD, fixed speed)")
    motor_speed_rpm: Optional[float] = Field(None, description="Motor rotation speed in RPM")
    cooling_type: Optional[str] = Field(None, description="Cooling system (e.g. air-cooled, water-cooled, oil-cooled)")
    lubrication_type: Optional[str] = Field(None, description="Lubrication classification (e.g. oil-free, oil-injected, oil-flooded)")
    drive_type: Optional[str] = Field(None, description="Drive transmission mechanism (e.g. direct-drive, belt-drive, gear-drive)")
    stage_count: Optional[int] = Field(None, description="Number of compression stages (e.g. 1 = single-stage, 2 = two-stage)")
    noise_level_db: Optional[float] = Field(None, description="Acoustic noise level rating in dB(A)")
    weight_kg: Optional[float] = Field(None, description="Net weight in kilograms")
    weight_lbs: Optional[float] = Field(None, description="Net weight in pounds")
    dimensions_mm: Optional[str] = Field(None, description="Outer dimensions: Width x Depth x Height in mm")
    tank_size_liters: Optional[float] = Field(None, description="Integral receiver tank volume in liters")
    tank_size_gallons: Optional[float] = Field(None, description="Integral receiver tank volume in US gallons")
    voltage: Optional[str] = Field(None, description="Electrical supply voltage (e.g. 230V, 460V, 400V)")
    frequency_hz: Optional[float] = Field(None, description="AC grid frequency in Hz (e.g. 50 or 60)")
    phase: Optional[str] = Field(None, description="Electrical phase (e.g. single-phase, 3-phase)")
    certifications: Optional[List[str]] = Field(None, description="Engineering certifications (e.g. CE, UL, ISO 8573)")
    warranty_years: Optional[float] = Field(None, description="Product warranty in years")
    oil_capacity_liters: Optional[float] = Field(None, description="Internal lubrication oil capacity in liters")
    outlet_size_inch: Optional[float] = Field(None, description="Compressed air discharge outlet diameter in inches")
    inlet_size_inch: Optional[float] = Field(None, description="Air inlet diameter in inches")
    efficiency_percent: Optional[float] = Field(None, description="Specific energy or volumetric efficiency in percent")
    operating_temp_min_c: Optional[float] = Field(None, description="Minimum ambient / operating temperature in °C")
    operating_temp_max_c: Optional[float] = Field(None, description="Maximum ambient / operating temperature in °C")
    duty_cycle: Optional[str] = Field(None, description="Operational duty cycle (e.g. 100% continuous, 60% intermittent)")
    service_interval_hours: Optional[float] = Field(None, description="Recommended preventive maintenance interval in hours")


class PumpTechnicalSpecsSchema(BaseModel):
    """Specification schema for Pump equipment (centrifugal, positive displacement, submersible, etc.)."""
    flow_rate_lpm: Optional[float] = Field(None, description="Nominal flow rate in Litres per Minute")
    flow_rate_m3hr: Optional[float] = Field(None, description="Nominal flow rate in Cubic Metres per Hour")
    flow_rate_gpm: Optional[float] = Field(None, description="Nominal flow rate in US Gallons per Minute")
    max_head_m: Optional[float] = Field(None, description="Maximum total dynamic head in metres")
    max_head_ft: Optional[float] = Field(None, description="Maximum total dynamic head in feet")
    npsh_required_m: Optional[float] = Field(None, description="Net Positive Suction Head Required (NPSHr) in metres")
    max_pressure_bar: Optional[float] = Field(None, description="Maximum discharge / working pressure in bar")
    max_pressure_psi: Optional[float] = Field(None, description="Maximum discharge / working pressure in PSI")
    power_kw: Optional[float] = Field(None, description="Motor / shaft power rating in kilowatts")
    power_hp: Optional[float] = Field(None, description="Motor / shaft power rating in horsepower")
    motor_type: Optional[str] = Field(None, description="Motor type (e.g. induction, IE3, VFD-compatible, submersible)")
    pump_speed_rpm: Optional[float] = Field(None, description="Pump / impeller rotational speed in RPM")
    impeller_type: Optional[str] = Field(None, description="Impeller design (e.g. open, semi-open, closed, vortex)")
    impeller_diameter_mm: Optional[float] = Field(None, description="Impeller outer diameter in mm")
    efficiency_percent: Optional[float] = Field(None, description="Best efficiency point (BEP) efficiency in percent")
    suction_size_inch: Optional[float] = Field(None, description="Suction port / inlet flange diameter in inches")
    discharge_size_inch: Optional[float] = Field(None, description="Discharge port / outlet flange diameter in inches")
    suction_size_mm: Optional[float] = Field(None, description="Suction port / inlet flange diameter in mm")
    discharge_size_mm: Optional[float] = Field(None, description="Discharge port / outlet flange diameter in mm")
    fluid_temperature_max_c: Optional[float] = Field(None, description="Maximum handled fluid temperature in °C")
    fluid_temperature_min_c: Optional[float] = Field(None, description="Minimum handled fluid temperature in °C")
    max_solid_size_mm: Optional[float] = Field(None, description="Maximum allowable solid particle size in mm (for solids-handling pumps)")
    casing_material: Optional[str] = Field(None, description="Pump casing / body material (e.g. cast iron, stainless steel, bronze)")
    impeller_material: Optional[str] = Field(None, description="Impeller material (e.g. cast iron, SS316, PVDF)")
    seal_type: Optional[str] = Field(None, description="Shaft sealing type (e.g. mechanical seal, gland packing, magnetic drive)")
    drive_type: Optional[str] = Field(None, description="Drive type (e.g. direct-coupled, belt-drive, close-coupled)")
    noise_level_db: Optional[float] = Field(None, description="Sound pressure level in dB(A)")
    weight_kg: Optional[float] = Field(None, description="Net weight in kilograms")
    weight_lbs: Optional[float] = Field(None, description="Net weight in pounds")
    dimensions_mm: Optional[str] = Field(None, description="Outer dimensions: Length x Width x Height in mm")
    voltage: Optional[str] = Field(None, description="Electrical supply voltage (e.g. 230V, 400V, 460V)")
    frequency_hz: Optional[float] = Field(None, description="AC grid frequency in Hz (e.g. 50 or 60)")
    phase: Optional[str] = Field(None, description="Electrical phase (e.g. single-phase, 3-phase)")
    certifications: Optional[List[str]] = Field(None, description="Engineering certifications (e.g. CE, ATEX, NSF, ISO)")
    warranty_years: Optional[float] = Field(None, description="Product warranty in years")
    operating_temp_min_c: Optional[float] = Field(None, description="Minimum ambient operating temperature in °C")
    operating_temp_max_c: Optional[float] = Field(None, description="Maximum ambient operating temperature in °C")
    service_interval_hours: Optional[float] = Field(None, description="Recommended service / maintenance interval in hours")


class ValveTechnicalSpecsSchema(BaseModel):
    """Specification schema for Valve equipment (control, gate, ball, butterfly, check, etc.)."""
    valve_type: Optional[str] = Field(None, description="Valve type/design (e.g. ball, gate, globe, butterfly, check, needle, diaphragm)")
    actuator_type: Optional[str] = Field(None, description="Actuation method (e.g. manual, pneumatic, electric, hydraulic, solenoid)")
    cv_coefficient: Optional[float] = Field(None, description="Flow coefficient Cv (US) — volume of water (GPM) at 1 psi pressure drop")
    kv_coefficient: Optional[float] = Field(None, description="Flow coefficient Kv (metric) — volume of water (m³/h) at 1 bar pressure drop")
    pressure_rating_bar: Optional[float] = Field(None, description="Maximum rated working pressure in bar")
    pressure_rating_psi: Optional[float] = Field(None, description="Maximum rated working pressure in PSI")
    pressure_class: Optional[str] = Field(None, description="ANSI / PN pressure class rating (e.g. Class 150, PN16, PN40)")
    temperature_rating_max_c: Optional[float] = Field(None, description="Maximum fluid / operating temperature in °C")
    temperature_rating_min_c: Optional[float] = Field(None, description="Minimum fluid / operating temperature in °C")
    port_size_inch: Optional[float] = Field(None, description="Nominal valve port / bore size in inches")
    port_size_dn: Optional[int] = Field(None, description="Nominal valve port size as DN (Diameter Nominal) in mm")
    end_connection_type: Optional[str] = Field(None, description="End connection / face type (e.g. flanged, threaded, butt-weld, socket-weld, wafer)")
    face_to_face_mm: Optional[float] = Field(None, description="Face-to-face installation length dimension in mm")
    body_material: Optional[str] = Field(None, description="Valve body material (e.g. carbon steel, SS316, cast iron, bronze, PVC)")
    seat_material: Optional[str] = Field(None, description="Seat / seating material (e.g. PTFE, EPDM, metal, nylon)")
    stem_material: Optional[str] = Field(None, description="Stem material (e.g. SS316, brass, Inconel)")
    leakage_class: Optional[str] = Field(None, description="Leakage / shut-off class rating (e.g. ANSI Class IV, Class VI, bubble-tight)")
    fail_position: Optional[str] = Field(None, description="Actuator fail-safe position on loss of signal (e.g. fail-open, fail-closed, fail-in-place)")
    flow_characteristic: Optional[str] = Field(None, description="Inherent flow characteristic (e.g. equal percentage, linear, quick-opening)")
    rangeability: Optional[str] = Field(None, description="Valve rangeability / turndown ratio (e.g. 50:1)")
    stroke_mm: Optional[float] = Field(None, description="Linear or rotary actuator stroke in mm")
    actuator_air_supply_bar: Optional[float] = Field(None, description="Pneumatic actuator supply pressure in bar")
    signal_range: Optional[str] = Field(None, description="Control signal input range (e.g. 4-20mA, 0-10V, digital)")
    weight_kg: Optional[float] = Field(None, description="Net assembled weight in kilograms")
    dimensions_mm: Optional[str] = Field(None, description="Outer dimensions in mm (L x W x H)")
    certifications: Optional[List[str]] = Field(None, description="Certifications and approvals (e.g. CE, ATEX, SIL2, API 6D, PED)")
    warranty_years: Optional[float] = Field(None, description="Product warranty in years")
    operating_temp_min_c: Optional[float] = Field(None, description="Minimum ambient operating temperature in °C")
    operating_temp_max_c: Optional[float] = Field(None, description="Maximum ambient operating temperature in °C")


class GenericTechnicalSpecsSchema(BaseModel):
    """Fallback specification schema for any equipment type not covered by a specific schema.
    Captures universal mechanical, electrical, and physical attributes."""
    power_kw: Optional[float] = Field(None, description="Motor / shaft power rating in kilowatts")
    power_hp: Optional[float] = Field(None, description="Motor / shaft power rating in horsepower")
    voltage: Optional[str] = Field(None, description="Electrical supply voltage (e.g. 230V, 400V, 460V)")
    frequency_hz: Optional[float] = Field(None, description="AC grid frequency in Hz")
    phase: Optional[str] = Field(None, description="Electrical phase (e.g. single-phase, 3-phase)")
    max_pressure_bar: Optional[float] = Field(None, description="Maximum operating pressure in bar")
    max_pressure_psi: Optional[float] = Field(None, description="Maximum operating pressure in PSI")
    flow_rate_m3hr: Optional[float] = Field(None, description="Nominal flow / throughput rate in m³/hr")
    speed_rpm: Optional[float] = Field(None, description="Operational rotation speed in RPM")
    efficiency_percent: Optional[float] = Field(None, description="Operating efficiency in percent")
    noise_level_db: Optional[float] = Field(None, description="Sound pressure level in dB(A)")
    weight_kg: Optional[float] = Field(None, description="Net weight in kilograms")
    weight_lbs: Optional[float] = Field(None, description="Net weight in pounds")
    dimensions_mm: Optional[str] = Field(None, description="Outer dimensions: Length x Width x Height in mm")
    operating_temp_min_c: Optional[float] = Field(None, description="Minimum ambient operating temperature in °C")
    operating_temp_max_c: Optional[float] = Field(None, description="Maximum ambient operating temperature in °C")
    certifications: Optional[List[str]] = Field(None, description="Engineering certifications (e.g. CE, UL, ISO)")
    warranty_years: Optional[float] = Field(None, description="Product warranty in years")
    material: Optional[str] = Field(None, description="Primary construction / body material")
    drive_type: Optional[str] = Field(None, description="Drive mechanism (e.g. direct, belt, gear)")
    cooling_type: Optional[str] = Field(None, description="Cooling method (e.g. air-cooled, water-cooled)")
    connection_size_inch: Optional[float] = Field(None, description="Primary process connection / port size in inches")
    service_interval_hours: Optional[float] = Field(None, description="Recommended service / maintenance interval in hours")


# Maps EquipmentMaster.name (case-insensitive) to the matching Pydantic schema class.
# Add new entries here as additional master categories are introduced.
SPECS_SCHEMA_MAP: dict = {
    "compressor": CompressorTechnicalSpecsSchema,
    "pump":       PumpTechnicalSpecsSchema,
    "valve":      ValveTechnicalSpecsSchema,
}

def _resolve_specs_schema(master_name: str):
    """Return the Pydantic schema class appropriate for this equipment master.
    Falls back to GenericTechnicalSpecsSchema for unknown master names.
    """
    return SPECS_SCHEMA_MAP.get(master_name.strip().lower(), GenericTechnicalSpecsSchema)


def _clean_json(raw: str) -> str:
    """Strip markdown code fences if Gemini wraps output in ```json ... ```"""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _should_retry(exc: Exception) -> bool:
    """Return True for transient errors worth retrying."""
    if isinstance(exc, (genai_errors.APIError, genai_errors.ClientError, genai_errors.ServerError)):
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
    client = get_genai_client()
    raw_text = None
    response = None
    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config={
                "temperature": 0.1,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
        raw_text = response.text
        cleaned = _clean_json(raw_text)
        return json.loads(cleaned)
    except Exception as e:
        if isinstance(e, json.JSONDecodeError):
            print(f"  [Gemini JSON Error] Failed to parse JSON: {e}")
            if response and response.candidates:
                print(f"  [Gemini Finish Reason]: {response.candidates[0].finish_reason}")
            print(f"  [Gemini Raw Text Debug]:\n{raw_text}\n-------------------")
        else:
            print(f"  [Gemini API Error] {type(e).__name__}: {e}")
        raise e


def _truncate(text: str) -> str:
    """Truncate input to safe length for Gemini."""
    return text[:_MAX_INPUT_CHARS]


def extract_manufacturers(equipment_master: str, equipment_type: str, subtypes: list, text: str) -> list[dict]:
    """
    Extract manufacturer list from scraped text using schema guides.
    """
    subtype_str = ", ".join(subtypes) if subtypes else "general"

    prompt = f"""You are an expert in industrial equipment and global manufacturing.

    Return a list of reputable, well-established industrial manufacturers for the following equipment:

    Equipment Master : {equipment_master}
    Equipment Type   : {equipment_type}
    Sub-Type         : {subtype_str}

    IMPORTANT: Only return manufacturers that specifically make {equipment_master}s of the "{equipment_type}" type.
    Do NOT return manufacturers for other equipment categories (e.g. if the master is "Pump", do not return compressor or blower manufacturers).

    Requirements:
    - Only include manufacturers known for industrial-grade products (not consumer or light commercial).
    - Manufacturers must have a strong global or regional reputation for quality, reliability, and after-sales support.
    - Include only genuine, real-world manufacturers.
    - For each manufacturer provide:
    1. Name — Full official company name
    2. Country of Origin — Headquarters country
    3. Website — Official website URL

    Scraped Text:
    {_truncate(text)}"""

    res = generate_json(prompt, schema=ManufacturerListSchema)
    return res.get("manufacturers", []) if isinstance(res, dict) else []


def extract_manufacturers_from_knowledge(equipment_master: str, equipment_type: str, subtypes: list) -> list[dict]:
    """
    Extract manufacturer list directly from Gemini's internal knowledge without web search/scrape.
    Useful as a clean, robust fallback.
    """
    subtype_str = ", ".join(subtypes) if subtypes else "general"

    prompt = f"""You are an expert in industrial equipment and global manufacturing.

    Return a list of reputable, well-established industrial manufacturers for the following equipment:

    Equipment Master : {equipment_master}
    Equipment Type   : {equipment_type}
    Sub-Type         : {subtype_str}

    IMPORTANT: Only return manufacturers that specifically make {equipment_master}s of the "{equipment_type}" type.
    Do NOT return manufacturers for other equipment categories.

    Requirements:
    - Only include manufacturers known for industrial-grade products (not consumer or light commercial).
    - Manufacturers must have a strong global or regional reputation for quality, reliability, and after-sales support.
    - Include only genuine, real-world manufacturers.
    - For each manufacturer provide:
    1. Name — Full official company name
    2. Country of Origin — Headquarters country
    3. Website — Official website URL
    """

    res = generate_json(prompt, schema=ManufacturerListSchema)
    return res.get("manufacturers", []) if isinstance(res, dict) else []


def extract_models(manufacturer: str, equipment_type: str, text: str, allowed_subtypes: list[str] = None) -> list[dict]:
    """
    Extract model list for a manufacturer from scraped text using schema guides.
    """
    subtype_hint = ""
    if allowed_subtypes:
        subtype_hint = f"\nFor the 'subtype' field, match it against one of these allowed options if possible: {', '.join(allowed_subtypes)}."

    prompt = f"""You are a technical data extraction assistant.
From the scraped content below, extract up to 10 actual product models made by {manufacturer}.
Equipment Type: {equipment_type}{subtype_hint}

Text:
{_truncate(text)}"""

    res = generate_json(prompt, schema=ModelListSchema)
    return res.get("models", []) if isinstance(res, dict) else []


def extract_attributes(
    manufacturer: str,
    model_name: str,
    equipment_type: str,
    text: str,
    master_name: str = "",
) -> dict:
    """
    Extract technical specs sheet dictionary from specifications text using schema guides.

    Args:
        manufacturer:   Manufacturer name (e.g. "Grundfos")
        model_name:     Model identifier (e.g. "CM5-6")
        equipment_type: Combined type context string (e.g. "Centrifugal Pump")
        text:           Pre-filtered specs page text
        master_name:    EquipmentMaster.name (e.g. "Pump", "Compressor", "Valve").
                        Used to select the appropriate Pydantic schema for Gemini.
                        Falls back to GenericTechnicalSpecsSchema if unknown.
    """
    schema = _resolve_specs_schema(master_name)
    print(f"  [Schema] Using {schema.__name__} for master='{master_name}'")

    prompt = f"""You are a technical specifications compiler.
From the specifications text below, extract ALL measurable mechanical, electrical, and physical specifications.

Manufacturer: {manufacturer}
Model: {model_name}
Equipment Type: {equipment_type}

Text:
{_truncate(text)}"""

    return generate_json(prompt, schema=schema)


def enrich_manufacturer_info(manufacturer: str, equipment_type: str) -> dict:
    """
    Ask Gemini directly (without scraping) to provide known manufacturer info.
    Used as a fallback when web scraping yields no results.
    """
    prompt = f"""Provide factual information about the manufacturer: {manufacturer}
Equipment Type context: {equipment_type}

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
        client = get_genai_client()
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embedding.values
    except Exception as e:
        print(f"  [Embedding Error] Failed to generate embedding: {e}")
        return None
