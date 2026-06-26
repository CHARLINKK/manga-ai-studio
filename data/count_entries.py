import json
import os

filepath = r"C:\Users\Admin\.gemini\antigravity\scratch\manga-ocr-extractor\data\false_cognates_en_pt.json"

with open(filepath, "r", encoding="utf-8") as f:
    d = json.load(f)

fc = len(d["false_cognates"])
ec = len(d["expression_corrections"])
ms = len(d["manga_specific"])
total = fc + ec + ms

print(f"False Cognates: {fc}")
print(f"Expression Corrections: {ec}")
print(f"Manga Specific: {ms}")
print(f"Total Entries: {total}")
print(f"File size: {os.path.getsize(filepath)} bytes")
print("JSON is valid!")
