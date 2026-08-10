# PII Privacy Middleware

Local FastAPI middleware that removes detected English PII before forwarding a prompt to an OpenAI-compatible Chat Completions API. It holds token mappings encrypted with a unique in-memory Fernet key per session and restores exact tokens in the model response.

## Setup

1. Create the environment: `py -3.14 -m venv .venv`
2. Activate it: `.\.venv\Scripts\Activate.ps1`
3. Install dependencies: `python -m pip install --upgrade pip` then `python -m pip install -e ".[dev]"`
4. Install the language model: `python -m spacy download en_core_web_lg`
5. Copy `.env.example` to `.env` and set `MODEL_BASE_URL`, `MODEL_NAME`, and, where needed, `MODEL_API_KEY`.
6. Run: `uvicorn app.main:app --host 127.0.0.1 --port 8000`

The API is intentionally local-development only and has no authentication. Do not expose it publicly.

## Usage

Create a session:

```powershell
$session = Invoke-RestMethod -Method Post http://127.0.0.1:8000/sessions
```

Send a message. The provider receives placeholders, never the originals:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/sessions/$($session.session_id)/messages" `
  -ContentType 'application/json' `
  -Body '{"role":"user","content":"Email alex@example.com about the appointment."}'
```

Close the session as soon as the conversation is complete:

```powershell
Invoke-RestMethod -Method Delete "http://127.0.0.1:8000/sessions/$($session.session_id)"
```

Sessions also expire after `SESSION_TTL_SECONDS` (15 minutes by default). A process restart removes every session and makes its encrypted mappings unrecoverable.

## Security model and limitations

- The middleware protects only PII recognized by Presidio. Review detection quality before production use.
- The process briefly handles plaintext while analyzing a request, then retains it only as Fernet ciphertext in memory until session deletion/expiry.
- Redacted conversation history remains in memory; it has no original PII values.
- Logs include only session IDs, entity counts, and safe error categories.
- Run a single process: the memory store is not shared across instances.
