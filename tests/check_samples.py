"""Run from the project folder after starting the configured local model."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyzer import analyse, read_resume


def keys(items):
    return {item.casefold() for item in items}


for case in json.loads((ROOT / "samples/cases.json").read_text()):
    resume = read_resume((ROOT / "samples" / (case["id"] + ".pdf")).read_bytes())
    result = analyse(resume, case["job"])
    agree = (keys(result["matched_skills"]) == keys(case["expected_matches"])
             and keys(result["missing_skills"]) == keys(case["expected_missing"]))
    print(case["id"], result["match_score"], "skill lists agree:", agree)
