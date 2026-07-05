# Resume Review Agent

An AI-powered resume analysis tool that reviews resumes against best practices and (optionally) a target job description — returning a structured score, strengths, weaknesses, missing keywords, and rewrite suggestions.



---

## 1. Project Overview

The Resume Review Agent lets a user upload a resume (PDF/DOCX), sends the extracted text to an LLM through carefully engineered prompts, and returns structured, actionable feedback. It also supports semantic matching between a resume and a job description using vector search, so users can see how well their resume aligns with a specific role.

### Core Requirements Satisfied

| Requirement | Implementation |
|---|---|
| Programming language | Python (FastAPI backend) |
| Prompt engineering | System prompts, few-shot examples, chain-of-thought reasoning, strict JSON output schema |
| LLM API | Groq API (Llama 3.x models) |
| Database | MongoDB Atlas (structured data + Atlas Vector Search for embeddings) |
| Web framework | FastAPI (backend REST API) |
| Frontend | HTML, CSS, JavaScript (vanilla) |
| Deployment | Docker containers, deployable to AWS / Azure / Render |

---

## 2. Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **LLM:** Groq API (Llama 3.1/3.3)
- **Database:** MongoDB Atlas (documents + native Vector Search)
- **Frontend:** HTML5, CSS3, vanilla JavaScript (Fetch API)
- **File Parsing:** pdfplumber (PDF), python-docx (DOCX)
- **Deployment:** Docker, Docker Compose, hosted on Render/AWS/Azure

---

## 3. System Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Frontend        │      │  FastAPI Backend  │      │  Groq LLM API    │
│  (HTML/CSS/JS)   │─────▶│  (Python)          │─────▶│  (Llama models)  │
│                  │◀─────│                    │◀─────│                  │
└─────────────────┘      └────────┬──────────┘      └─────────────────┘
                                    │
                                    ▼
                          ┌──────────────────┐
                          │  MongoDB Atlas     │
                          │  - resumes         │
                          │  - reviews         │
                          │  - embeddings       │
                          │  (+ Vector Search)  │
                          └──────────────────┘
```

### Request Flow (Resume Review)

1. User uploads a resume file via the browser (HTML form + JS `fetch`).
2. FastAPI receives the file, extracts raw text using `pdfplumber` / `python-docx`.
3. Extracted text is stored in MongoDB (`resumes` collection).
4. Backend builds a structured prompt (system prompt + resume text) and sends it to the Groq API.
5. LLM returns a structured JSON response (score, strengths, weaknesses, missing keywords, rewrite suggestions).
6. Backend validates/parses the JSON and stores it in MongoDB (`reviews` collection).
7. Frontend renders the results as score cards and lists.

### Request Flow (JD Matching — Vector Search)

1. User pastes a job description alongside their resume.
2. Backend generates embeddings for both resume text and JD text.
3. Embeddings are stored in MongoDB's `embeddings` collection with a Vector Search index.
4. A `$vectorSearch` aggregation pipeline computes cosine similarity between resume and JD embeddings.
5. The similarity score is combined with the LLM's qualitative analysis into a final match score.
6. Result is returned to the frontend and displayed as a match percentage with explanation.

---

## 4. Folder Structure

```
resume-review-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point, CORS, router registration
│   │   ├── routes/
│   │   │   ├── upload.py           # POST /upload — file upload + text extraction
│   │   │   ├── review.py           # POST /review — LLM analysis
│   │   │   └── match.py            # POST /match — JD vector matching
│   │   ├── services/
│   │   │   ├── llm_service.py      # Groq API calls, prompt construction
│   │   │   ├── pdf_parser.py       # PDF/DOCX text extraction
│   │   │   └── embedding_service.py# Embedding generation + vector search queries
│   │   ├── db/
│   │   │   └── mongo_client.py     # MongoDB connection + collections
│   │   └── models/
│   │       └── schemas.py          # Pydantic request/response models
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── index.html                  # Upload form, JD input, results display
│   ├── style.css                   # Layout, score cards, responsive design
│   ├── script.js                   # Fetch calls to backend, DOM rendering
│   └── Dockerfile                  # Nginx static file server
├── docker-compose.yml
└── README.md
```

---

## 5. Prompt Engineering Design

The core intelligence of this project lies in how prompts are structured.

**System Prompt** — defines the agent's role, expertise, and strict output format:
> "You are an expert technical recruiter and resume reviewer with 15 years of experience across tech, product, and business roles. Analyze the given resume and respond ONLY with a valid JSON object matching the schema provided. Do not include any text outside the JSON."

**Prompt Components:**
1. **Role definition** — establishes expertise and tone.
2. **Few-shot examples** — 1–2 example resume snippets with ideal feedback, to anchor output quality and format.
3. **Chain-of-thought instruction** — the model is asked to internally reason through: grammar → structure → measurable impact → ATS keyword compatibility → job relevance — before producing the final verdict.
4. **Structured output enforcement** — output is constrained to a fixed JSON schema so the backend can reliably parse it.
5. **Guardrails** — instructs the model to avoid hallucinating skills not present in the resume, and to flag if the uploaded document isn't actually a resume.

**Output Schema Example:**
```json
{
  "overall_score": 78,
  "ats_compatibility": "Medium",
  "strengths": ["Clear quantifiable achievements", "Good use of action verbs"],
  "weaknesses": ["Missing a professional summary", "Inconsistent date formatting"],
  "missing_keywords": ["Docker", "CI/CD", "REST APIs"],
  "suggested_rewrites": [
    {
      "original": "Responsible for managing a team",
      "improved": "Led a cross-functional team of 6 engineers, improving sprint velocity by 20%"
    }
  ]
}
```

---

## 6. Database Design (MongoDB Atlas)

**Collections:**
- `resumes` — raw extracted resume text + metadata (user id, filename, upload timestamp)
- `reviews` — structured LLM feedback linked to a resume id
- `embeddings` — vector embeddings for resumes and job descriptions, indexed for Atlas Vector Search

**Why MongoDB Atlas for both structured + vector data:**
- LLM outputs are JSON-shaped, mapping naturally to MongoDB documents without rigid schemas.
- Atlas Vector Search removes the need for a separate vector database (e.g. Pinecone/Chroma) — one connection, one system, simpler architecture.

---

## 7. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/upload` | Accepts a resume file, extracts text, stores in MongoDB |
| POST | `/review` | Sends resume text to LLM, returns structured feedback |
| POST | `/match` | Computes resume-JD similarity using vector search |
| GET | `/reviews/{id}` | Retrieves a specific past review |
| GET | `/reviews/history/{user_id}` | Retrieves a user's review history |

---

## 8. Setup & Local Development

### Prerequisites
- Python 3.11+
- MongoDB Atlas account (free M0 cluster)
- Groq API key

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in MONGO_URI, DB_NAME, GROQ_API_KEY
uvicorn app.main:app --reload
```
Backend runs at `http://localhost:8000` (Swagger docs at `/docs`).

### Frontend Setup
Simply open `frontend/index.html` in a browser, or serve it with any static file server. Update `API_BASE` in `script.js` to point to your backend URL.

### MongoDB Atlas Vector Index
Create a vector search index on the `embeddings` collection:
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    }
  ]
}
```

---

