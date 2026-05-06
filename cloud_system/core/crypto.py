import base64
import json
from typing import Any, Dict

from cloud_system.config.system_config import DETECTION_ENCRYPTION_KEY


def decrypt_fernet_blob(blob_b64: str) -> Dict[str, Any]:
    try:
        from cryptography.fernet import Fernet
    except Exception:
        raise RuntimeError("cryptography/fernet not available")

    if not DETECTION_ENCRYPTION_KEY:
        raise RuntimeError("Missing DETECTION_ENCRYPTION_KEY in cloud config")

    key_bytes = DETECTION_ENCRYPTION_KEY.encode() if isinstance(DETECTION_ENCRYPTION_KEY, str) else DETECTION_ENCRYPTION_KEY
    f = Fernet(key_bytes)
    ciphertext = base64.b64decode(blob_b64)
    plaintext = f.decrypt(ciphertext)
    payload = json.loads(plaintext.decode("utf-8"))
    # expected payload keys: data_type, status, precision, files[{name,mime,content_b64}]
    return payload
