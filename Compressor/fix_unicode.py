"""Fix Unicode box-drawing and special characters in all stage files."""
import re

FILES = [
    "stages/stage1_manufacturers.py",
    "stages/stage2_models.py",
    "stages/stage3_attributes.py",
    "utils/cache.py",
    "utils/web_search.py",
    "utils/scraper.py",
    "utils/genai_extractor.py",
    "config.py",
]

# Map of unicode chars to ASCII replacements
REPLACEMENTS = {
    "\u2500": "-",   # ─ horizontal box
    "\u2502": "|",   # │ vertical box
    "\u250c": "+",   # ┌
    "\u2510": "+",   # ┐
    "\u2514": "+",   # └
    "\u2518": "+",   # ┘
    "\u251c": "+",   # ├
    "\u2524": "+",   # ┤
    "\u252c": "+",   # ┬
    "\u2534": "+",   # ┴
    "\u253c": "+",   # ┼
    "\u2550": "=",   # ═
    "\u2551": "|",   # ║
    "\u2554": "+",   # ╔
    "\u2557": "+",   # ╗
    "\u255a": "+",   # ╚
    "\u255d": "+",   # ╝
    "\u2588": "#",   # █
    "\u25ba": ">",   # ►
    "\u2192": "->",  # →
    "\u2014": "--",  # —
    "\u2013": "-",   # –
    "\u25b6": ">",   # ▶
    "\u26a0": "(!)", # ⚠
    "\u2714": "OK",  # ✔
    "\u2716": "X",   # ✖
    "\u2713": "OK",  # ✓
    "\u2717": "X",   # ✗
    "\u00e9": "e",   # é
    "\u00e0": "a",   # à
}

for filepath in FILES:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        for char, repl in REPLACEMENTS.items():
            content = content.replace(char, repl)

        # Remove any remaining non-ASCII from docstrings/comments
        # (keep strings intact but replace box chars)
        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {filepath}")
        else:
            print(f"Clean: {filepath}")
    except Exception as e:
        print(f"Error in {filepath}: {e}")

print("Done.")
