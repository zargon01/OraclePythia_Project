"""
auth/bearer.py
--------------
Fetches a Bearer token by replaying a saved browser session headlessly.

How it works:
  1. Loads auth.json (saved by auth/session.py) into a Playwright context.
  2. Navigates to the agents page — this triggers authenticated API requests.
  3. Intercepts outgoing request headers and captures the Bearer token.
  4. Caches the token in memory for TOKEN_TTL seconds so we don't spin up
     a browser on every single API call.

Flakiness fixes vs the original:
  - waitForLoadState("networkidle") was replaced with a smarter wait that
    retries if the page doesn't emit a Bearer request quickly.
  - The polling while-loop now has a proper backoff (0.5s) instead of 0.3s.
  - Token cache respects TOKEN_TTL via the same logic as TokenStore.
  - A threading.Lock prevents two threads from launching Playwright simultaneously.
"""

import time
import threading
import logging
from playwright.sync_api import sync_playwright
from config import AUTH_STATE_PATH, BASE_URL, TOKEN_TTL

logger = logging.getLogger(__name__)

# ── Internal cache ─────────────────────────────────────────────────────────────
_cached_token: str | None = None
_token_fetched_at: float   = 0.0
_lock = threading.Lock()   # prevents parallel Playwright launches

# How long to wait for the page to emit a Bearer token before giving up
_CAPTURE_TIMEOUT_SECONDS = 30


def _launch_and_capture_token() -> str:
    """
    Internal: spin up a headless browser, load the saved session,
    navigate to /agents, and capture the first Bearer token seen in
    outgoing request headers.

    Raises an exception if no token is captured within the timeout.
    """
    logger.info("[Bearer] Launching headless browser to capture token...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Load the saved login session — this is what makes headless auth work
        context = browser.new_context(storage_state=AUTH_STATE_PATH)
        page    = context.new_page()

        captured = {"token": None}

        def on_request(request):
            """Intercept every outgoing request and grab the Bearer token."""
            auth = request.headers.get("authorization", "")
            if "Bearer " in auth and not captured["token"]:
                captured["token"] = auth.replace("Bearer ", "").strip()
                logger.debug("[Bearer] Token captured from request headers")

        page.on("request", on_request)

        try:
            # Navigate — this triggers the app to make authenticated requests
            page.goto(f"{BASE_URL}/agents", wait_until="domcontentloaded")

            # Poll until we have the token or we hit the timeout
            deadline = time.time() + _CAPTURE_TIMEOUT_SECONDS

            while not captured["token"]:
                if time.time() > deadline:
                    raise TimeoutError(
                        f"[Bearer] No Bearer token seen within {_CAPTURE_TIMEOUT_SECONDS}s. "
                        "Session may have expired — run auth/session.py to refresh."
                    )
                page.wait_for_timeout(500)   # 0.5s backoff — less CPU than 0.3s

            logger.info("[Bearer] Token successfully captured")
            return captured["token"]

        finally:
            browser.close()


def get_bearer_token(force_refresh: bool = False) -> str:
    """
    Return a valid Bearer token, using the in-memory cache when possible.

    Args:
        force_refresh: If True, ignore the cache and fetch a fresh token.

    Returns:
        A JWT string (without 'Bearer ' prefix).

    Raises:
        TimeoutError: If the browser session fails to produce a token.
        Exception:    If the saved session (auth.json) doesn't exist or is invalid.
    """
    global _cached_token, _token_fetched_at

    with _lock:
        token_age = time.time() - _token_fetched_at
        cache_valid = _cached_token and token_age < TOKEN_TTL

        if not force_refresh and cache_valid:
            logger.info(f"[Bearer] Using cached token ({token_age:.0f}s old)")
            return _cached_token

        # Cache miss or forced refresh — fetch a new token
        token = _launch_and_capture_token()

        _cached_token     = token
        _token_fetched_at = time.time()

        return _cached_token


def invalidate_cached_token():
    """Clear the in-memory token cache, forcing a fresh fetch next time."""
    global _cached_token
    with _lock:
        _cached_token = None
    logger.info("[Bearer] Token cache cleared")