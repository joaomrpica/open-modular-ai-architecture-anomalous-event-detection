import time
import os
import sys

import requests

# Ensure parent directory (local_system) is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import system_config


def run_system_health_loop():
    if not getattr(system_config, "VERIFICATION_SYSTEM_ENABLED", False):
        print("[VERIFICATION_SYSTEM] Disabled in configuration.")
        return

    base_url = getattr(system_config, "VERIFICATION_SYSTEM_API_BASE_URL", None)
    api_key = getattr(system_config, "CLOUD_API_BEARER_TOKEN", "")
    interval = int(getattr(system_config, "VERIFICATION_SYSTEM_INTERVAL_SECONDS", 30))
    payload_base = getattr(system_config, "VERIFICATION_SYSTEM_PAYLOAD", {})

    if not base_url:
        print("[VERIFICATION_SYSTEM] Missing VERIFICATION_SYSTEM_API_BASE_URL.")
        return

    if not api_key:
        print("[VERIFICATION_SYSTEM] Missing VERIFICATION_SYSTEM_BEARER_KEY.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"[VERIFICATION_SYSTEM] Starting loop. Endpoint: {base_url}; interval: {interval}s")

    try:
        while True:
            payload = dict(payload_base)

            try:
                resp = requests.post(base_url, json=payload, headers=headers, timeout=10)
                status = resp.status_code
                ok = 200 <= status < 300
                print(f"[VERIFICATION_SYSTEM] POST {status} ({'OK' if ok else 'FAIL'})")
            except requests.RequestException as e:
                print(f"[VERIFICATION_SYSTEM] Request error: {e}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("[SYSTEM_HEALTH] Stopped by user.")


if __name__ == "__main__":
    run_system_health_loop()
