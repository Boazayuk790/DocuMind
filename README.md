# DocuMind

**Live demo:** https://documind-3yfxw3feqscg3zn6ec7sjx.streamlit.app/

**Live API docs:** https://documind-txiu.onrender.com/docs

[![CI](https://github.com/Boazayuk790/DocuMind/actions/workflows/ci.yml/badge.svg)](https://github.com/Boazayuk790/DocuMind/actions/workflows/ci.yml)

_Free hosting sleeps when idle, so the first load can take about a minute. Register a test account to try it._

An AI-powered document intelligence app. Upload a PDF, DOCX or TXT file and Gemini turns it into structured results. You can then review your history, export reports, chat with a document, or compare two documents. Accounts are private.

Built as a portfolio project with FastAPI, Streamlit, PostgreSQL and the Gemini API.

## Features

- Upload PDF, DOCX or TXT files and get a structured analysis: document type, summary, key information, important dates, amounts, missing information and inconsistencies
- Analysis history with search, document type filter, date filter and sorting
- Export any analysis as JSON, DOCX or PDF
- Chat with a document: ask questions about an analysed file
- Compare two documents
- Private accounts: register, log in, log out. Each user only sees their own data

## Screenshots

![Login](docs/login.png)
![Analysis](docs/analysis.png)
![Chat](docs/chat.png)
![Compare](docs/compare.png)

## Tech stack

- Backend: FastAPI, Pydantic, PostgreSQL (Neon), SQLite fallback for local use and tests
- Frontend: Streamlit
- AI: Google Gemini (google-genai)
- Auth: scrypt password hashing with per-user salts, signed tokens (itsdangerous) with 24-hour expiry
- Tests: Pytest, 41 tests (Gemini is mocked, no API calls in tests)
- Hosting: Render (API), Streamlit Community Cloud (frontend), Neon (database)

## Architecture

    Browser --> Streamlit Community Cloud (frontend.py)
                    |
                    v  HTTPS
                Render (FastAPI)  --> Gemini API
                    |
                    v
                Neon PostgreSQL

## Project structure

    DocuMind/
    |-- app/
    |   |-- main.py              API endpoints
    |   |-- auth.py              password hashing and tokens
    |   |-- database.py          PostgreSQL/SQLite: users, document_analyses
    |   |-- rate_limit.py        per-IP rate limiting
    |   |-- schemas.py           Pydantic models
    |   `-- services/
    |       |-- document_reader.py   file reading and content validation
    |       `-- llm_service.py       Gemini calls and error handling
    |-- frontend.py              Streamlit UI
    |-- tests/                   41 automated tests
    |-- docs/                    screenshots
    |-- requirements.txt
    `-- .env.example

## API endpoints

Public: GET /, POST /register, POST /login

Require `Authorization: Bearer <token>`: GET /me, POST /analyze, GET /history, GET /history/{id}, DELETE /history/{id}, POST /chat, POST /compare

Interactive docs are available at /docs.

## Security

- Passwords hashed with scrypt and a per-user salt
- Signed tokens that expire after 24 hours
- Rate limiting on login and register (5 per minute per IP)
- Upload content validation: PDF header check, DOCX zip structure check with a zip-bomb size cap, TXT UTF-8 and null byte checks
- Prompt-injection tagging: document text is marked as untrusted data in chat and compare prompts
- Server-side error logging with generic error messages, so internal and AI errors are never shown to users
- All history, chat and delete operations are filtered by user
- Secrets are read from environment variables and never committed

## Running locally

1. Clone the repo and create a virtual environment:

        python -m venv .venv
        .\.venv\Scripts\Activate.ps1
        pip install -r requirements.txt

2. Copy `.env.example` to `.env` and fill in the values:

        GEMINI_API_KEY=your-gemini-key
        SECRET_KEY=a-long-random-string
        DATABASE_URL=optional, leave empty to use local SQLite

3. Start the API (terminal 1):

        uvicorn app.main:app --reload

4. Start the frontend (terminal 2):

        streamlit run frontend.py

   The app opens at http://localhost:8501 and the API docs are at http://127.0.0.1:8000/docs

The frontend reads the API address from the `API_URL` environment variable (default `http://127.0.0.1:8000`).

## Running the tests

    python -m pytest

The tests use a local SQLite database and a mocked Gemini client, so they never touch the hosted database or use API quota.

## Deployment

- API: Render web service (free instance), started with `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`
- Database: Neon PostgreSQL, selected automatically when `DATABASE_URL` is set
- Frontend: Streamlit Community Cloud, pointed at the API through `API_URL`
- Required environment variables: GEMINI_API_KEY, SECRET_KEY, DATABASE_URL
- HTTPS is provided by both hosts

Free hosting puts idle services to sleep, so the first request after a quiet period can take about a minute.

## Roadmap

- Token revocation and rate limits on the AI endpoints
