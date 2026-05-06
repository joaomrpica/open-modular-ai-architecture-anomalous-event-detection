from typing import List, Dict, Any
import os
import sys
import importlib.util

# Try relative import first (package-aware loader). If that fails because the
# loader imported this file as a top-level module, fall back to loading the
# sibling `plugin_config.py` by path or use an existing `plugin_config_<name>`
# module if the loader already imported it.
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

if plugin_config is None:
    class _DefaultConfig:
        LANGUAGE = "pt"

    plugin_config = _DefaultConfig()

_HAS_WHISPER = True
try:
    import whisper
except Exception:
    _HAS_WHISPER = False

# Load help phrases
_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
_PHRASES_PATH = os.path.join(_PLUGIN_DIR, "help_phrases.txt")
_PHRASES: List[str] = []
if os.path.isfile(_PHRASES_PATH):
    try:
        with open(_PHRASES_PATH, "r", encoding="utf-8") as f:
            _PHRASES = [ln.strip().lower() for ln in f.read().splitlines() if ln.strip()]
    except Exception:
        _PHRASES = []


def _transcribe_with_whisper(model, path: str) -> str:
    try:
        # Default transcribe; keep simple for compatibility
        res = model.transcribe(path)
        text = res.get("text", "")
        return text or ""
    except Exception:
        return ""

def get_model():
    """Load and return the Whisper model (cached). Returns None if whisper is unavailable.

    Routines should call this once at startup and pass the model into `run_detection`.
    """
    model = None
    print(f"[help_audio] Loading Whisper model...")
    if not _HAS_WHISPER:
        print("[help_audio] Whisper not installed.")
        return None
    try:
        print("[help_audio] Loading tiny model...")
        model = whisper.load_model("tiny")
        print("[help_audio] Whisper model loaded.")
        return model
    except Exception:
        print("[help_audio] Error loading Whisper model.")
        model = None
        return None


def run_detection(model, files: List[str], data_type: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Transcribe audio files with whisper (if available) and look for help phrases.

    Returns a result with `label` either `help_detected` or `no_help`, and `precision`
    set to 100 if any phrase matched, otherwise 0.
    """
    transcripts: List[str] = []
    matched_phrases: List[str] = []

    if not _HAS_WHISPER:
        return {
            "plugin": "help_audio",
            "data_type": data_type,
            "num_files": len(files),
            "meta": {"device_id": meta.get("device_id", ""), "system_id": meta.get("system_id", "")},
            "label": "no-whisper",
            "score": 0.0,
            "precision": 0.0,
            "notes": "whisper not installed",
            "trigger_api": False
        }

    # Fixed language from plugin configuration (Portuguese)
    lang = getattr(plugin_config, "LANGUAGE", "pt")

    for p in files:
        try:
            # files from local_system are file paths
            # Use faster transcription parameters when possible
            try:
                if lang:
                    # Request a single-beam transcription in the requested language
                    res = model.transcribe(p, language=lang, beam_size=1)
                else:
                    res = model.transcribe(p, beam_size=1)
                text = res.get("text", "")
            except TypeError:
                # Older whisper versions may not accept beam_size; fall back
                text = _transcribe_with_whisper(model, p)

            text_l = text.lower()
            transcripts.append(text)
            for phrase in _PHRASES:
                if phrase in text_l:
                    matched_phrases.append(phrase)
        except Exception:
            continue

    detected = len(matched_phrases) > 0
    label = "help_detected" if detected else "no_help"
    precision = 100.0 if detected else 0.0

    return {
        "plugin": "help_audio",
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
