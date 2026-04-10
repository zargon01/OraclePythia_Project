"""
agents/runner.py
----------------
Fallback strategy (in order):

  Step 1 — Primary agent,  frontend token       (fast, no browser)
  Step 2 — Fallback agent, fallback token        (fast, no browser)
  Step 3 — Primary agent,  automation token      (Playwright, uses cache)

Rules:
  - If frontend (primary) token is not set        → skip straight to step 3
  - If frontend (primary) token is set but fails  → try fallback token (step 2)
  - If fallback token also fails                  → use automation (step 3)
  - Automation token is cached for TOKEN_TTL — no new browser on every call

In other words: frontend tokens are always preferred; automation is the last
resort and is never used if a frontend token is available and working.
"""

import os
import json
import logging
import requests

from config import (
    CHAT_API,
    AUTH_STATE_PATH,
    PRIMARY_SPACE_NAME, PRIMARY_FLOW_ID,
    FALLBACK_SPACE_NAME, FALLBACK_FLOW_ID,
    REQUEST_TIMEOUT,
)
from auth.token_store import token_store
from auth.bearer import get_bearer_token

logger = logging.getLogger(__name__)

PRIMARY_AGENT  = {"name": "primary",  "space": PRIMARY_SPACE_NAME,  "flow": PRIMARY_FLOW_ID}
FALLBACK_AGENT = {"name": "fallback", "space": FALLBACK_SPACE_NAME, "flow": FALLBACK_FLOW_ID}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize_token(token: str) -> str:
    """Ensure the token has a 'Bearer ' prefix."""
    token = token.strip()
    return token if token.startswith("Bearer ") else f"Bearer {token}"


def _post(token: str, query_type: str, query: str, agent: dict) -> requests.Response:
    """POST one request to the chat API. Raises on timeout or network error."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": _normalize_token(token),
    }
    payload = {
        "query":      json.dumps({"type": query_type, "content": query}),
        "space_name": agent["space"],
        "flowId":     agent["flow"],
    }

    logger.info(f"[Runner] POST → space={agent['space']}")
    resp = requests.post(CHAT_API, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    logger.info(f"[Runner] {resp.status_code} ← space={agent['space']}")

    if not resp.ok:
        logger.warning(f"[Runner] Body: {resp.text[:300]}")

    return resp


def _get_automation_token() -> str | None:
    """
    Return a cached Playwright bearer token, fetching a new one if needed.
    Returns None (and logs clearly) if auth.json doesn't exist.
    """
    if not os.path.exists(AUTH_STATE_PATH):
        logger.error(
            "[Runner] auth.json missing — run `python -m auth.session` "
            "before starting the server."
        )
        return None

    try:
        # get_bearer_token() uses its own in-memory cache (TOKEN_TTL)
        # so this only launches Playwright when the cache is cold/expired
        token = get_bearer_token()
        logger.info("[Runner] Automation token ready (cached or freshly fetched)")
        return token
    except Exception as e:
        logger.warning(f"[Runner] Automation fetch failed: {e} — retrying with force_refresh")

    try:
        token = get_bearer_token(force_refresh=True)
        logger.info("[Runner] Automation token ready after force refresh")
        return token
    except Exception as e2:
        logger.error(f"[Runner] Automation force refresh also failed: {e2}")

    return None


# ── Main Entry Point ───────────────────────────────────────────────────────────

def call_chat_api(query_type: str, query: str) -> requests.Response:
    """
    Call the chat API using the strategy described at the top of this file.

    Short summary:
      1. Use primary frontend token if available
      2. On failure, use fallback token
      3. On failure, use automation token (Playwright, cached)
    """

    primary_token  = token_store.get("primary")
    fallback_token = token_store.get("fallback")

    # ── Step 1: Primary frontend token ────────────────────────────────────────
    if primary_token:
        logger.info("[Runner] ── Step 1: Primary agent | primary frontend token")
        try:
            resp = _post(primary_token, query_type, query, PRIMARY_AGENT)
            if resp.ok:
                logger.info("[Runner] Step 1 succeeded ✅")
                return resp

            # Token is definitively rejected — drop it so it isn't retried
            if resp.status_code == 401:
                logger.warning("[Runner] Step 1: 401 — invalidating primary token")
                token_store.invalidate("primary")

            logger.warning(f"[Runner] Step 1 failed ({resp.status_code}) → trying fallback token")

        except requests.Timeout:
            logger.warning("[Runner] Step 1: timed out → trying fallback token")
        except Exception as e:
            logger.warning(f"[Runner] Step 1: error ({e}) → trying fallback token")

    else:
        # No frontend token at all — skip straight to automation
        logger.info("[Runner] No primary frontend token → skipping to automation (Step 3)")
        token = _get_automation_token()
        if token:
            try:
                resp = _post(token, query_type, query, PRIMARY_AGENT)
                if resp.ok:
                    logger.info("[Runner] Automation (early) succeeded ✅")
                    return resp
            except requests.Timeout:
                logger.warning("[Runner] Automation (early): timed out")
            except Exception as e:
                logger.warning(f"[Runner] Automation (early): error — {e}")

        raise RuntimeError(
            "No frontend token was set and automation failed. "
            "Check auth.json or supply a token via POST /token1."
        )

    # ── Step 2: Fallback frontend token ───────────────────────────────────────
    if fallback_token:
        logger.info("[Runner] ── Step 2: Fallback agent | fallback frontend token")
        try:
            resp = _post(fallback_token, query_type, query, FALLBACK_AGENT)
            if resp.ok:
                logger.info("[Runner] Step 2 succeeded ✅")
                return resp

            if resp.status_code == 401:
                logger.warning("[Runner] Step 2: 401 — invalidating fallback token")
                token_store.invalidate("fallback")

            logger.warning(f"[Runner] Step 2 failed ({resp.status_code}) → trying automation")

        except requests.Timeout:
            logger.warning("[Runner] Step 2: timed out → trying automation")
        except Exception as e:
            logger.warning(f"[Runner] Step 2: error ({e}) → trying automation")
    else:
        logger.info("[Runner] No fallback frontend token → trying automation")

    # ── Step 3: Automation token on primary agent ──────────────────────────────
    logger.info("[Runner] ── Step 3: Primary agent | automation token")
    token = _get_automation_token()
    if token:
        try:
            resp = _post(token, query_type, query, PRIMARY_AGENT)
            if resp.ok:
                logger.info("[Runner] Step 3 succeeded ✅")
                return resp
            logger.error(f"[Runner] Step 3 failed ({resp.status_code})")
        except requests.Timeout:
            logger.error("[Runner] Step 3: timed out")
        except Exception as e:
            logger.error(f"[Runner] Step 3: error — {e}")

    raise RuntimeError(
        "All fallback strategies exhausted. "
        "Check that auth.json exists and at least one token is valid."
    )