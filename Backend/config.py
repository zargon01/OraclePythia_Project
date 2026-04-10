"""
config.py
---------
Central configuration for the Blueverse API wrapper.
All environment-specific values live here — nothing hardcoded elsewhere.
"""

import os

# ── Paths ──────────────────────────────────────────────────────────────────────
# BASE_DIR points two levels up from this file (project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Playwright saves the logged-in browser session here so we don't re-login every time
AUTH_STATE_PATH = os.path.join(BASE_DIR,"Backend", "state", "auth.json")
# AUTH_STATE_PATH = os.path.join(BASE_DIR, "state", "auth.json")

# ── API Endpoints ──────────────────────────────────────────────────────────────
BASE_URL = "https://blueverse-foundry.ltimindtree.com"
CHAT_API  = f"{BASE_URL}/chatservice/chat"

# ── Primary Agent (Agent 1) ────────────────────────────────────────────────────
PRIMARY_SPACE_NAME = "Scripter_7c0c1e4b"
PRIMARY_FLOW_ID    = "69c4ca6b8bbe8031ba495dd9"

# ── Fallback Agent (Agent 2) ───────────────────────────────────────────────────
FALLBACK_SPACE_NAME = "BackupAgent_d8544a5f"
FALLBACK_FLOW_ID    = "69d3bae8ea80f1bdfe45e207"

# ── Token Settings ─────────────────────────────────────────────────────────────
TOKEN_TTL       = 1800  # seconds — cached bearer token is reused for 30 minutes
REQUEST_TIMEOUT = 120  # seconds — the chat API can be slow; 2 minutes per attempt