"""
LLM service — prompt engineering + Groq API integration.
Uses chain-of-thought prompting with few-shot examples and strict JSON output.
"""
from __future__ import annotations
import json
import os
import re
from groq import Groq

from app.models.schemas import ReviewResult, SuggestedRewrite

# ─── Prompt Templates ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert technical recruiter and senior resume coach with 15+ years of experience \
evaluating candidates across technology, product, finance, and business roles. \
You have deep knowledge of ATS (Applicant Tracking System) optimization, \
impactful resume writing, and industry-standard hiring criteria.

Your task is to rigorously analyze the provided resume and return ONLY a valid JSON object \
matching the schema below — no markdown fences, no extra text, no explanation outside the JSON.

OUTPUT SCHEMA:
{
  "overall_score": <integer 0-100>,
  "ats_compatibility": "<High|Medium|Low>",
  "strengths": ["<string>", ...],
  "weaknesses": ["<string>", ...],
  "missing_keywords": ["<string>", ...],
  "suggested_rewrites": [
    {"original": "<exact phrase from resume>", "improved": "<rewritten version>"},
    ...
  ]
}

SCORING RUBRIC:
- 80-100: Exceptional — strong quantified impact, perfect ATS keywords, professional format
- 60-79:  Good — solid experience but missing some keywords or quantification
- 40-59:  Needs Work — weak structure, missing key sections, or poor keyword density
- 0-39:   Poor — major issues with content, format, or relevance

INTERNAL REASONING STEPS (do NOT output these — reason internally before generating JSON):
1. Grammar & clarity: Are sentences professional and free of errors?
2. Structure: Are all key sections present (Summary, Experience, Education, Skills)?
3. Measurable impact: Does the candidate quantify achievements (%, $, users, etc.)?
4. ATS compatibility: Are standard industry keywords and job titles present?
5. Overall impression: What would a recruiter think in the first 6 seconds?

GUARDRAILS:
- Do NOT invent skills or experiences not explicitly stated in the resume.
- If the document is clearly not a resume, set overall_score to 0 and explain in weaknesses.
- Provide at least 2 strengths, 2 weaknesses, 3 missing keywords, and 2 suggested rewrites.
"""

FEW_SHOT_EXAMPLE = """\
EXAMPLE RESUME SNIPPET:
---
John Doe | Software Engineer
Skills: Python, SQL
Experience:
  - Worked on backend systems
  - Helped with database migrations
Education: B.S. Computer Science
---

EXAMPLE OUTPUT:
{
  "overall_score": 42,
  "ats_compatibility": "Low",
  "strengths": [
    "Relevant educational background in Computer Science",
    "Exposure to both backend development and database work"
  ],
  "weaknesses": [
    "No quantified achievements (e.g., improved performance by X%, reduced latency)",
    "Vague bullet points — 'worked on' and 'helped with' convey no concrete impact",
    "Missing key sections: Professional Summary, Projects, Certifications"
  ],
  "missing_keywords": ["REST API", "microservices", "Docker", "CI/CD", "Git", "Agile"],
  "suggested_rewrites": [
    {
      "original": "Worked on backend systems",
      "improved": "Engineered scalable Python microservices handling 10K+ daily requests, reducing API latency by 35%"
    },
    {
      "original": "Helped with database migrations",
      "improved": "Led migration of 500GB legacy MySQL database to PostgreSQL with zero downtime using blue-green deployment"
    }
  ]
}
"""

# ─── Main Service ─────────────────────────────────────────────────────────────

def build_review_prompt(resume_text: str) -> str:
    return f"""{FEW_SHOT_EXAMPLE}

Now analyze the following resume:

RESUME:
---
{resume_text}
---

Return ONLY the JSON object. No markdown, no preamble."""


def _extract_json(raw: str) -> dict:
    """Extract JSON from LLM output, handling markdown fences if present."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
    # Find the first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {raw[:200]}")
    return json.loads(match.group())


def analyze_resume(resume_text: str) -> ReviewResult:
    """
    Send resume text to Groq LLM and return a validated ReviewResult.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_review_prompt(resume_text)},
        ],
        temperature=0.2,      # Low temperature for consistent structured output
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    raw_content = completion.choices[0].message.content
    data = _extract_json(raw_content)

    # Normalize suggested_rewrites
    rewrites = [
        SuggestedRewrite(original=r["original"], improved=r["improved"])
        for r in data.get("suggested_rewrites", [])
    ]
    data["suggested_rewrites"] = rewrites

    return ReviewResult(**data)


# ─── JD Match LLM Analysis ───────────────────────────────────────────────────

JD_MATCH_SYSTEM_PROMPT = """\
You are an expert technical recruiter comparing a resume against a job description.
Return ONLY a valid JSON object:
{
  "explanation": "<2-3 sentence summary of fit>",
  "matched_keywords": ["<keyword present in both resume and JD>", ...],
  "missing_keywords": ["<important JD keyword NOT in resume>", ...]
}
No markdown, no extra text.
"""


def analyze_jd_match(resume_text: str, job_description: str) -> dict:
    """Ask the LLM to identify matched and missing keywords between resume and JD."""
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    prompt = f"""RESUME:
---
{resume_text}
---

JOB DESCRIPTION:
---
{job_description}
---

Identify matched keywords, missing keywords, and write a 2-3 sentence explanation of fit.
Return ONLY the JSON object."""

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JD_MATCH_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    raw_content = completion.choices[0].message.content
    return _extract_json(raw_content)
