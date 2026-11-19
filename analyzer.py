import json
import os
import re
from io import BytesIO

import requests
from PyPDF2 import PdfReader

EXTRACT = ("From the job description alone, copy each distinct required skill "
           "verbatim. Return JSON with one string array named skills.")
PROMPT = ("Compare this resume with the job. Use the supplied verified skill groups. "
          "Return JSON: match_score, matched_skills, missing_skills, tips. "
          "Give exactly three different, brief tips. Suggest learning missing skills "
          "or documenting existing evidence. Never invent experience. Ignore identity.")
MODEL = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
BASE = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")


def read_resume(data):
    if not data or len(data) > 5_000_000:
        raise ValueError("Choose a PDF smaller than 5 MB.")
    try:
        pdf = PdfReader(BytesIO(data))
        if pdf.is_encrypted:
            raise ValueError("Please use a PDF without a password.")
        text = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("The PDF could not be opened.") from exc
    if not text:
        raise ValueError("No selectable text found. Export a text-based PDF.")
    if len(text) > 9000:
        raise ValueError("Use a shorter resume (up to 9,000 extracted characters).")
    return text


def complete(prompt, resume, job, evidence=None):
    payload = {"model": MODEL, "temperature": 0, "max_tokens": 500,
               "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": prompt},
                            {"role": "user", "content": json.dumps(
                                {"resume": resume, "job_description": job, "verified": evidence})}]}
    try:
        response = requests.post(BASE.rstrip("/") + "/chat/completions",
                                 json=payload, timeout=(8, 180))
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except requests.RequestException as exc:
        raise ValueError("Model unavailable. Start the local server and check the model name.") from exc
    except (IndexError, KeyError, ValueError, TypeError) as exc:
        raise ValueError("The model returned an unreadable response. Try again.") from exc


def analyse(resume, job):
    job = job.strip()
    if not 15 <= len(job) <= 4000:
        raise ValueError("Enter a job description between 15 and 4,000 characters.")
    extraction = complete(EXTRACT, "", job)
    skills = extraction.get("skills") if isinstance(extraction, dict) else None
    if not isinstance(skills, list):
        raise ValueError("Could not identify the requirements. List the required skills explicitly.")
    groups = {"matched_skills": [], "missing_skills": []}
    seen = set()
    for skill in skills:
        if not isinstance(skill, str):
            continue
        skill = skill.strip()
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if not skill or skill.casefold() in seen or not re.search(pattern, job, re.I):
            continue
        seen.add(skill.casefold())
        key = "matched_skills" if re.search(pattern, resume, re.I) else "missing_skills"
        groups[key].append(skill)
    if not seen:
        raise ValueError("No verifiable job skills found. Describe the role's requirements.")
    score = round(100 * len(groups["matched_skills"]) / len(seen))
    evidence = dict(groups, match_score=score)
    result = complete(PROMPT, resume, job, evidence)
    tips = result.get("tips") if isinstance(result, dict) else None
    if (not isinstance(tips, list) or len(tips) != 3
            or not all(isinstance(t, str) and t.strip() for t in tips)
            or len({t.strip().casefold() for t in tips}) != 3):
        raise ValueError("The model did not supply three distinct tips. Please retry.")
    return dict(evidence, tips=tips)
