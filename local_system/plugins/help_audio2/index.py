from typing import List, Dict, Any
import os
import json
import sys
import importlib.util

# Robust plugin_config import (package-aware or file load)
try:
    from . import plugin_config
except Exception:
    plugin_config = None
    try:
        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        plugin_name = os.path.basename(plugin_dir)
        mod_name = f"plugin_config_{plugin_name}"
        cfg_path = os.path.join(plugin_dir, "plugin_config.py")
        if os.path.isfile(cfg_path):
            spec = importlib.util.spec_from_file_location(mod_name, cfg_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                plugin_config = mod
    except Exception:
        plugin_config = None

_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
_PHRASES_PATH = os.path.join(_PLUGIN_DIR, "help_phrases.txt")
_PHRASES: List[str] = []
if os.path.isfile(_PHRASES_PATH):
    try:
        with open(_PHRASES_PATH, "r", encoding="utf-8") as f:
            _PHRASES = [ln.strip().lower() for ln in f.read().splitlines() if ln.strip()]
    except Exception:
        _PHRASES = []


def get_model():
    """Return a tuple (model_path, vosk.Model) or None if unavailable.

    This function does not download models; the model directory should already
    be present on the device. The `MODEL_PATH` in `plugin_config` may be
    relative to the plugin directory.
    """
    try:
        import vosk
    except Exception:
        return None

    model_path = getattr(plugin_config, "MODEL_PATH", "vosk-model-small-pt") if plugin_config else "vosk-model-small-pt"
    # interpret relative path relative to plugin dir
    if not os.path.isabs(model_path):
        model_path = os.path.join(_PLUGIN_DIR, model_path)

    if not os.path.isdir(model_path):
        return None

    try:
        model = vosk.Model(model_path)
        return (model_path, model)
    except Exception:
        return None


def _recognize_file(model_obj, filepath: str) -> List[str]:
    """Recognize text from `filepath` using a VOSK recognizer built from model_obj.

    Returns a list of recognized words/phrases (lowercased final text split).
    """
    try:
        import wave
        import vosk
    except Exception:
        return []

    model = model_obj
    results: List[str] = []
    try:
        wf = wave.open(filepath, "rb")
    except Exception:
        return []

    if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
        # VOSK expects mono PCM16 WAV. Caller should provide proper files.
        # We will still try, but results may be poor.
        pass

    rec = vosk.KaldiRecognizer(model, wf.getframerate())
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            part = rec.Result()
            try:
                j = json.loads(part)
                text = j.get("text", "")
                if text:
                    results.append(text.lower())
            except Exception:
                continue
    # final
    try:
        final = rec.FinalResult()
        j = json.loads(final)
        text = j.get("text", "")
        if text:
            results.append(text.lower())
    except Exception:
        pass

    return results


def run_detection(model_tuple, files: List[str], data_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Run detection using the preloaded VOSK model tuple returned by `get_model()`.

    `model_tuple` is (model_path, vosk.Model) or None.
    """
    transcripts: List[str] = []
    matched_phrases: List[str] = []

    if model_tuple is None:
        return {
            "plugin": "help_audio2",
            "data_type": data_type,
            "num_files": len(files),
            "meta": {"device_id": meta.get("device_id", ""), "system_id": meta.get("system_id", "")},
            "label": "no-model",
            "score": 0.0,
            "precision": 0.0,
            "notes": "vosk model not available",
            "trigger_api": False
        }

    model = model_tuple[1]

    for p in files:
        try:
            parts = _recognize_file(model, p)
            for t in parts:
                transcripts.append(t)
                for phrase in _PHRASES:
                    if phrase in t:
                        matched_phrases.append(phrase)
        except Exception:
            continue

    detected = len(matched_phrases) > 0
    label = "help_detected" if detected else "no_help"
    precision = 100.0 if detected else 0.0

    return {
        "plugin": "help_audio2",
        "data_type": data_type,
        "num_files": len(files),
        "meta": {"device_id": meta.get("device_id", ""), "system_id": meta.get("system_id", "")},
        "label": label,
        "score": precision / 100.0,
        "precision": precision,
        "transcripts": transcripts,
        "matched_phrases": matched_phrases,
        "trigger_api": detected
    }
