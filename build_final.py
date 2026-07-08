import json
import os

with open('results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Convert list/dict to dict
if isinstance(data, list):
    data = {item['id']: item for item in data}

# Update Fathom and Devin
if 93 in data:
    data[93]['evidence_url'] = "https://developers.fathom.ai/quickstart"
    data[93]['buildability_verdict'] = "buildable-now"
    data[93]['needs_human_review'] = False
    data[93]['confidence'] = "high"
    
if 96 in data:
    data[96]['evidence_url'] = "https://docs.devin.ai/work-with-devin/devin-mcp"
    data[96]['buildability_verdict'] = "buildable-now"
    data[96]['needs_human_review'] = False
    data[96]['confidence'] = "high"

with open('results_final.json', 'w', encoding='utf-8') as f:
    json.dump(list(data.values()), f, indent=2)

print("Saved results_final.json")
