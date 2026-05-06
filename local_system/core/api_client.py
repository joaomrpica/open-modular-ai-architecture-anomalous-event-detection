
"""Simplified API client for sending detection payloads.

Exports:
- send_detection_payload(detections: list, meta: dict) -> dict

Behavior:
- Reads `DETECTION_SYSTEM_API_BASE_URL` and `API_KEY` from `config.system_config`.
- Adds `Authorization: Bearer <API_KEY>` header if key is present.
- If `DETECTION_ENCRYPTION_ENABLED` is True and `DETECTION_ENCRYPTION_KEY` is set,
  the JSON `payload` will be encrypted with Fernet and sent as `{'enc_scheme':'fernet','blob': <b64>}`.
"""

import json
from typing import List, Dict, Any
try:
    import requests
except Exception:
    requests = None

from config import system_config
import base64
import mimetypes
import os


def send_detection_payload(detections: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Send detections (list) to configured endpoint. Returns {'ok': bool, 'status_code': int|None}.

    Each detection dict may include:
      - 'plugin': plugin name
      - 'result': result dict
      - 'plugin_type': 'image'|'audio'
      - 'data': list of file paths related to the detection
    The function will read files and attach them as base64 in the payload.
    """
    base_url = getattr(system_config, "DETECTION_SYSTEM_API_BASE_URL", None)
    api_key = getattr(system_config, "CLOUD_API_BEARER_TOKEN", None)
    if not base_url:
        return {"ok": False, "status_code": None, "error": "Missing DETECTION_SYSTEM_API_BASE_URL"}
    if not api_key:
        return {"ok": False, "status_code": None, "error": "Missing API key (API_KEY)"}
    if requests is None:
        return {"ok": False, "status_code": None, "error": "requests library not available"}

    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    # Build a flat files array from detections' data paths
    files_payload: List[Dict[str, Any]] = []
    for det in detections:
        data_field = det.get("data")
        if isinstance(data_field, (list, tuple)):
            for p in data_field:
                try:
                    p_abs = os.path.abspath(p) if not os.path.isabs(p) else p
                    with open(p_abs, "rb") as fh:
                        raw = fh.read()
                    mime = mimetypes.guess_type(p_abs)[0] or "application/octet-stream"
                    name = os.path.basename(p_abs)
                    files_payload.append({"name": name, "mime": mime, "raw": raw})
                except Exception:
                    continue

    # Optional per-file encryption using Fernet: encrypt raw bytes before b64
    encrypt_files = getattr(system_config, "DETECTION_ENCRYPTION_ENABLED", False) and bool(getattr(system_config, "DETECTION_ENCRYPTION_KEY", ""))
    if encrypt_files:
        try:
            from cryptography.fernet import Fernet
        except Exception:
            return {"ok": False, "status_code": None, "error": "cryptography.fernet not available"}

        key = system_config.DETECTION_ENCRYPTION_KEY
        if isinstance(key, str):
            key_bytes = key.encode()
        else:
            key_bytes = key
        try:
            f = Fernet(key_bytes)
            for fp in files_payload:
                try:
                    ciphertext = f.encrypt(fp["raw"])
                    fp["content_b64"] = base64.b64encode(ciphertext).decode("ascii")
                    fp["enc_scheme"] = "fernet"
                except Exception:
                    fp["content_b64"] = ""
        except Exception as e:
            return {"ok": False, "status_code": None, "error": f"encryption failed: {e}"}
    else:
        for fp in files_payload:
            try:
                fp["content_b64"] = base64.b64encode(fp["raw"]).decode("ascii")
            except Exception:
                fp["content_b64"] = ""

    # Remove raw bytes before sending
    for fp in files_payload:
        fp.pop("raw", None)

    payload = {"meta": meta or {}, "files": files_payload}

    try:
        resp = requests.post(base_url, json=payload, headers=headers, timeout=20)
        ok = 200 <= resp.status_code < 300
        return {"ok": ok, "status_code": resp.status_code, "text": resp.text}
    except requests.RequestException as e:
        return {"ok": False, "status_code": None, "error": str(e)}

