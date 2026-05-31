"""
data/compressors.py — Master input list of compressor types
"""

compressors = [
    {
        "type": "Air Compressors",
        "applications": ["Pneumatic tools", "Tire inflation"],
        "subtypes": []
    },
    {
        "type": "Refrigeration Compressors",
        "applications": ["AC units", "Heat pumps"],
        "subtypes": ["Reciprocating", "Scroll", "Screw"]
    },
    {
        "type": "Gas Compressors",
        "applications": ["Natural gas pipelines"],
        "subtypes": ["Reciprocating", "Centrifugal"]
    },
    {
        "type": "Turbochargers/Superchargers",
        "applications": ["Automotive"],
        "subtypes": ["Centrifugal", "Roots"]
    },
    {
        "type": "Medical Compressors",
        "applications": ["Medical devices"],
        "subtypes": ["Oil-free diaphragm", "Scroll"]
    }
]
