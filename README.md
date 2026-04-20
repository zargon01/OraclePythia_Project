# Oracle Pythia

> **LTIMindtree Blueverse Hackathon Project**

An AI-powered scripting assistant that converts plain English business rules into Oracle Fast Formulas, Groovy scripts, and JDE Business Function code — and explains existing customisations for impact analysis. Built to deliver a **60% reduction in custom development time** for Oracle HCM and Fusion environments.

---

## Problem Statement

**AI-Assisted Fast Formula & Groovy Scripting**

> Developers describe business rules in plain English; AI generates Oracle Fast Formulas (HCM), Groovy scripts (Fusion), or JDE Business Function code. AI also explains existing customizations for impact analysis. Pair with GitHub Copilot-style IDE integration for 60% faster custom development.
>
> ✓ 60% reduction in Dev Speed
> ✓ Conversion from Plain English to Formula

Writing Oracle Fast Formulas and Groovy scripts is a highly specialised, time-consuming skill. Developers must understand both the business rule and the exact syntax of the target scripting language — a context switch that slows every customisation cycle. Oracle Pythia eliminates that gap: describe what you want in plain English, get production-ready code back in seconds, with a full explanation alongside it.

---

## What Oracle Pythia Does

| Capability | Description |
|------------|-------------|
| **Plain English → Formula** | Describe a business rule in natural language; receive Oracle Fast Formula, Groovy, or JDE Business Function code instantly |
| **Code Explanation** | Paste existing customisation code and get a plain-English breakdown for impact analysis, audits, or onboarding |
| **Iterative Refinement** | Send existing code with a new instruction — the AI improves or extends it while preserving the original logic |
| **Multi-Agent Resilience** | Two Blueverse AI agents with automatic token fallback — keeps working through expiry or agent downtime without manual intervention |

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [What Oracle Pythia Does](#what-oracle-pythia-does)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Running the Project](#running-the-project)
- [Backend — API Reference](#backend--api-reference)
- [Backend — Fallback Strategy](#backend--fallback-strategy)
- [Backend — Configuration](#backend--configuration)
- [Troubleshooting](#troubleshooting)

---

## Project Structure

```
OraclePythia/
│
├── frontend/                        # React application (Vite)
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/                         # FastAPI server
│   ├── main.py                      # App entry point — routes and request handling
│   ├── config.py                    # All configuration (URLs, agent IDs, timeouts)
│   ├── requirements.txt             # Python dependencies
│   │
│   ├── auth/
│   │   ├── token_store.py           # In-memory token store with TTL + JWT validation
│   │   ├── bearer.py                # Playwright — captures bearer tokens headlessly
│   │   └── session.py               # Interactive login — saves browser session to disk
│   │
│   ├── agents/
│   │   └── runner.py                # Fallback chain — token selection and API calls
│   │
│   └── state/
│       └── auth.json                # Saved browser session (auto-created, git-ignored)
│
└── README.md                        # This file
```

---

## How It Works

```
User describes a business rule in plain English
            │
            ▼
    React frontend sends POST /chat to the backend
            │
            ▼
    Backend selects the best available token
    (primary token → fallback token → Playwright automation)
            │
            ▼
    Backend calls Blueverse Chat API (Agent 1 or Agent 2)
            │
            ▼
    LLM generates Oracle Fast Formula / Groovy / JDE code
    Response is parsed → code and explanation extracted
            │
            ▼
    Frontend displays generated code + explanation side by side
```

The backend maintains two Blueverse AI agents. If the primary agent's token is expired or the agent is unavailable, the backend automatically tries the fallback agent — and if that also fails, it silently captures a fresh token using a headless Playwright browser session. The whole fallback chain is invisible to the user.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite |
| Backend | Python, FastAPI, Uvicorn |
| AI / LLM | Blueverse Chat API (LTIMindtree) |
| Browser Automation | Playwright (Chromium) |
| HTTP | requests, CORS via FastAPI middleware |

---

## Prerequisites

Make sure you have the following installed before starting:

- **Node.js** v18 or higher — [nodejs.org](https://nodejs.org)
- **Python** 3.10 or higher — [python.org](https://python.org)
- **pip** — comes bundled with Python
- Access to the LTIMindtree Blueverse platform
- A terminal / command prompt

---

## Setup & Installation

### Backend Setup

**1. Navigate to the backend folder**
```bash
cd backend
```

**2. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**3. Install Playwright's browser binaries**

Playwright needs to download Chromium to run the headless browser for token automation.
```bash
playwright install
```
> Downloads ~150MB of browser binaries. Only needs to be done once per machine.

**4. Save a browser session (required before first run)**

This one-time step lets the backend fetch tokens automatically without opening a visible browser on every request. It opens a real browser for you to log in to Blueverse manually.

```bash
python -m auth.session
```

A browser window will open and navigate to the Blueverse login page. Log in, then return to the terminal and press ENTER. Your session is saved to `state/auth.json`.

> **Re-run this command whenever automation starts failing** (typically when the Blueverse session expires after a few days). You do not need to reinstall anything — just re-run this and restart the server.

---

### Frontend Setup

**1. Navigate to the frontend folder**
```bash
cd frontend
```

**2. Install dependencies**
```bash
npm install
```

---

## Running the Project

Both servers need to run simultaneously. Open two terminals.

**Terminal 1 — Start the backend**
```bash
cd backend
python -m uvicorn main:app
```
Backend runs on → `http://127.0.0.1:8000`

**Terminal 2 — Start the frontend**
```bash
cd frontend
npm run dev
```
Frontend runs on → `http://localhost:5173`

Open **`http://localhost:5173`** in your browser to use the app.

---

## Backend — API Reference

### `GET /`
Health check. Used by the frontend to confirm the backend is reachable.

**Response:**
```json
{ "status": "running" }
```

---

### `POST /token1`
Store the primary agent's bearer token. The frontend calls this after intercepting a token from its own Blueverse session, enabling faster requests without Playwright automation.

**Request:**
```json
{ "token": "eyJhbGciOiJSUzI1NiJ9..." }
```

| Status | Response |
|--------|----------|
| `200` | `{ "status": "primary token set" }` |
| `400` | `{ "detail": "Invalid token — must be a JWT" }` |

---

### `POST /token2`
Store the fallback agent's bearer token.

**Request:**
```json
{ "token": "eyJhbGciOiJSUzI1NiJ9..." }
```

| Status | Response |
|--------|----------|
| `200` | `{ "status": "fallback token set" }` |
| `400` | `{ "detail": "Invalid token — must be a JWT" }` |

---

### `POST /chat`
Submit a plain English query and receive generated code with an explanation. This is the main endpoint — the backend handles all token management and fallback automatically.

**Request body:**
```json
{
  "type": "script",
  "query": "Write an Oracle Fast Formula that checks if an employee is eligible for overtime based on their grade and hours worked",
  "current_code": ""
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | ✅ | Query type forwarded to the Blueverse API (e.g. `"script"`) |
| `query` | string | ✅ | Plain English description of the formula or rule to generate |
| `current_code` | string | ❌ | Existing code to refine, extend, or explain — included as context |

**Success response `200`:**
```json
{
  "status": "success",
  "code": "/* FAST FORMULA */\nIF GRADE = 'G5' AND HOURS_WORKED > 40 THEN...",
  "explanation": "This formula checks whether the employee's grade is G5 and their weekly hours exceed 40, returning Y for overtime eligibility.",
  "model": "gpt-4o",
  "response_time": 3.142,
  "backend_time": 2.891
}
```

| Field | Description |
|-------|-------------|
| `code` | The generated Oracle Fast Formula, Groovy, or JDE code |
| `explanation` | Plain English explanation of what the code does |
| `model` | Which model/agent served the response |
| `response_time` | Total wall-clock time for the full round trip (seconds) |
| `backend_time` | Execution time reported by the Blueverse API itself |

**Error responses:**

| Status | Meaning |
|--------|---------|
| `503` | All fallback strategies exhausted — check tokens and `auth.json` |
| `500` | Unexpected internal server error |

---

## Backend — Fallback Strategy

Every `/chat` request walks through up to 3 steps. The first `2xx` response wins and is returned immediately.

```
Primary frontend token available?
│
├── YES
│    Step 1: Primary agent + primary token
│            ├── 2xx  →  ✅ done
│            ├── 401  →  Token invalidated → Step 2
│            └── fail →  Step 2
│
│    Step 2: Fallback agent + fallback token (if stored)
│            ├── 2xx  →  ✅ done
│            ├── 401  →  Token invalidated → Step 3
│            └── fail →  Step 3
│
│    Step 3: Primary agent + Playwright automation token (cached)
│            ├── 2xx  →  ✅ done
│            └── fail →  ❌ 503 returned to frontend
│
└── NO (no frontend token set)
     Skips to Step 3 directly
     Step 3: Primary agent + Playwright automation token
             ├── 2xx  →  ✅ done
             └── fail →  ❌ 503 returned to frontend
```

The Playwright automation token is cached in memory for 30 minutes. The headless browser only launches when the cache is cold or expired — all other calls just read from memory with no performance cost.

---

## Backend — Configuration

All values are in `backend/config.py`. Nothing is hardcoded elsewhere.

| Variable | Default | Description |
|----------|---------|-------------|
| `TOKEN_TTL` | `1800` | Seconds a cached token stays valid before expiry (30 min) |
| `REQUEST_TIMEOUT` | `120` | Max seconds to wait per Blueverse API call |
| `PRIMARY_SPACE_NAME` | `Scripter_7c0c1e4b` | Blueverse space name for Agent 1 |
| `PRIMARY_FLOW_ID` | `69c4ca6b...` | Blueverse flow ID for Agent 1 |
| `FALLBACK_SPACE_NAME` | `BackupAgent_d8544a5f` | Blueverse space name for Agent 2 |
| `FALLBACK_FLOW_ID` | `69d3bae8...` | Blueverse flow ID for Agent 2 |

---

## Troubleshooting

**`auth.json not found` in backend logs**
Run `python -m auth.session` from the `backend/` directory, log in to Blueverse in the browser, press ENTER. Then restart the server with `uvicorn main:app`.

**`401 Bad token; invalid JSON` appearing in logs**
A stored frontend token has expired. The backend handles this automatically by moving to the next fallback step. To proactively fix it, have the frontend re-POST a fresh token to `/token1`.

**`503 Service Unavailable` returned to the frontend**
All three fallback steps failed. Check: (1) `state/auth.json` exists, (2) the Blueverse session is still valid — re-run `python -m auth.session` if needed, (3) the Blueverse API is reachable from your network.

**Playwright times out when capturing a token**
The saved browser session has expired. Re-run `python -m auth.session` to refresh it.

**Frontend shows `Network Error` or CORS error**
Make sure the backend is running on port `8000`. Allowed CORS origins in `backend/main.py` are `localhost:5173`, `localhost:3000`, and `127.0.0.1:5173`. If your frontend runs on a different port, add it to the `allow_origins` list.

**`playwright install` fails or Chromium won't launch**
Run `playwright install --with-deps` instead — this also installs OS-level browser dependencies needed on Linux or some Windows environments.
