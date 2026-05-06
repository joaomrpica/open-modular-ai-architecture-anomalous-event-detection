"""AI review routine

Scans `temp_cloud_storage` for pending evidence folders, reads `metadata.json`
and files, asks the `ai_multimodal` plugin to confirm whether the event is
actually a help request (audio) or a fall (images). If confirmed, triggers
enabled communication plugins with a descriptive message.

This routine is intentionally defensive: it tries multiple plugin call
signatures and logs errors instead of failing hard.
"""

import os
import sys
import json
import shutil
import time
from typing import List, Dict, Any

# Ensure project root (parent of `cloud_system`) is on the path so
# `import cloud_system.plugins...` resolves correctly when this file
# is executed directly.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import system_config

def _temp_storage_root() -> str:
    configured = getattr(system_config, "TEMP_CLOUD_STORAGE_PATH", None)
    # If user provided an absolute path, use it directly
    if configured and os.path.isabs(configured):
        return configured

    # Default: temp_cloud_storage sibling to this routines folder (cloud_system/temp_cloud_storage)
    routines_dir = os.path.dirname(__file__)
    sibling = os.path.abspath(os.path.join(routines_dir, "..", "temp_cloud_storage"))
    # If configured is a relative path, resolve it relative to project root
    if configured:
        if not os.path.isabs(configured):
            try:
                configured_abs = os.path.abspath(configured)
                return configured_abs
            except Exception:
                pass
    return sibling


def _list_pending_folders(root: str) -> List[str]:
    # Prefer to list subfolders inside the configured TEMP_CLOUD_STORAGE_PATH
    configured = getattr(system_config, "TEMP_CLOUD_STORAGE_PATH", None) or "temp_cloud_storage"
    # Resolve configured path to absolute
    if not os.path.isabs(configured):
        # If configured is relative, assume it's relative to project root (root may be parent)
        configured_abs = os.path.abspath(configured)
    else:
        configured_abs = configured

    # If the configured path exists, list its subfolders
    try:
        if os.path.isdir(configured_abs):
            base = configured_abs
        else:
            # maybe configured path is a basename under the provided root
            candidate = os.path.join(root, os.path.basename(configured_abs))
            if os.path.isdir(candidate):
                base = candidate
            else:
                # fallback to provided root
                base = root

        entries = [os.path.join(base, p) for p in os.listdir(base) if os.path.isdir(os.path.join(base, p))]
        return entries
    except Exception:
        return []


def _read_metadata(folder: str) -> Dict[str, Any]:
    meta_path = os.path.join(folder, "metadata.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _list_files(folder: str) -> List[str]:
    files_dir = os.path.join(folder, "files")
    try:
        return [os.path.join(files_dir, f) for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]
    except Exception:
        return []


def _load_ai_plugin():
    try:

        from plugins.ai_multimodal import index as ai_plugin
        return ai_plugin
    except Exception:
        try:
            # fallback import path
            import plugins.ai_multimodal.index as ai_plugin2  # type: ignore
            return ai_plugin2
        except Exception:
            return None


def _call_ai_plugin(ai_plugin, files: List[str], meta: Dict[str, Any]) -> Dict[str, Any]:
    if ai_plugin is None:
        return {"ok": False, "error": "ai_multimodal plugin not available"}

    # The ai_multimodal plugin exposes run_detection which accepts either
    # (model, files, data_type, meta) or (files, data_type, meta). Prefer
    # to pass the model when available.
    try:
        run_fn = getattr(ai_plugin, "run_inference", None)
        if callable(run_fn):
            try:
                return run_fn(files, meta)
            except TypeError:
                return {"ok": False, "error": f"ai plugin run_inference failed: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": False, "error": "no callable entrypoint found in ai_multimodal"}


def _trigger_communications(message: str):
    try:
        try:
            from core.communication_plugin_loader import load_enabled_communication_plugins

            plugins = load_enabled_communication_plugins()
            plugin_configs = getattr(system_config, "COMMUNICATION_PLUGIN_CONFIGS", {})
        except Exception as e:
            print(f"[AI_ROUTINE] Error loading communication plugins: {e}")

        # trigger all enabled plugins for this specific device
        for name, mod in plugins.items():
            cfg = plugin_configs.get(name, {})
            res = {"ok": False, "error": "no send function called"}
            try:
                # call unified send_communication API in plugin
                send_fn = getattr(mod, "send_communication", None)

                print(f"[COMMUNICATION] send_fn: {send_fn}")
                run_fn = getattr(mod, "run_communication", None)
                print(f"[COMMUNICATION] send_fn: {send_fn}; run_fn: {run_fn}")
                if callable(send_fn):
                    print(f"[COMMUNICATION] Calling send_communication for plugin {name}")
                    cfg['SUBJECT'] = "AI-confirmed detection alert"
                    res = send_fn(message, cfg)
                    print(f"[COMMUNICATION] Plugin {name} send_communication result: {res}")
            except Exception as e:
                res = {"ok": False, "error": str(e)}
                print(f"[COMMUNICATION] Error running communication plugin {name}: {e}")
    except Exception as e:
        print(f"[AI_ROUTINE] Error loading communication plugins: {e}")


def _build_message(meta: Dict[str, Any], ai_result: Dict[str, Any], file_paths: List[str]) -> str:

    # Try to extract structured fields first
    label = ai_result.get("label") or ai_result.get("result") or "unknown"
    confidence = ai_result.get("confidence") or ai_result.get("precision") or ai_result.get("score") or ai_result.get("score_pct") or 'unknown'
    description = ai_result.get("description") or ai_result.get("explanation") or "unavailable"


    print(f"[AI_ROUTINE] Building message with label={label}, confidence={confidence}, meta={meta}, files={file_paths} description={description}")

    lines = ["ALERT: AI-confirmed detection"]
    if meta:
        lines.append(f"System: {meta.get('system_id','')}")
        lines.append(f"Client: {meta.get('client_id','')}")
        lines.append(f"Device: {meta.get('device_id','')}")
        lines.append(f"Timestamp: {meta.get('timestamp','')}")
    lines.append(f"Detection: {label}")
    if confidence is not None:
        lines.append(f"Confidence: {confidence}")
    if file_paths:
        names = [os.path.basename(p) for p in file_paths]
        lines.append(f"Files: {', '.join(names)}")
    # Include extracted description and model raw text
    if description:
        lines.append("")
        lines.append("AI description:")
        lines.append(description.strip())

    return "\n".join(lines)


def _persist_alert(meta: Dict[str, Any], ai_result: Dict[str, Any], message: str, files: List[str]) -> None:
    """Persist AI-confirmed alert to MongoDB `data` collection.

    This function is defensive: it will log and return if DB isn't
    configured. It intentionally does not raise to avoid breaking the
    routine when persistence fails.
    """
    try:
        from core.db import get_db
        db = get_db()
        if db is None:
            print("[AI_ROUTINE] MongoDB not configured; skipping persistence.")
            return

        entry = {
            "created_at": int(time.time()),
            "meta": meta,
            "message": message,
            "ai_result": ai_result
        }

        # TODO: if system_config.ALLOW_STORE_ALERT_FILES is True,
        # include the actual file blobs (consider GridFS or external object storage)

        try:
            col = db[system_config.MONGODB_COLLECTION_DATA]
            col.insert_one(entry)
            print("[AI_ROUTINE] Alert persisted to MongoDB collection 'data'.")
        except Exception as e:
            print(f"[AI_ROUTINE] Could not write alert to MongoDB: {e}")
    except Exception as e:
        print(f"[AI_ROUTINE] Error while persisting alert to DB: {e}")


def run_once_and_process() -> None:
    root = _temp_storage_root()
    print(f"[AI_ROUTINE] temp storage root={root}")
    if not os.path.exists(root):
        print(f"[AI_ROUTINE] temp storage root does not exist; creating: {root}")
        try:
            os.makedirs(root, exist_ok=True)
        except Exception as e:
            print(f"[AI_ROUTINE] Could not create temp storage root: {e}")
            return

    pending = _list_pending_folders(root)
    if not pending:
        try:
            entries = os.listdir(root)
        except Exception as e:
            entries = f"(could not list directory: {e})"
        print(f"[AI_ROUTINE] No pending evidence folders found. root entries={entries}")
        return

    ai_plugin = _load_ai_plugin()

    for folder in pending:
        print(f"[AI_ROUTINE] Processing {folder}")
        meta = _read_metadata(folder)
        files = _list_files(folder)
        if not files:
            print(f"[AI_ROUTINE] No files in {folder}, skipping")
            continue

        # Ask AI plugin to validate
        try:
            print(f"[AI_ROUTINE] Calling AI plugin on {len(files)} files with meta={meta}")
            ai_result = _call_ai_plugin(ai_plugin, files, meta)
            print(f"[AI_ROUTINE] AI plugin result: {ai_result}")
        except Exception as e:
            ai_result = {"ok": False, "error": str(e)}

        #Decide confirmation: plugin may return {'label': 'fall', 'confidence': 0.8} or similar
        confirmed = False
        try:
            if isinstance(ai_result, dict) and ai_result.get("ok") is not False:
                print(f"[AI_ROUTINE] Evaluating AI result for confirmation: {ai_result}")
                lbl = str(ai_result.get("label", ai_result.get("result", ""))).lower()
                conf = ai_result.get("confidence") or ai_result.get("precision") or ai_result.get("score") or ai_result.get("score_pct") or 0
                try:
                    conf = float(conf)
                except Exception:
                    conf = 0

                min_conf = float(getattr(system_config, "AI_CONFIRMATION_MIN_CONFIDENCE", 0.5))
                if (("help" in lbl) or ("fall" in lbl)) and (conf >= min_conf):
                    confirmed = True

        except Exception:
            confirmed = False

        print(f"[AI_ROUTINE] Confirmation result for {folder}: {confirmed}")

        if confirmed:
            message = _build_message(meta, ai_result, files)

            # Trigger communications if enabled
            if bool(getattr(system_config, "COMMUNICATION_ENABLED", True)):
                print(f"[AI_ROUTINE] Confirmation OK for {folder}: triggering communications")
                _trigger_communications(message)
                print(f"[AI_ROUTINE] Communications triggered for {folder}")
            else:
                print(f"[AI_ROUTINE] Communications disabled by config; skipping for {folder}")

            # Persist alert to MongoDB only if enabled in config
            if bool(getattr(system_config, "STORE_DETECTION_IN_DB", False)):
                _persist_alert(meta, ai_result, message, files)
            else:
                print("[AI_ROUTINE] STORE_DETECTION_IN_DB=False; skipping persistence.")

            # Cleanup: archive or delete processed folder
            archive = bool(getattr(system_config, "ARCHIVE_PROCESSED_DETECTIONS", True))
            if archive:
                processed_root = os.path.join(root, "..", "temp_cloud_storage_processed")
                os.makedirs(processed_root, exist_ok=True)
                dest = os.path.join(processed_root, os.path.basename(folder))
                try:
                    shutil.move(folder, dest)
                    print(f"[AI_ROUTINE] Archived processed folder to {dest}")
                except Exception as e:
                    print(f"[AI_ROUTINE] Could not archive folder {folder}: {e}")
            else:
                try:
                    shutil.rmtree(folder)
                    print(f"[AI_ROUTINE] Deleted processed folder {folder}")
                except Exception as e:
                    print(f"[AI_ROUTINE] Could not delete folder {folder}: {e}")

if __name__ == "__main__":
    def run_forever():
        interval = int(getattr(system_config, "AI_ROUTINE_INTERVAL_SECONDS", 30))
        print(f"[AI_ROUTINE] Starting main loop, interval={interval}s")
        try:
            while True:
                try:
                    run_once_and_process()
                except Exception as e:
                    print(f"[AI_ROUTINE] Error during run: {e}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("[AI_ROUTINE] Stopped by user.")

    run_forever()
