import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from google import genai
from utils.genai_extractor import ManufacturerListSchema

client = genai.Client(api_key=config.GEMINI_API_KEY)

# Let's rebuild the prompt and call Gemini directly to print finish_reason and full response text
prompt = """You are an expert in industrial equipment and global manufacturing.

Return a list of reputable, well-established industrial manufacturers for the following equipment:

Equipment Master : Pump
Equipment Type   : Piston
Sub-Type         : Simplex, Duplex, Triplex, Quadruplex, Quintuplex

IMPORTANT: Only return manufacturers that specifically make Pumps of the "Piston" type.
Do NOT return manufacturers for other equipment categories.

Requirements:
- Only include manufacturers known for industrial-grade products.
- Name, Country, Website.

Scraped Text:
Bosch Rexroth: Known for innovative hydraulic solutions with a global footprint.
Grundfos: Offers energy-efficient pumps with strong after-sales support.
Eaton: Provides a wide range of industrial pumps with customizable options.
Kawasaki: Renowned for durable, high-performance piston pumps in heavy industries.
Yamada: Specializes in compact, high-precision piston pump solutions.
Hydra-Tech: Focuses on rugged, reliable pumps for mining and construction.
Vickers: Offers hydraulic piston pumps with a focus on efficiency and control.
Sauer-Danfoss: Known for innovative control systems integrated with piston pumps.
Daikin: Provides energy-efficient piston pumps suitable for HVAC applications.
Sunfab: Swedish vendor with a strong presence in mobile hydraulic solutions.
Parkinson Technologies: Specializes in high-precision piston pumps for aerospace and medical sectors.
Wilden: Focuses on high-pressure piston pumps for chemical and industrial use.
"""

print("Calling generate_content...")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config={
        "temperature": 0.1,
        "max_output_tokens": 2048,
        "response_mime_type": "application/json",
        "response_schema": ManufacturerListSchema,
    }
)

print("Finish Reason:", response.candidates[0].finish_reason)
print("Text length:", len(response.text))
print("Response Text:")
print(response.text)
