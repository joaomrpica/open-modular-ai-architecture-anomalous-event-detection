"""
AI Plugin Loader (Cloud)

Scans `cloud_system/plugins/`, loads only those present in
`system_config.ENABLED_AI_PLUGINS`, reads `plugin_config.py` to determine
`PLUGIN_TYPE` (expected: "ai"), and imports `index.py` providing modules
exposing a unified interface:

    def run_inference(files: list[dict], meta: dict) -> dict

Returns a dict mapping plugin name -> module.
"""

import os
import importlib.util
from typing import Dict, Optional

from cloud_system.config import system_config


def _import_module_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return module
    except Exception:
        return None


def load_enabled_ai_plugins() -> Dict[str, object]:
    """Load enabled AI plugins and return a mapping name->module.

    Only plugins with PLUGIN_TYPE == "ai" and an `index.py` defining
    `run_inference(files: list[dict], meta: dict)` are loaded.
    """

    loaded: Dict[str, object] = {}

    # Resolve the absolute path to cloud_system root
    cloud_system_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    plugins_root = os.path.join(cloud_system_root, "plugins")

    enabled = list(getattr(system_config, "ENABLED_AI_PLUGINS", []))
    for name in enabled:
        plugin_dir = os.path.join(plugins_root, name)
        if not os.path.isdir(plugin_dir):
            continue

        # Read plugin_config.py for PLUGIN_TYPE
        config_path = os.path.join(plugin_dir, "plugin_config.py")
        config_mod = _import_module_from_path(f"ai_plugin_config_{name}", config_path) if os.path.isfile(config_path) else None
        if config_mod is None:
            continue

        plugin_type_raw: Optional[str] = getattr(config_mod, "PLUGIN_TYPE", None)
        if not isinstance(plugin_type_raw, str):
            continue
        plugin_type = plugin_type_raw.strip().lower()
        if plugin_type != "ai":
            continue

        # Import index.py
        index_path = os.path.join(plugin_dir, "index.py")
        index_mod = _import_module_from_path(f"ai_index_{name}", index_path) if os.path.isfile(index_path) else None
        if index_mod is None:
            continue

        # Verify required function exists
        if not hasattr(index_mod, "run_inference"):
            continue

        loaded[name] = index_mod

    return loaded
