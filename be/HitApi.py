import os
import requests
import json
import logging

from utils.GetBearer import get_bearer_token, invalidate_token
from utils.config import CHAT_API, SPACE_NAME, FLOW_ID, AUTH_STATE_PATH
from utils.tokenStore import get_token
from GetState import refresh_session

logging.basicConfig(level=logging.INFO)

AGENT2_SPACE = "BackupAgent_d8544a5f"
AGENT2_FLOW = "69d3bae8ea80f1bdfe45e207"

TIMEOUT = 30


# ✅ ---------------- TOKEN VALIDATION ----------------
def _is_valid_token(token: str) -> bool:
    if not token:
        return False

    token = token.strip()

    if token.lower() in ["null", "undefined", ""]:
        return False

    if token.startswith("Bearer "):
        token = token[7:]

    parts = token.split(".")
    return len(parts) == 3


# ✅ ---------------- AUTH HEADER BUILDER ----------------
def _build_auth_header(token: str) -> str:
    token = token.strip()
    return token if token.startswith("Bearer ") else f"Bearer {token}"


# 🔧 ---------------- GENERIC REQUEST ----------------
def _make_request(token, query_type, query, space_name, flow_id):
    headers = {
        "Content-Type": "application/json",
        "Authorization": _build_auth_header(token)
    }

    payload = {
        "query": json.dumps({
            "type": query_type,
            "content": query
        }),
        "space_name": space_name,
        "flowId": flow_id
    }

    logging.info(f"📤 Payload: {json.dumps(payload)[:200]}")
    logging.info(f"🔐 Token (first 30 chars): {token[:30]}...")

    try:
        response = requests.post(
            CHAT_API,
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )

        logging.info(f"📥 {response.status_code} from space={space_name}")

        if not response.ok:
            logging.warning(f"⚠️ Response body: {response.text[:300]}")

        return response

    except requests.Timeout:
        logging.error("⏳ Request timed out")
        raise


# 🔑 ---------------- TOKEN RESOLUTION ----------------
def _resolve_token(agent_type: str, allow_automation=True) -> str | None:
    frontend_token = get_token(agent_type)

    logging.info(f"[DEBUG] Raw frontend {agent_type} token: {repr(frontend_token)}")

    if _is_valid_token(frontend_token):
        logging.info(f"✅ Using frontend {agent_type} token")
        return frontend_token

    logging.warning(f"⚠️ Invalid/missing frontend {agent_type} token")

    if not allow_automation:
        return None

    # 🔁 AUTOMATION FLOW
    try:
        if not os.path.exists(AUTH_STATE_PATH):
            logging.warning("⚠️ auth.json missing → refreshing session")
            refresh_session()

        token = get_bearer_token()

        if _is_valid_token(token):
            logging.info(f"✅ Automation token acquired for {agent_type}")
            return token

    except Exception as e:
        logging.warning(f"⚠️ Automation fetch failed: {e}")

        # 🔁 FORCE REFRESH + RETRY
        try:
            logging.info("🔄 Refreshing session and retrying token fetch...")
            refresh_session()

            token = get_bearer_token(force_refresh=True)

            if _is_valid_token(token):
                logging.info(f"✅ Token acquired after refresh for {agent_type}")
                return token

        except Exception as e2:
            logging.error(f"❌ Retry failed: {e2}")

    return None


# 🚀 ---------------- MAIN FUNCTION ----------------
def call_chat_api(query_type: str, query: str):

    # =========================
    # 🔹 STEP 1: PRIMARY (Frontend → Automation)
    # =========================
    try:
        token = _resolve_token("primary", allow_automation=True)

        if token:
            response = _make_request(token, query_type, query, SPACE_NAME, FLOW_ID)

            if response.ok:
                logging.info("✅ Primary agent success")
                return response

            logging.warning(f"⚠️ Primary failed: {response.status_code}")

    except Exception as e:
        logging.warning(f"⚠️ Primary error: {e}")

    # =========================
    # 🔹 STEP 2: AGENT 2 (Frontend Token)
    # =========================
    try:
        fallback_token = _resolve_token("fallback", allow_automation=False)

        if fallback_token:
            logging.info("🔁 Trying Agent 2 with frontend token")

            response = _make_request(
                fallback_token,
                query_type,
                query,
                AGENT2_SPACE,
                AGENT2_FLOW
            )

            if response.ok:
                logging.info("✅ Agent 2 frontend success")
                return response

            logging.warning(f"⚠️ Agent 2 frontend failed: {response.status_code}")

    except Exception as e:
        logging.warning(f"⚠️ Agent 2 frontend error: {e}")

    # =========================
    # 🔹 STEP 3: AGENT 2 (Automation Token)
    # =========================
    try:
        logging.info("⚙️ Fetching automation token for Agent 2")

        fallback_token = _resolve_token("fallback", allow_automation=True)

        if fallback_token:
            response = _make_request(
                fallback_token,
                query_type,
                query,
                AGENT2_SPACE,
                AGENT2_FLOW
            )

            if response.ok:
                logging.info("✅ Agent 2 automation success")
                return response

    except Exception as e:
        logging.error(f"❌ Agent 2 automation error: {e}")

    # =========================
    # 🔥 FINAL GUARANTEE (NEVER FAIL)
    # =========================
    try:
        logging.critical("🚨 FINAL FALLBACK: Forcing fresh session + Agent 1")

        refresh_session()
        token = get_bearer_token(force_refresh=True)

        response = _make_request(token, query_type, query, SPACE_NAME, FLOW_ID)

        if response.ok:
            logging.info("✅ Final fallback success (Agent 1)")
            return response

    except Exception as e:
        logging.critical(f"❌ Final fallback failed: {e}")

    raise Exception("❌ SYSTEM FAILURE: All fallback strategies exhausted")