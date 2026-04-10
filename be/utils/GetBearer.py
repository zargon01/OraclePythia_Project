import time
import threading
from playwright.sync_api import sync_playwright
from utils.config import AUTH_STATE_PATH, BASE_URL, TOKEN_TTL

_cached_token = None
_token_time = 0
_lock = threading.Lock()


def _fetch_new_token(headless=True) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        context = browser.new_context(
            storage_state=AUTH_STATE_PATH
        )

        page = context.new_page()

        token_holder = {"token": None}

        def handle_request(request):
            auth = request.headers.get("authorization")
            if auth and "Bearer" in auth:
                token_holder["token"] = auth.split("Bearer ")[-1]

        page.on("request", handle_request)

        try:
            page.goto(f"{BASE_URL}/agents")
            page.wait_for_load_state("networkidle")

            # Minimal trigger
            page.wait_for_timeout(3000)

            start = time.time()
            timeout = 30

            while not token_holder["token"]:
                if time.time() - start > timeout:
                    raise Exception("❌ Token capture timeout")
                page.wait_for_timeout(300)

            return token_holder["token"]

        finally:
            browser.close()


def get_bearer_token(force_refresh=False) -> str:
    global _cached_token, _token_time

    with _lock:  # 🔥 prevents race condition
        if not force_refresh and _cached_token and (time.time() - _token_time < TOKEN_TTL):
            print("Using cached token")
            return _cached_token

        print("🔄 Fetching new bearer token...")

        token = _fetch_new_token()

        _cached_token = token
        _token_time = time.time()

        return token


def invalidate_token():
    global _cached_token
    with _lock:
        _cached_token = None