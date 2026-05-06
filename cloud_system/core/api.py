from typing import Any, Dict, List, Optional
import base64
import time
import os
import sys
import datetime

from fastapi import FastAPI, Header, Form, UploadFile, File, Body, Request
from fastapi import HTTPException
from fastapi.responses import JSONResponse

# Ensure parent directory (local_system) is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from cloud_system.config.system_config import (
    CLOUD_API_BEARER_TOKEN,
    STORE_SYSTEM_HEALTH_IN_DB,
    MONGODB_COLLECTION_VERIFICATION_SYSTEM
)
from cloud_system.core.db import get_db

app = FastAPI(title="Cloud System API")


def _auth_or_401(authorization: Optional[str]):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != CLOUD_API_BEARER_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bearer token")

@app.post("/api/v1/verification_system")
async def verification_system(
    payload: Dict[str, Any] = Body(...),
    authorization: Optional[str] = Header(None),
):
    _auth_or_401(authorization)

    # Accept both "SYSTEM_ID" or "system_id" keys
    system_id = payload.get("SYSTEM_ID") or payload.get("system_id")
    device_id = payload.get("DEVICE_ID") or payload.get("device_id")

    if not system_id or not device_id:
        raise HTTPException(status_code=400, detail="Missing required fields: system_id and device_id")

    doc = {
        "received_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "SYSTEM_ID": system_id,
        "DEVICE_ID": device_id,
    }

    if STORE_SYSTEM_HEALTH_IN_DB:
        db = get_db()
        if db is not None:
            try:
                db[MONGODB_COLLECTION_VERIFICATION_SYSTEM].insert_one(doc)
                return JSONResponse({"success": True, "message": "Stored in DB"})
            except Exception:
                return JSONResponse({"success": False, "message": "Failed to store in DB"})

    return JSONResponse({"success": True, "message": "Not stored in DB"})


@app.post("/api/v1/store_evidence")
async def store_evidence(
    authorization: Optional[str] = Header(None),
    payload: Dict[str, Any] = Body(...),
):
    """Store received metadata and files under `temp_cloud_storage/<unique>`.

    Expected JSON body:
      {
         "meta": { ... arbitrary metadata ... },
         "files": [ {"name": "file.jpg", "mime": "image/jpeg", "content_b64": "...base64..." }, ... ]
      }
    """
    _auth_or_401(authorization)

    meta_obj = payload.get("meta") or {}
    files_list = payload.get("files") or []

    # build destination folder under repo root temp_cloud_storage
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    storage_root = os.path.join(repo_root, "temp_cloud_storage")
    os.makedirs(storage_root, exist_ok=True)

    import uuid
    folder_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    dest = os.path.join(storage_root, folder_name)
    files_dir = os.path.join(dest, "files")
    os.makedirs(files_dir, exist_ok=True)

    # save metadata.json
    try:
        with open(os.path.join(dest, "metadata.json"), "w", encoding="utf-8") as mf:
            __import__("json").dump(meta_obj, mf, ensure_ascii=False, indent=2)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Failed to write metadata: {e}"}, status_code=500)

    saved = []
    failures = []
    for idx, fe in enumerate(files_list):
        try:
            if not isinstance(fe, dict):
                failures.append({"index": idx, "error": "file entry not an object"})
                continue
            name = fe.get("name") or fe.get("filename") or f"file_{idx}"
            content_b64 = fe.get("content_b64") or fe.get("content")
            if not content_b64:
                failures.append({"name": name, "error": "missing content_b64"})
                continue

            # Support data URI like: data:audio/wav;base64,XXXX
            if isinstance(content_b64, str) and content_b64.startswith("data:") and "," in content_b64:
                content_b64 = content_b64.split(",", 1)[1]

            raw = base64.b64decode(content_b64)
            safe_name = os.path.basename(name)
            dest_path = os.path.join(files_dir, safe_name)
            with open(dest_path, "wb") as fh:
                fh.write(raw)
            saved.append(safe_name)
        except Exception as e:
            failures.append({"name": fe.get("name") if isinstance(fe, dict) else f"index_{idx}", "error": str(e)})

    resp = {"ok": True, "path": folder_name, "files_saved": len(saved), "files": saved}
    if failures:
        resp["failures"] = failures
    return JSONResponse(resp)

