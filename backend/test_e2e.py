"""
Full end-to-end test suite for the Resume Review Agent API.
Tests: Health, Upload, Review, Match, History endpoints.
"""
import sys
import json
import time
import requests

BASE = "http://localhost:8000"
RESUME_PATH = r"E:\Resume Review Agent\test_resume.pdf"

SAMPLE_JD = """
We are looking for a Senior Full Stack Engineer to join our team.

Requirements:
- 3+ years of experience with Python (FastAPI or Django)
- Strong proficiency in React, TypeScript, Next.js
- Experience with REST APIs and GraphQL
- Familiarity with Docker, Kubernetes, and CI/CD pipelines
- Database experience: PostgreSQL, MongoDB, Redis
- Cloud platform experience: AWS or GCP
- Excellent communication and mentoring skills

Nice to have:
- Terraform or other IaC tools
- Experience with microservices architecture
- Knowledge of system design principles
"""

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = []

def test(name, fn):
    try:
        result = fn()
        print(f"{PASS} {name}: {result}")
        results.append((name, True, result))
        return result
    except Exception as e:
        print(f"{FAIL} {name}: {e}")
        results.append((name, False, str(e)))
        return None

# ── 1. Health Check ──────────────────────────────────────────────────────────
def check_health():
    r = requests.get(f"{BASE}/", timeout=5)
    assert r.status_code == 200, f"Status {r.status_code}"
    data = r.json()
    assert data["status"] == "ok", f"Unexpected status: {data}"
    return f"status=ok, version={data['version']}"

test("Health Check GET /", check_health)

# ── 2. Upload Resume ─────────────────────────────────────────────────────────
resume_id = None

def upload_resume():
    global resume_id
    with open(RESUME_PATH, "rb") as f:
        files = {"file": ("test_resume.pdf", f, "application/pdf")}
        data = {"user_id": "test_user_01"}
        r = requests.post(f"{BASE}/upload", files=files, data=data, timeout=15)
    assert r.status_code == 200, f"Status {r.status_code} — {r.text}"
    resp = r.json()
    assert "resume_id" in resp, "Missing resume_id in response"
    assert resp["char_count"] > 100, f"Too few chars extracted: {resp['char_count']}"
    resume_id = resp["resume_id"]
    return f"resume_id={resume_id}, chars={resp['char_count']}, file={resp['filename']}"

test("Upload Resume POST /upload", upload_resume)

if not resume_id:
    print(f"\n{FAIL} Cannot continue without resume_id. Exiting.")
    sys.exit(1)

# ── 3. Upload Invalid File ───────────────────────────────────────────────────
def upload_invalid():
    files = {"file": ("test.txt", b"this is not a resume", "text/plain")}
    r = requests.post(f"{BASE}/upload", files=files, data={"user_id": "test"}, timeout=10)
    assert r.status_code in (422, 415, 400), f"Expected 4xx, got {r.status_code}"
    return f"Correctly rejected with {r.status_code}"

test("Upload Invalid File (non-resume text)", upload_invalid)

# ── 4. Upload Bad resume_id ──────────────────────────────────────────────────
def review_bad_id():
    r = requests.post(f"{BASE}/review", json={"resume_id": "badid123", "user_id": "test"}, timeout=10)
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    return f"Correctly rejected with 422"

test("Review with invalid resume_id", review_bad_id)

# ── 5. Review Resume ─────────────────────────────────────────────────────────
review_result = None

def review_resume():
    global review_result
    print(f"  {INFO} Calling LLM (may take 10-30s)...")
    r = requests.post(
        f"{BASE}/review",
        json={"resume_id": resume_id, "user_id": "test_user_01"},
        timeout=60,
    )
    assert r.status_code == 200, f"Status {r.status_code} — {r.text[:300]}"
    data = r.json()
    result = data["result"]
    assert "overall_score" in result, "Missing overall_score"
    assert 0 <= result["overall_score"] <= 100, f"Score out of range: {result['overall_score']}"
    assert result["ats_compatibility"] in ("High", "Medium", "Low"), f"Bad ATS: {result['ats_compatibility']}"
    assert len(result["strengths"]) >= 2, "Too few strengths"
    assert len(result["weaknesses"]) >= 2, "Too few weaknesses"
    assert len(result["missing_keywords"]) >= 2, "Too few keywords"
    assert len(result["suggested_rewrites"]) >= 1, "No rewrites"
    review_result = result
    return (
        f"score={result['overall_score']}/100, ATS={result['ats_compatibility']}, "
        f"strengths={len(result['strengths'])}, weaknesses={len(result['weaknesses'])}, "
        f"keywords={len(result['missing_keywords'])}, rewrites={len(result['suggested_rewrites'])}"
    )

test("Review Resume POST /review (LLM)", review_resume)

# ── 6. JD Match ──────────────────────────────────────────────────────────────
def match_jd():
    print(f"  {INFO} Generating embeddings + LLM match analysis...")
    r = requests.post(
        f"{BASE}/match",
        json={"resume_id": resume_id, "job_description": SAMPLE_JD, "user_id": "test_user_01"},
        timeout=90,
    )
    assert r.status_code == 200, f"Status {r.status_code} — {r.text[:300]}"
    data = r.json()
    assert "match_percentage" in data, "Missing match_percentage"
    assert 0 <= data["match_percentage"] <= 100, f"Match % out of range: {data['match_percentage']}"
    assert "explanation" in data, "Missing explanation"
    assert isinstance(data["matched_keywords"], list), "matched_keywords not a list"
    assert isinstance(data["missing_keywords"], list), "missing_keywords not a list"
    return (
        f"match={data['match_percentage']}%, "
        f"matched_kw={len(data['matched_keywords'])}, "
        f"missing_kw={len(data['missing_keywords'])}, "
        f"explanation='{data['explanation'][:60]}...'"
    )

test("JD Match POST /match (Embeddings + LLM)", match_jd)

# ── 7. History endpoint ──────────────────────────────────────────────────────
def check_history():
    r = requests.get(f"{BASE}/reviews/history/test_user_01", timeout=10)
    assert r.status_code == 200, f"Status {r.status_code}"
    data = r.json()
    assert isinstance(data, list), "Expected a list"
    assert len(data) >= 1, f"Expected at least 1 review in history, got {len(data)}"
    return f"Found {len(data)} review(s) in history for test_user_01"

test("Review History GET /reviews/history/test_user_01", check_history)

# ── 8. Get Review by ID ──────────────────────────────────────────────────────
def check_nonexistent_review():
    fake_id = "000000000000000000000000"
    r = requests.get(f"{BASE}/reviews/{fake_id}", timeout=10)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    return f"Correctly returned 404 for non-existent ID"

test("GET /reviews/nonexistent returns 404", check_nonexistent_review)

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
for name, ok, msg in results:
    status = PASS if ok else FAIL
    print(f"  {status}  {name}")
print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("\nAll tests passed! The project is working perfectly.")
else:
    print(f"\n{failed} test(s) failed. Check the output above for details.")
    sys.exit(1)
