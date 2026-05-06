"""
Communication Plugin Loader

Scans `cloud_system/communication_plugins/`, loads only those present in
`system_config.ENABLED_COMMUNICATION_PLUGINS`, reads `plugin_config.py` to determine
`PLUGIN_TYPE` (expected: "communication"), and imports `index.py` providing
modules exposing:

    def run_communication(message: str, config: dict) -> dict

Returns a dict mapping plugin name -> module.
"""

import os
import sys
import importlib.util
from typing import Dict, Optional

# Ensure project root (parent of `cloud_system`) is on the path so
# `import cloud_system.plugins...` resolves correctly when this file
# is executed directly.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import system_config


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


def load_enabled_communication_plugins() -> Dict[str, object]:
    """Load enabled communication plugins and return a mapping name->module.

    Only plugins with PLUGIN_TYPE == "communication" and an `index.py` defining
    `run_communication(message: str, config: dict)` are loaded.
    """

    loaded: Dict[str, object] = {}

    # Resolve the absolute path to cloud_system root
    cloud_system_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    plugins_root = os.path.join(cloud_system_root, "communication_plugins")

    enabled = list(getattr(system_config, "ENABLED_COMMUNICATION_PLUGINS", []))
    for name in enabled:
        plugin_dir = os.path.join(plugins_root, name)
        if not os.path.isdir(plugin_dir):
            continue

        # Read plugin_config.py for PLUGIN_TYPE
        config_path = os.path.join(plugin_dir, "plugin_config.py")
        config_mod = _import_module_from_path(f"comm_plugin_config_{name}", config_path) if os.path.isfile(config_path) else None
        if config_mod is None:
            continue

        plugin_type_raw: Optional[str] = getattr(config_mod, "PLUGIN_TYPE", None)
        if not isinstance(plugin_type_raw, str):
            continue
        plugin_type = plugin_type_raw.strip().lower()
        if plugin_type != "communication":
            continue

        # Import index.py
        index_path = os.path.join(plugin_dir, "index.py")
        index_mod = _import_module_from_path(f"comm_index_{name}", index_path) if os.path.isfile(index_path) else None
        if index_mod is None:
            continue

        # Verify required function exists
        if not hasattr(index_mod, "run_communication"):
            continue

        loaded[name] = index_mod

    return loaded
