"""
auth/token_store.py
-------------------
In-memory token store with built-in TTL expiry and JWT structure validation.

Why this exists:
  The old tokenStore.py was a plain dict with no expiry and no validation.
  Stale or garbage tokens were silently kept and used, causing mysterious 401s.
  This class fixes that by:
    - Rejecting tokens that don't look like JWTs at set-time
    - Auto-expiring tokens after TOKEN_TTL seconds
    - Providing a clean get/set/invalidate interface
"""

import time
import threading
import logging
from config import TOKEN_TTL

logger = logging.getLogger(__name__)


def _is_valid_jwt(token: str) -> bool:
    """
    Returns True if `token` looks like a valid JWT (3 dot-separated parts).
    Strips a leading 'Bearer ' prefix before checking.
    Rejects obviously bad values like 'null', 'undefined', or empty string.
    """
    if not token:
        return False

    token = token.strip()

    # Reject placeholder strings that sometimes come from JS frontends
    if token.lower() in {"null", "undefined", ""}:
        return False

    # Strip the Bearer prefix if present before checking structure
    if token.startswith("Bearer "):
        token = token[7:]

    # A JWT always has exactly 3 parts: header.payload.signature
    return len(token.split(".")) == 3


class TokenStore:
    """
    Thread-safe store for bearer tokens keyed by agent name.

    Usage:
        store = TokenStore()
        store.set("primary", "eyJ...")
        token = store.get("primary")   # None if missing or expired
        store.invalidate("primary")
    """

    def __init__(self):
        # Each entry: { "token": str, "set_at": float }
        self._store: dict[str, dict] = {}
        self._lock = threading.Lock()

    def set(self, agent: str, token: str) -> bool:
        """
        Store a token for `agent`.
        Returns True on success, False if the token fails validation.
        """
        if not _is_valid_jwt(token):
            logger.warning(f"[TokenStore] Rejected invalid token for '{agent}'")
            return False

        with self._lock:
            self._store[agent] = {
                "token": token.strip(),
                "set_at": time.time()
            }

        logger.info(f"[TokenStore] Token set for '{agent}'")
        return True

    def get(self, agent: str) -> str | None:
        """
        Return the stored token for `agent`, or None if:
          - No token has been set
          - The token has exceeded TOKEN_TTL seconds
        """
        with self._lock:
            entry = self._store.get(agent)

            if not entry:
                return None

            age = time.time() - entry["set_at"]

            if age > TOKEN_TTL:
                logger.info(f"[TokenStore] Token for '{agent}' expired ({age:.0f}s old) — clearing")
                del self._store[agent]
                return None

            return entry["token"]

    def invalidate(self, agent: str):
        """Force-remove the stored token for `agent`."""
        with self._lock:
            self._store.pop(agent, None)
        logger.info(f"[TokenStore] Token invalidated for '{agent}'")


# ── Singleton ─────────────────────────────────────────────────────────────────
# One shared instance used across the whole app.
# Import this directly: `from auth.token_store import token_store`
token_store = TokenStore()