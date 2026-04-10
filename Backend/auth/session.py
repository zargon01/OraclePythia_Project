"""
auth/session.py
---------------
Saves a logged-in browser session to disk (auth.json).

IMPORTANT — this must be run BEFORE starting the uvicorn server.
It cannot be called from inside a running web request because it uses
input() to wait for manual login, which will block the server thread.

Run it once from a terminal:

    python -m auth.session

Then start the server normally:

    uvicorn main:app

Re-run it whenever the session expires and automation starts failing.
"""

import os
import sys
import logging
from playwright.sync_api import sync_playwright
from config import AUTH_STATE_PATH, BASE_URL

logger = logging.getLogger(__name__)


def save_session():
    """
    Open a visible browser, let the user log in, then save the session to disk.

    Ensures the state/ directory exists before writing.
    Raises RuntimeError if called from a non-interactive context (no TTY),
    which prevents the server from hanging if this is mistakenly called
    from inside a web request.
    """
    # Guard: refuse to run if there's no terminal to interact with
    if not sys.stdin.isatty():
        raise RuntimeError(
            "save_session() requires an interactive terminal. "
            "Run `python -m auth.session` before starting the server."
        )

    # Make sure the state/ directory exists before trying to write to it
    state_dir = os.path.dirname(AUTH_STATE_PATH)
    os.makedirs(state_dir, exist_ok=True)
    logger.info(f"[Session] State directory ready: {state_dir}")

    logger.info("[Session] Launching browser for manual login...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()   # always fresh — don't load stale state
        page    = context.new_page()

        page.goto(f"{BASE_URL}/agents")

        print("\n" + "="*60)
        print("  Log in manually in the browser window.")
        print("  Once fully logged in, come back here and press ENTER.")
        print("="*60 + "\n")
        input("  Press ENTER when ready > ")

        # Persist cookies + localStorage for headless reuse
        context.storage_state(path=AUTH_STATE_PATH)
        logger.info(f"[Session] Session saved → {AUTH_STATE_PATH}")

        browser.close()

    print(f"\n✅  Session saved to {AUTH_STATE_PATH}")
    print("   You can now start the server: uvicorn main:app\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    save_session()