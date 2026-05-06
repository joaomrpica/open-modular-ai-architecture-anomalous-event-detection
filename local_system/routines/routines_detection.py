"""
Simplified Detection Routine

This version loads enabled plugins once, preloads model objects by calling
each plugin's `get_model()` (if available), stores those model objects in
`plugin_models` (by category and plugin name), and then enters the periodic
loop that calls `run_detection` for image and audio plugins.

Plugins may implement either signature:
 - new: def run_detection(model, files, data_type, meta)
 - old: def run_detection(files, data_type, meta)

If the plugin provides `get_model()` it will be called once and its return
value passed as `model` to `run_detection`. This keeps the routine simple
and deterministic.
"""

import os
import sys
import time
import datetime
from typing import List

# Ensure local_system root is on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import system_config
from core.plugin_loader import load_enabled_plugins
from core import api_client


def _resolve_storage_path(rel_path: str) -> str:
    local_system_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    return os.path.join(local_system_root, rel_path)


def _recent_files(folder: str, max_count: int) -> List[str]:
    try:
        files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    except Exception:
        return []
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[: max(0, int(max_count))]


def run_detection_loop() -> None:
    interval = int(getattr(system_config, "DETECTION_SYSTEM_INTERVAL_SECONDS", 30))
    num_images = int(getattr(system_config, "DETECTION_NUM_IMAGES", 5))
    num_audios = int(getattr(system_config, "DETECTION_NUM_AUDIOS", 5))

    images_rel = getattr(system_config, "LOCAL_STORAGE_IMAGES_PATH", getattr(system_config, "IMAGE_STORAGE_PATH", "local_storage/images"))
    audios_rel = getattr(system_config, "LOCAL_STORAGE_AUDIOS_PATH", getattr(system_config, "AUDIO_STORAGE_PATH", "local_storage/audios"))

    images_dir = _resolve_storage_path(images_rel)
    audios_dir = _resolve_storage_path(audios_rel)

    print(f"[DETECTION] Interval={interval}s, images_dir={images_dir}, audios_dir={audios_dir}")

    # Load enabled plugins once and preload their models
    plugins = load_enabled_plugins()

    print("[DETECTION] Loaded plugins:")
    for category, mods in plugins.items():
        print(f"  {category}:")
        for mod in mods:
            print(f"    - {getattr(mod, '__name__', str(mod))}")
    plugin_models = {"image": {}, "audio": {}}

    print(f"[DETECTION] Preloading plugin models...")

    for category in ("image", "audio"):
        for mod in plugins.get(category, []):
            print(f"[DETECTION] Preloading models for category: {category}")
            try:
                print(f"[DETECTION] Preloading model for plugin: {getattr(mod, '__name__', str(mod))} (category={category})")
                get_model_fn = getattr(mod, "get_model", None)
                print(f"[DETECTION] get_model_fn: {get_model_fn}")
                model_obj = get_model_fn() if callable(get_model_fn) else None
                plugin_models[category][mod] = model_obj
                print(f"[DETECTION] Plugin loaded: {getattr(mod, '__name__', str(mod))} (category={category}), model_loaded={model_obj is not None}")
            except Exception as e:
                plugin_models[category][mod] = None
                print(f"[DETECTION] Error preloading model for {getattr(mod, '__name__', str(mod))} (category={category}): {e}")

    print(f"[DETECTION] Starting detection loop...")

    try:
        while True:
            triggered_apis = False
            has_meta_audio_detection = False
            has_meta_image_detection = False

            detections_to_send = []

            image_files = _recent_files(images_dir, num_images)
            audio_files = _recent_files(audios_dir, num_audios)

            meta = {
                "system_id": getattr(system_config, "SYSTEM_ID", ""),
                "client_id": getattr(system_config, "CLIENT_ID", ""),
                "device_id": getattr(system_config, "DEVICE_ID", ""),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            # Image plugins
            for mod in plugins.get("image", []):
                print(f"[DETECTION] Running image detection at {meta['timestamp']}")

                name = getattr(mod, "__name__", str(mod))
                model_obj = plugin_models["image"].get(mod)
                try:
                    try:
                        result = mod.run_detection(model_obj, image_files, "image", meta)
                        # Decide whether this result should trigger API validation
                        if isinstance(result, dict):
                            if result.get("trigger_api", True):
                                lbl = str(result.get("label", "")).lower()
                                precision = float(result.get("precision", result.get("score", 0.0) * 100.0)) if (result.get("precision") is not None or result.get("score") is not None) else 0.0
                                if ("detect" in lbl) or (precision > 0.0):
                                    triggered_apis = True
                                    has_meta_image_detection = True
                                    detections_to_send.append({"plugin": name, "result": result, "plugin_type": 'image', "data": image_files})
                        print(f"[DETECTION][IMAGE][{name}] Called with model argument")
                    except TypeError:
                        print(f"[DETECTION][IMAGE][{name}] No model argument, calling old signature")
                        result = mod.run_detection(image_files, "image", meta)
                    print(f"[DETECTION][IMAGE][{name}] {result}")
                except Exception as e:
                    print(f"[DETECTION][IMAGE][{name}] error: {e}")

                print(f"[DETECTION] Image detection completed.")

            # Audio plugins
            for mod in plugins.get("audio", []):
                print(f"[DETECTION] Running audio detection at {meta['timestamp']}")

                name = getattr(mod, "__name__", str(mod))
                model_obj = plugin_models["audio"].get(mod)
                try:
                    try:
                        result = mod.run_detection(model_obj, audio_files, "audio", meta)
                        if isinstance(result, dict):
                            if result.get("trigger_api", True):
                                lbl = str(result.get("label", "")).lower()
                                precision = float(result.get("precision", result.get("score", 0.0) * 100.0)) if (result.get("precision") is not None or result.get("score") is not None) else 0.0
                                if ("detect" in lbl) or (precision > 0.0):
                                    triggered_apis = True
                                    has_meta_audio_detection
                                    detections_to_send.append({"plugin": name, "result": result, "plugin_type": 'audio', "data": audio_files})

                        print(f"[DETECTION][AUDIO][{name}] Called with model argument")
                    except TypeError:
                        print(f"[DETECTION][AUDIO][{name}] No model argument, calling old signature")
                        result = mod.run_detection(audio_files, "audio", meta)
                    print(f"[DETECTION][AUDIO][{name}] {result}")
                except Exception as e:
                    print(f"[DETECTION][AUDIO][{name}] error: {e}")

                print(f"[DETECTION] Audio detection completed.")

            # Plugins want to triggered the Cloud API Validation
            if triggered_apis:
                print(f"[DETECTION] One or more plugins triggered API calls. Sending payload with {len(detections_to_send)} detections")
                try:
                    # Ensure payload includes both image and audio files so the cloud
                    # receives all evidence even if only one plugin type triggered.
                    try:
                        combined_paths = []
                        if isinstance(image_files, (list, tuple)) and len(image_files) > 0:
                            combined_paths.extend(image_files)
                        if isinstance(audio_files, (list, tuple)) and len(audio_files) > 0:
                            combined_paths.extend(audio_files)
                        if combined_paths:
                            detections_to_send.append({
                                "plugin": "system_combined",
                                "result": {"label": "combined", "trigger_api": True},
                                "plugin_type": "image/audio",
                                "data": combined_paths,
                            })
                    except Exception as _:
                        # non-fatal: proceed with existing detections
                        pass

                    # Add plugin_type into meta (image, audio, or image/audio)
                    meta_with_type = dict(meta)
                    try:
                        types_present = ""
                        if has_meta_image_detection == True and has_meta_audio_detection == False:
                            types_present = "image"
                        elif has_meta_image_detection == False and has_meta_audio_detection == True:
                            types_present = "audio"
                        elif has_meta_image_detection == True and has_meta_audio_detection == True:
                            types_present = "image/audio"
                        else:
                            types_present = "unknown"
                        meta_with_type["plugin_type"] = types_present
                    except Exception:
                        meta_with_type["plugin_type"] = "unknown"

                    print(f"[DETECTION] Sending detection payload to API with meta: {meta_with_type}")

                    resp = api_client.send_detection_payload(detections_to_send, meta_with_type)
                    if isinstance(resp, dict) and resp.get("ok"):
                        print(f"[DETECTION] Detection payload sent to API (status {resp.get('status_code')}).")
                    else:
                        # transient retry once for network/server errors
                        print(f"[DETECTION] API client returned error: {resp}")
                        retry = False
                        status = resp.get("status_code") if isinstance(resp, dict) else None
                        if status is None or (isinstance(status, int) and status >= 500):
                            retry = True
                        if retry:
                            print("[DETECTION] Retrying send_detection_payload once...")
                            resp2 = api_client.send_detection_payload(detections_to_send, meta)
                            if isinstance(resp2, dict) and resp2.get("ok"):
                                print(f"[DETECTION] Retry succeeded (status {resp2.get('status_code')}).")
                            else:
                                print(f"[DETECTION] Retry failed: {resp2}")
                except Exception as e:
                    print(f"[DETECTION] Error sending detection payload: {e}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("[DETECTION] Stopped by user.")

if __name__ == "__main__":
    run_detection_loop()
