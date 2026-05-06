from typing import List, Dict, Any
import os
import sys
import importlib.util

# Import plugin_config using relative import when available; fall back to
# loading plugin_config_<pluginname> or the file path so this module can be
# imported even when the loader doesn't register package parents.
try:
    from . import plugin_config
except Exception:
    plugin_config = None
    try:
        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        plugin_name = os.path.basename(plugin_dir)
        mod_name = f"plugin_config_{plugin_name}"
        if mod_name in sys.modules:
            plugin_config = sys.modules[mod_name]
        else:
            cfg_path = os.path.join(plugin_dir, "plugin_config.py")
            if os.path.isfile(cfg_path):
                spec = importlib.util.spec_from_file_location(mod_name, cfg_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                    plugin_config = mod
    except Exception:
        plugin_config = None

# Provide sensible defaults if plugin_config is missing
if plugin_config is None:
    class _DefaultConfig:
        PLUGIN_TYPE = "image"
        CONFIDENCE_THRESHOLD = 40.0
        FALL_ASPECT_THRESHOLD = 0

    plugin_config = _DefaultConfig()

_HAS_DEPS = True
try:
    import cv2
    import math
    from ultralytics import YOLO
except Exception:
    _HAS_DEPS = False

# Try to locate model and classes inside the plugin directory
_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
_MODEL_PATH = os.path.join(_PLUGIN_DIR, "yolov8s.pt")

def get_model():
    model = None
    if not _HAS_DEPS:
        print("[fall_detector] Missing dependencies (cv2/ultralytics).")
        return None
 
    try:
        if os.path.isfile(_MODEL_PATH):
            model = YOLO(_MODEL_PATH)
            print("[fall_detector] Loaded YOLO model from plugin directory.")
        else:
            # Attempt to load a default model name (may fail if not installed)
            print("[fall_detector] Warning: Model file yolov8s.pt not found in plugin directory, attempting to load default model.")
            model = YOLO("yolov8s.pt")
    except Exception:
        print("[fall_detector] Error loading YOLO model.")
        return None

    return model


def _read_image(path: str):
    try:
        img = cv2.imread(path)
        return img
    except Exception:
        return None


def run_detection(model, files: List[str], data_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Run a simple fall-detection heuristic using YOLO object boxes.

    files: list of image file paths (strings).
    Returns a dict with keys: plugin, data_type, num_files, meta, label, precision, detections
    """
    if not _HAS_DEPS:
        return {
            "plugin": "fall_detector",
            "data_type": data_type,
            "num_files": len(files),
            "meta": {"device_id": meta.get("device_id", ""), "system_id": meta.get("system_id", "")},
            "label": "no-deps",
            "score": 0.0,
            "precision": 0.0,
            "notes": "Missing dependencies (cv2/ultralytics).",
            "trigger_api": False
        }

    if model is None:
        return {
            "plugin": "fall_detector",
            "data_type": data_type,
            "num_files": len(files),
            "meta": {"device_id": meta.get("device_id", ""), "system_id": meta.get("system_id", "")},
            "label": "no-model",
            "score": 0.0,
            "precision": 0.0,
            "notes": "YOLO model not available (yolov8s.pt).",
            "trigger_api": False
        }

    detections: List[Dict[str, Any]] = []
    max_conf = 0.0
    any_fall = False

    for path in files:
        img = _read_image(path)
        if img is None:
            continue

        try:
            # Limit prediction to the 'person' class (class id 0) for better performance
            # ultralytics YOLO supports a `predict` call with a `classes` filter
            results = model.predict(img, classes=[0])
        except Exception:
            continue

        # results may be iterable; follow ultralytics results structure
        for res in results:
            boxes = getattr(res, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                try:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    confidence = float(box.conf[0])
                    cls_name = 'person'
                except Exception:
                    continue

                conf_pct = confidence * 100.0

                height = y2 - y1
                width = x2 - x1
                threshold = height - width

                # Update max confidence only for person detections
                max_conf = max(max_conf, conf_pct)

                fall_detected = False
                if conf_pct > plugin_config.CONFIDENCE_THRESHOLD and threshold < plugin_config.FALL_ASPECT_THRESHOLD:
                    fall_detected = True
                    any_fall = True

                detections.append({
                    "file": os.path.basename(path),
                    "class": cls_name,
                    "confidence": conf_pct,
                    "bbox": [x1, y1, x2, y2],
                    "fall": fall_detected,
                })

    label = "fall" if any_fall else "no-fall"
    precision = float(max_conf)

    return {
        "plugin": "fall_detector",
        "data_type": data_type,
        "num_files": len(files),
        "meta": {"device_id": meta.get("device_id", ""), "system_id": meta.get("system_id", "")},
        "label": label,
        "score": precision / 100.0,
        "precision": precision,
        "detections": detections,
        "trigger_api": any_fall
    }
