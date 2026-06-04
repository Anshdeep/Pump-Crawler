import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.genai_extractor import extract_manufacturers

text = """
Kawasaki Heavy Industries, established in 1878, manufactures high-pressure piston pumps, gear pumps and axial piston units under its precision machinery division.
Bosch Rexroth AG, a leading global supplier of drive and control technologies, offers high-efficiency axial piston pumps and radial piston pumps for mobile and industrial applications.
Atos S.p.A., an Italian manufacturer founded in 1957, produces high-quality electrohydraulic piston pumps and vane pumps conforming to international standards.
Bucher Hydraulics GmbH, a Swiss company established in 1923, manufactures high-reliability internal gear pumps and axial piston pumps.
Casappa S.p.A., an Italian hydraulics specialist founded in 1952, manufactures high-performance gear pumps and piston pumps.
Daikin Industries, Ltd., a Japanese multinational company founded in 1924, manufactures energy-efficient piston pumps and vane pumps for industrial machinery.
"""

models_to_test = ["gemini-2.0-flash", "gemini-2.5-flash"]

for model in models_to_test:
    print(f"\n================ Testing Model: {model} ================")
    config.GEMINI_MODEL = model
    try:
        res = extract_manufacturers("Pump", "Piston", ["Simplex", "Duplex"], text)
        print(f"Success! Discovered {len(res)} manufacturers:")
        for m in res:
            print(f" - {m.get('name')} ({m.get('country')})")
    except Exception as e:
        print("Failed with exception:", e)
