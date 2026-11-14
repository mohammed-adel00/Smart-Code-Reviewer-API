# Smart Code Reviewer API

A backend microservice built with FastAPI, SQLModel and the Google Gemini API that performs automated security reviews on source code snippets. It looks for common vulnerabilities (RCE, SQL Injection, XSS, command injection, path traversal, hardcoded secrets), returns a structured JSON report with a suggested fix, and stores every scan in a local SQLite database.

> **Limitations:** the analysis is done by an LLM, so it can miss real vulnerabilities and can report ones that do not exist. Treat the output as a quick first pass, not a replacement for static analysis tools such as [Bandit](https://github.com/PyCQA/bandit) or [Semgrep](https://semgrep.dev), or for a human review. Submitted code is sent to Google's Gemini API, so do not submit code you are not allowed to share.

## Features

- **Security code analysis:** scans snippets for common AppSec vulnerabilities and logic flaws using Gemini.
- **Structured responses:** a Pydantic schema (with an enum for the risk level) forces consistent JSON from the model.
- **Prompt-injection hardening:** the code is passed as untrusted data inside a random per-request boundary, with a separate system instruction, and the `language` field is strictly validated.
- **Input limits:** empty snippets and snippets over 20,000 characters are rejected.
- **Scan history:** snippets, risk levels and feedback are persisted in SQLite; `/history` is paginated and newest-first.
- **Optional API-key auth:** set `API_KEY` and every request must send it in the `X-API-Key` header.
- **Safe failures:** if the AI call fails the API returns `502`, saves nothing, and keeps error details in the server log only.
- **Tests and CI:** pytest suite (the Gemini call is mocked) that runs on GitHub Actions.

## Tech Stack

- **Backend:** FastAPI, Uvicorn
- **Database / ORM:** SQLite, SQLModel
- **AI SDK:** Google GenAI (`gemini-2.5-flash` by default)
- **Language:** Python 3.10+

## Project Structure

```
Smart-Code-Reviewer-API/
├── main.py               # FastAPI app, auth, route handlers (/analyze, /history)
├── models.py             # Request validation + SQLModel table definitions
├── database.py           # SQLite engine setup and session dependency
├── ai_service.py         # Gemini client, system prompt, error handling
├── tests/                # pytest suite (Gemini is mocked)
├── requirements.txt      # Runtime dependencies
├── requirements-dev.txt  # Runtime + test dependencies
├── .env.example          # Template for environment variables
└── .github/workflows/    # CI
```

## Setup & Installation

1. **Clone the repository:**

```bash
git clone https://github.com/mohammed-adel00/-Smart-Code-Reviewer-API.git Smart-Code-Reviewer-API
cd Smart-Code-Reviewer-API
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables:** copy `.env.example` to `.env` and set at least your Gemini key:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | yes | - | Your Google Gemini API key |
| `GEMINI_MODEL` | no | `gemini-2.5-flash` | Gemini model name |
| `API_KEY` | no | unset (API is open) | If set, clients must send it as the `X-API-Key` header |
| `DATABASE_URL` | no | `sqlite:///reviews.db` | Database connection URL |
| `SQL_ECHO` | no | `false` | Log every SQL query (this includes submitted code) |

4. **Start the server:**

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to try the endpoints in Swagger UI.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/analyze` | Analyzes a code snippet for vulnerabilities and saves the result. |
| `GET` | `/history?limit=50&offset=0` | Returns stored scans, newest first (`limit` 1-200). |

### Example

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"code_snippet": "query = \"SELECT * FROM users WHERE id = \" + user_id", "language": "python"}'
```

Example response (the exact wording of `ai_feedback` will vary):

```json
{
  "id": 1,
  "code_snippet": "query = \"SELECT * FROM users WHERE id = \" + user_id",
  "language": "python",
  "security_status": "High Risk",
  "ai_feedback": "String concatenation builds the SQL query, which allows SQL injection. Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
  "created_at": "2026-11-14T16:00:00.123456Z"
}
```

`security_status` is always one of `Safe`, `Low Risk`, `High Risk`, `Critical Vulnerability`.

| Status | Meaning |
| --- | --- |
| `422` | Invalid input (empty or too long snippet, bad `language`) |
| `401` | `API_KEY` is configured and the header is missing or wrong |
| `502` | The AI model call failed; nothing was saved |

## Data Flow

```
Client ──POST /analyze──▶ main.py
                            │ validates payload (models.py) + API key
                            ▼
                         ai_service.py ──▶ Gemini API (system instruction + code in a random boundary)
                            │ parses and validates the JSON answer
                            ▼
                         database.py ──▶ reviews.db (CodeReviewRecord)
                            │
Client ◀──────JSON record───┘
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Roadmap

- Rate limiting per client
- Docker image
- Support for reviewing multiple files per request

## License

MIT, see [LICENSE](LICENSE).
