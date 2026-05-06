"""Simplified communication routine.

Runs periodically and triggers `send_communication(message, config)` on each
enabled communication plugin when a system shows missing health pings.

This implementation is intentionally small and easy to read.
"""

from typing import Dict, Any, List
import time

import os
import sys

# Ensure parent directory (local_system) is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import system_config
from core.db import get_db
from core.communication_plugin_loader import load_enabled_communication_plugins
from datetime import datetime


def _now_s() -> int:
    return int(time.time())


def _safe_exc_str(exc: Exception) -> str:
    try:
        return str(exc)
    except Exception:
        try:
            return repr(exc)
        except Exception:
            return "<unrepresentable exception>"


def run_once() -> Dict[str, Any]:
    if not getattr(system_config, "COMMUNICATION_ENABLED", False):
        return {"ok": True, "skipped": True, "reason": "COMMUNICATION_ENABLED is False"}

    db = get_db()
    if db is None:
        return {"ok": False, "error": "DB not available"}

    coll_name = getattr(system_config, "MONGODB_COLLECTION_VERIFICATION_SYSTEM", "verification_system")
    coll = db[coll_name]
    threshold = int(getattr(system_config, "VERIFICATION_SYSTEM_MISSING_MAX_AGE_SECONDS", 300))

    systems_coll_name = getattr(system_config, "MONGODB_COLLECTION_SYSTEMS", "systems")
    systems_coll = db[systems_coll_name]

    plugins = load_enabled_communication_plugins()
    plugin_configs = getattr(system_config, "COMMUNICATION_PLUGIN_CONFIGS", {})

    triggered: List[Dict[str, Any]] = []

    now = _now_s()

    def _to_ts(val) -> int:
        if not val:
            return 0
        if isinstance(val, (int, float)):
            return int(val)
        if isinstance(val, str):
            try:
                dt = datetime.fromisoformat(val)
                return int(dt.timestamp())
            except Exception:
                return 0
        if hasattr(val, "timestamp"):
            try:
                return int(val.timestamp())
            except Exception:
                return 0
        return 0

    # iterate systems collection and check each device
    try:
        systems_cursor = systems_coll.find({}, {"SYSTEM_ID": 1, "DEVICES": 1})
    except Exception:
        systems_cursor = []

    systems_list = list(systems_cursor)
    print(f"[COMMUNICATION] Checking systems for missing health pings (threshold={threshold}s) - systems to check {len(systems_list)}")
   
    for sys_doc in systems_list:
        print(f"[COMMUNICATION] Checking system: {sys_doc}")
        system_id = sys_doc.get("SYSTEM_ID") or sys_doc.get("system_id")
        devices = sys_doc.get("DEVICES") or sys_doc.get("devices") or []

        # if no explicit devices, treat the whole system as a single entity
        if not devices:
            print(f"[COMMUNICATION] No devices found for system {system_id}, treating as single entity")
            devices = [None]

        print(f"[COMMUNICATION] Devices to check for system {system_id}: {devices}")
        
        for device in devices:
            print(f"[COMMUNICATION] Checking device: {device} for system {system_id}")
            # build query for verification collection
            q = {"SYSTEM_ID": system_id} if device is None else {"SYSTEM_ID": system_id, "DEVICE_ID": device}
            try:
                docs = list(coll.find(q, {"received_at": 1}).sort("received_at", -1).limit(1))
                print(f"[COMMUNICATION] Found verification docs for device {device}")
            except Exception:
                print(f"[COMMUNICATION] Error querying verification documents for system {system_id}, device {device}")
                docs = []

            last_raw = docs[0]["received_at"] if len(docs) > 0 else None
            last_ts = _to_ts(last_raw)

            print(f"[COMMUNICATION] Last received_at for system {system_id} device {device}: {last_raw} (ts: {last_ts})")

            should_trigger = last_ts == 0 or ((now - last_ts) > threshold)

            print(f"[COMMUNICATION] should_trigger={should_trigger} for system {system_id} device {device}")

            if not should_trigger:
                print(f"[COMMUNICATION] System {system_id} device {device} is healthy (last ping {last_raw}, age {now - last_ts}s)")
                continue

            # simple message (only last ping age matters)
            message = ""
            age = max(0, now - (last_ts or 0))

            print(f"[COMMUNICATION] Triggering communication for system {system_id} device {device} (now {now}, last ping {last_ts}, age {age}s)")
            
            if device is None:
                message = f"System {system_id} missing health pings: last ping {last_raw} ({age}s ago)."
                print(f"[COMMUNICATION] Triggering communication for system {system_id}: {message}")
            else:
                message = f"System {system_id} device {device} missing health pings: last ping {last_raw} ({age}s ago)."
                print(f"[COMMUNICATION] Triggering communication for system {system_id} device {device}: {message}")

            # trigger all enabled plugins for this specific device
            for name, mod in plugins.items():
                print(f"[COMMUNICATION] Triggering plugin {name} for system {system_id} device {device}")
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
                        res = send_fn(message, cfg)
                        print(f"[COMMUNICATION] Plugin {name} send_communication result: {res}")
                except Exception as e:
                    err = _safe_exc_str(e)
                    res = {"ok": False, "error": err}
                    print(f"[COMMUNICATION] Error running communication plugin {name}: {err}")

                triggered.append({"system_id": system_id, "device_id": device, "plugin": name, "result": res})
                print(f"[COMMUNICATION] Plugin {name} triggered for system {system_id} device {device} with result: {res}")

    return {"ok": True, "triggered": triggered}


def run_forever():
    interval = int(getattr(system_config, "VERIFICATION_CHECK_INTERVAL_SECONDS", 60))
    while True:
        try:
            run_once()
        except Exception:
            pass
        time.sleep(interval)

run_forever()