"""
main.py
-------
FastAPI entry point for the Blueverse API wrapper.

This file is intentionally thin — it only handles:
  - Route definitions
  - Request/response schemas
  - Calling into the agents layer

All business logic lives in agents/runner.py and auth/.

Endpoints:
  POST /token1   — Set the primary agent's frontend token
  POST /token2   — Set the fallback agent's frontend token
  POST /chat     — Submit a query to the chat API
  GET  /         — Health check
"""

import json
import logging
import time
from typing import Optional

# ── Suppress health check spam in uvicorn access logs ─────────────────────────
# uvicorn logs every GET / hit at INFO level, which floods the terminal when
# the frontend polls the health check frequently. This filter drops those lines.

class _SuppressHealthCheck(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # The uvicorn access log message looks like: '127.0.0.1:PORT - "GET / HTTP/1.1" 200'
        return "GET / " not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(_SuppressHealthCheck())
# ──────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth.token_store import token_store
from agents.runner import call_chat_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Blueverse API Wrapper")

# Allow local dev frontends to call this API directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Schemas ─────────────────────────────────────────────────

class TokenRequest(BaseModel):
    token: str

class ChatRequest(BaseModel):
    type: str
    query: str
    current_code: Optional[str] = None  # if provided, appended to the query


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_llm_response(raw: str) -> tuple[str, str]:
    """
    The LLM is instructed to return JSON: { "code": "...", "explanation": "..." }
    This function attempts to parse that JSON.

    Returns:
        (code, explanation) — falls back to (raw, "") if parsing fails.
    """
    if not raw:
        return "", ""

    # Strip markdown code fences if the model ignored instructions
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed.get("code", raw), parsed.get("explanation", "")
    except Exception:
        logger.warning("[Main] LLM output was not valid JSON — returning raw response as code")

    return raw, ""


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    """Simple health check — confirms the server is running."""
    return {"status": "running"}


@app.post("/token1")
def set_primary_token(req: TokenRequest):
    """
    Store the primary agent's Bearer token (provided by the frontend).
    The token is validated before storing — invalid tokens are rejected with 400.
    """
    success = token_store.set("primary", req.token)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid token — must be a JWT")

    return {"status": "primary token set"}


@app.post("/token2")
def set_fallback_token(req: TokenRequest):
    """
    Store the fallback agent's Bearer token (provided by the frontend).
    The token is validated before storing — invalid tokens are rejected with 400.
    """
    success = token_store.set("fallback", req.token)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid token — must be a JWT")

    return {"status": "fallback token set"}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Main chat endpoint. Sends the query to the chat API via the agent runner
    (which handles token management and multi-step fallback automatically).

    Request body:
        type         — query type string (passed through to the chat API)
        query        — the user's question or instruction
        current_code — optional existing code to include in the query context

    Response:
        status        — "success"
        code          — extracted code string from LLM output
        explanation   — extracted explanation string from LLM output
        model         — which model/source served the response
        response_time — total wall-clock time in seconds
        backend_time  — execution time reported by the chat API itself
    """
    start = time.time()

    # Build the final query — append current_code if provided
    final_query = req.query

    if req.current_code:
        final_query += f"\n\nExisting Code:\n{req.current_code}"

    # Remind the LLM to return structured JSON (same instruction as before)
    final_query += """

DO NOT include markdown, backticks, or extra text.
The "code" field in your response MUST contain only the code, without any markdown formatting or explanations.
Return EXACTLY this JSON format:
{
  "code": "<string>",
  "explanation": "<string>"
}
Do not add extra keys. Do not escape JSON.
If code is provided in input, you MUST include it in the output "code" field exactly or improved. Do not omit it.
"""

    try:
        response = call_chat_api(req.type, final_query)
    except RuntimeError as e:
        logger.error(f"[Main] All strategies failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"[Main] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Parse the outer API envelope
    try:
        data = response.json()
    except Exception:
        data = {}

    raw_output   = data.get("response", "")
    model        = data.get("responseSource", "unknown")
    backend_time = data.get("execution_time", None)

    code, explanation = _parse_llm_response(raw_output)

    return {
        "status":       "success",
        "code":         code,
        "explanation":  explanation,
        "model":        model,
        "response_time": round(time.time() - start, 3),
        "backend_time": backend_time,
    }