import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from google import genai

client = genai.Client(api_key=config.GEMINI_API_KEY)
models = client.models.list()
for m in models:
    if "flash" in m.name or "pro" in m.name:
        print(f"Name: {m.name}, Supported Actions: {m.supported_actions}")
