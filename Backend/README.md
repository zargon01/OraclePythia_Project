# Oracle Pythia — Backend

A FastAPI server that wraps the Blueverse chat API. It handles authentication automatically — intercepting bearer tokens from a saved browser session when no frontend token is available — and uses a multi-step fallback strategy to keep requests working even when individual tokens expire or agents are unavailable.

---

## Table of Contents

- [Project Structure](#project-structure)
- [File Reference](#file-reference)
- [How sa as It Works](#how-it-works)
- [Fallback Strategy](#fallback-strategy)
- [Token Lifecycle](#token-lifecycle)
- [API Endpoints](#api-endpoints)
- [Setup & Running](#setup--running)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Project Structure

```
Backend/
│
├── main.py                  # FastAPI app — routes, schemas, request handling
├── config.py                # All configuration (URLs, agent IDs, timeouts)
├── requirements.txt         # Python dependencies
├── readme.md                # Backend Documentation
│
├── auth/
│   ├── token_store.py       # In-memory token store with TTL expiry + JWT validation
│   ├── bearer.py            # Playwright headless browser — captures bearer tokens
│   └── session.py           # Interactive browser login — saves auth.json to disk
│
├── agents/
│   └── runner.py            # Fallback chain — decides which token/agent to use
│
└── state/
    └── auth.json            # Saved browser session (created by auth/session.py)
```

---

## File Reference

### `main.py`
The entry point. Kept intentionally thin — only handles HTTP routing and request/response shaping. Contains:
- FastAPI app setup and CORS configuration
- Request schemas (`ChatRequest`, `TokenRequest`)
- Route handlers for all 4 endpoints
- `_parse_llm_response()` — strips markdown fences and parses the LLM's JSON output
- A log filter that suppresses `GET /` health check spam from the terminal

### `config.py`
Single source of truth for all configuration values. Nothing is hardcoded elsewhere. Contains:
- `BASE_URL` / `CHAT_API` — the Blueverse API endpoint
- `PRIMARY_SPACE_NAME` / `PRIMARY_FLOW_ID` — Agent 1 identifiers
- `FALLBACK_SPACE_NAME` / `FALLBACK_FLOW_ID` — Agent 2 identifiers
- `TOKEN_TTL` — how long a cached bearer token stays valid (default: 1800s / 30 min)
- `REQUEST_TIMEOUT` — max wait per HTTP request to the chat API (default: 120s)
- `AUTH_STATE_PATH` — path to `state/auth.json`

### `auth/token_store.py`
Thread-safe in-memory store for the two frontend-supplied bearer tokens (`primary` and `fallback`). Key properties:
- Validates that every stored token is a proper JWT (3-part structure) at set-time — rejects garbage values immediately
- Auto-expires tokens after `TOKEN_TTL` seconds — stale tokens are never silently reused
- Exposes `set(agent, token)`, `get(agent)`, and `invalidate(agent)` methods
- A single shared `token_store` instance is imported across the app

### `auth/bearer.py`
Uses Playwright to capture a bearer token from a live browser session. Key properties:
- Loads `auth.json` into a headless Chromium context — no visible browser, no manual login
- Intercepts outgoing request headers and extracts the first `Bearer` token seen
- Caches the captured token in memory for `TOKEN_TTL` seconds — Playwright only launches when the cache is cold or expired
- `get_bearer_token(force_refresh=False)` — main entry point; respects the cache by default
- `invalidate_cached_token()` — clears the cache if needed

### `auth/session.py`
One-time interactive tool for creating `auth.json`. Opens a real (visible) browser, waits for manual login, then saves the browser's cookies and localStorage to disk. Must be run from a terminal before starting the server — it uses `input()` and will refuse to run if there is no TTY (preventing server hangs). Run with `python -m auth.session`.

### `agents/runner.py`
The core fallback logic. Contains the `call_chat_api(query_type, query)` function which is called by every `/chat` request. Implements the 3-step strategy described below. Also handles 401 token invalidation — if a token gets a 401, it is immediately removed from the store so it won't be retried.

---

## How It Works

A `/chat` request flows through the system like this:

```
Frontend
   │
   ▼
main.py  (/chat)
   │  Builds the final query string (appends current_code + JSON format instruction)
   │
   ▼
agents/runner.py  (call_chat_api)
   │  Decides which token and agent to use (see Fallback Strategy)
   │  Makes the HTTP request to Blueverse chat API
   │
   ├── Token from auth/token_store.py   (frontend-supplied, TTL-aware)
   │   or
   └── Token from auth/bearer.py        (Playwright automation, cached)
          │
          └── Uses state/auth.json      (saved browser session)
   │
   ▼
Blueverse Chat API
   │  Returns: { response, responseSource, execution_time }
   │
   ▼
main.py
   │  Parses LLM output JSON → extracts code + explanation
   │
   ▼
Frontend  ← { status, code, explanation, model, response_time, backend_time }
```

## Fallback Strategy

Every `/chat` request goes through up to 3 steps. The first successful `2xx` response is returned immediately.

```
Is a primary frontend token stored?
│
├── YES
│    └── Step 1: POST to Primary Agent using primary token
│              ├── 2xx  →  ✅ Done
│              ├── 401  →  Invalidate primary token, continue to Step 2
│              └── fail →  Continue to Step 2
│
│         Step 2: POST to Fallback Agent using fallback token (if stored)
│                   ├── 2xx  →  ✅ Done
│                   ├── 401  →  Invalidate fallback token, continue to Step 3
│                   └── fail →  Continue to Step 3
│
│         Step 3: POST to Primary Agent using automation token (Playwright)
│                   ├── 2xx  →  ✅ Done
│                   └── fail →  ❌ 503 returned to frontend
│
└── NO (no primary token set)
     └── Step 3 directly: POST to Primary Agent using automation token
                   ├── 2xx  →  ✅ Done
                   └── fail →  ❌ 503 returned to frontend
```

**Key rules:**
- Frontend tokens are always preferred — automation is only used as a last resort
- A `401` response immediately invalidates that token from the store
- The automation token is cached in memory — Playwright only launches when the cache is cold or expired (every 30 minutes at most)
- Steps 1 and 2 use different agents (Primary vs Fallback) with their respective tokens

---

## Token Lifecycle

There are two types of tokens in the system:

**Frontend tokens** (set via `/token1` and `/token2`)
- Supplied by the frontend after it logs in to Blueverse
- Stored in `TokenStore` in memory
- Validated as JWTs on arrival — rejected immediately if malformed
- Auto-expire after `TOKEN_TTL` seconds (30 min)
- Invalidated immediately on a `401` response

**Automation token** (captured by Playwright)
- Captured headlessly using the saved `auth.json` session
- Cached in memory inside `auth/bearer.py` for `TOKEN_TTL` seconds
- A new browser is only launched when the cache is expired or `force_refresh=True`
- Requires `state/auth.json` to exist — created once via `python -m auth.session`

---

## API Endpoints

### `GET /`
Health check. Returns `{ "status": "running" }`. Hits to this endpoint are suppressed from the terminal log to reduce noise.

---

### `POST /token1`
Store the primary agent's bearer token (provided by the frontend after login).

**Request body:**
```json
{ "token": "eyJhbGciOiJSUzI1NiJ9..." }
```

**Responses:**
| Status | Body |
|--------|------|
| `200` | `{ "status": "primary token set" }` |
| `400` | `{ "detail": "Invalid token — must be a JWT" }` |

---

### `POST /token2`
Store the fallback agent's bearer token.

**Request body:**
```json
{ "token": "eyJhbGciOiJSUzI1NiJ9..." }
```

**Responses:**
| Status | Body |
|--------|------|
| `200` | `{ "status": "fallback token set" }` |
| `400` | `{ "detail": "Invalid token — must be a JWT" }` |

---

### `POST /chat`
Send a query to the Blueverse chat API. The runner handles token selection and fallback automatically.

**Request body:**
```json
{
  "type": "script",
  "query": "Write a Python function that reverses a string",
  "current_code": "def foo(): pass"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | ✅ | Query type passed to the Blueverse API |
| `query` | string | ✅ | The user's question or instruction |
| `current_code` | string | ❌ | Existing code to include as context |

**Success response `200`:**
```json
{
  "status": "success",
  "code": "def reverse_string(s): return s[::-1]",
  "explanation": "Uses Python slice notation to reverse the string.",
  "model": "gpt-4o",
  "response_time": 3.142,
  "backend_time": 2.891
}
```

| Field | Description |
|-------|-------------|
| `code` | Extracted code from LLM output |
| `explanation` | Extracted explanation from LLM output |
| `model` | Which model/agent served the response (`responseSource` from Blueverse) |
| `response_time` | Total wall-clock time for the whole request (seconds) |
| `backend_time` | Execution time reported by the Blueverse API itself |

**Error responses:**
| Status | Meaning |
|--------|---------|
| `503` | All fallback strategies exhausted — check tokens and auth.json |
| `500` | Unexpected internal error |

---

## Setup & Running

### 1. Install dependencies
```bash
pip install fastapi uvicorn playwright requests pydantic
playwright install chromium
```

### 2. Save a browser session (first time only)
This must be done before starting the server. It opens a real browser for you to log in manually.
```bash
python -m auth.session
```
Log in to Blueverse in the browser window, then press ENTER in the terminal. This creates `state/auth.json`. Re-run this command whenever the session expires and automation starts failing.

### 3. Start the server
```bash
uvicorn main:app
```
The server runs on `http://127.0.0.1:8000` by default.

### 4. (Optional) Supply frontend tokens
If the frontend has an active Blueverse session, POST the tokens immediately after login for faster responses (skips Playwright):
```bash
curl -X POST http://localhost:8000/token1 -H "Content-Type: application/json" -d '{"token": "eyJ..."}'
curl -X POST http://localhost:8000/token2 -H "Content-Type: application/json" -d '{"token": "eyJ..."}'
```

---

## Configuration

All values are in `config.py`. The ones you're most likely to need to change:

| Variable | Default | Description |
|----------|---------|-------------|
| `TOKEN_TTL` | `1800` | Seconds before a cached token is considered expired |
| `REQUEST_TIMEOUT` | `120` | Seconds to wait for a single chat API response |
| `PRIMARY_SPACE_NAME` | `Scripter_7c0c1e4b` | Blueverse space for Agent 1 |
| `PRIMARY_FLOW_ID` | `69c4ca6b...` | Blueverse flow ID for Agent 1 |
| `FALLBACK_SPACE_NAME` | `BackupAgent_d8544a5f` | Blueverse space for Agent 2 |
| `FALLBACK_FLOW_ID` | `69d3bae8...` | Blueverse flow ID for Agent 2 |

---

## Troubleshooting

**`auth.json not found` in logs**
Run `python -m auth.session` from a terminal, log in, press ENTER. Then restart the server.

**`Bad token; invalid JSON` (401) from Blueverse**
The stored frontend token has expired. The runner will automatically fall through to the next step. To fix proactively, re-POST a fresh token to `/token1` or `/token2`.

**All steps exhausted / `503` returned**
Both frontend tokens have failed and Playwright automation also failed. Check: (1) `state/auth.json` exists, (2) the Blueverse session in auth.json hasn't expired (re-run `python -m auth.session`), (3) the Blueverse API itself is reachable.

**Playwright times out capturing a token**
The saved session has likely expired. Re-run `python -m auth.session` to refresh it.

**Multiple browser windows opening**
This should not happen with the current code — `save_session()` is never called mid-request. If it does occur, check that you're running the latest `agents/runner.py`.
