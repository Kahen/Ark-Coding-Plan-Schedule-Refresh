#!/usr/bin/env python3
"""
Automated API request and snapshot script.
Calls an Ark/Volcengine API endpoint, saves the request+response as a snapshot,
and sends a Telegram notification with the result.
"""

import json
import os
import sys
import requests
from datetime import datetime

from pytz import timezone


def get_env(name, default=None, required=False):
    """Get an environment variable.

    - If the variable is set, return its value.
    - If it is not set and a default is provided, return the default.
    - If it is not set, no default is provided, and it is required, exit with an error.
    """
    value = os.environ.get(name)
    if not value:
        if default is not None:
            print(f"INFO: {name} not set, using default: {default}")
            return default
        if required:
            print(f"ERROR: Missing required environment variable: {name}")
            sys.exit(1)
        print(f"INFO: {name} not set, this feature will be disabled.")
        return None
    return value


def call_api(base_url, api_key, model):
    """Call the API and return (success, response_data_or_error, request_payload)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    }
    payload = {
        "model": model,
        "max_tokens": 1024,
        "stream": False,
        "messages": [{"role": "user", "content": "Hello"}],
    }

    try:
        resp = requests.post(base_url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return True, resp.json(), payload
    except requests.exceptions.Timeout:
        return False, "Request timed out after 60s", payload
    except requests.exceptions.HTTPError:
        return False, f"HTTP {resp.status_code}: {resp.text[:500]}", payload
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}", payload
    except json.JSONDecodeError:
        return False, f"Invalid JSON response (status {resp.status_code}): {resp.text[:500]}", payload


def extract_reply_text(response_data):
    """Extract the model's reply text from an OpenAI-compatible response."""
    try:
        choices = response_data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if content:
                return content
        # Fallback: return the full JSON if we can't find a clean reply
        return json.dumps(response_data, ensure_ascii=False)
    except Exception:
        return str(response_data)


def save_snapshot(request_payload, response_data, success):
    """Save request + response as a JSON snapshot in the snapshots/ directory."""
    snapshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)

    now = datetime.now(timezone("Asia/Shanghai"))
    filename = f"snapshot_{now.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(snapshots_dir, filename)

    snapshot = {
        "timestamp": now.isoformat(),
        "success": success,
        "request": request_payload,
        "response": response_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"Snapshot saved: {filepath}")
    return filepath


def send_telegram(tg_token, tg_chat_id, message):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    payload = {
        "chat_id": tg_chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        print("Telegram notification sent successfully.")
        return True
    except Exception as e:
        print(f"WARNING: Failed to send Telegram notification: {e}")
        return False


def main():
    print("=== Automated API Request & Snapshot ===")

    # Load configuration from environment (populated from GitHub Secrets)
    # ARK_API_KEY is the only required variable. BASE_URL and MODEL fall back to
    # the defaults below when omitted. Telegram is completely optional — if
    # TG_TOKEN / TG_CHAT_ID are not set, notifications are skipped.
    base_url = get_env(
        "BASE_URL",
        default="https://ark.cn-beijing.volces.com/api/coding/v1/messages",
    )
    api_key = get_env("ARK_API_KEY", required=True)
    model = get_env("MODEL", default="ark-code-latest")
    tg_token = get_env("TG_TOKEN")
    tg_chat_id = get_env("TG_CHAT_ID")

    print(f"Model: {model}")
    print(f"Endpoint: {base_url}")

    # Call the API
    success, response_data, request_payload = call_api(base_url, api_key, model)

    # Extract the reply text for the notification
    if success:
        reply_text = extract_reply_text(response_data)
        print(f"API call SUCCESS. Reply: {reply_text[:200]}...")
    else:
        reply_text = str(response_data)
        print(f"API call FAILED. Error: {reply_text[:200]}...")

    # Save snapshot (always, so failures are recorded too)
    try:
        snapshot_path = save_snapshot(request_payload, response_data, success)
    except Exception as e:
        print(f"ERROR: Failed to save snapshot: {e}")
        snapshot_path = "N/A"

    # Send Telegram notification (only when both TG_TOKEN and TG_CHAT_ID are set)
    if tg_token and tg_chat_id:
        now_bj = datetime.now(timezone("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        status_emoji = "✅" if success else "❌"
        message = (
            f"{status_emoji} <b>API Snapshot Report</b>\n\n"
            f"<b>Model:</b> {model}\n"
            f"<b>Status:</b> {'SUCCESS' if success else 'FAILED'}\n"
            f"<b>Time (BJT):</b> {now_bj}\n\n"
            f"<b>Reply:</b>\n{reply_text[:3000]}"
        )
        send_telegram(tg_token, tg_chat_id, message)
    else:
        print("INFO: TG_TOKEN / TG_CHAT_ID not set, skipping Telegram notification.")

    # Exit with non-zero code if the API call failed, so the workflow run is marked failed
    if not success:
        sys.exit(1)

    print("=== Done ===")


if __name__ == "__main__":
    main()
