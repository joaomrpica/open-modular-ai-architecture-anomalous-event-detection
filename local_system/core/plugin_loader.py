"""Very small plugin loader.

This loader imports each enabled plugin's `plugin_config.py` (optional)
and `index.py`, groups modules by `PLUGIN_TYPE` when present, otherwise
defaults to "image". No extensive validation is performed.
"""

import os
import importlib.util
import traceback
from typing import Dict, List

from config import system_config


def _import_module_from_path(name: str, path: str):
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod
    except Exception as e:
        # print traceback to help debugging on-device
        try:
            print(f"[PLUGIN_LOADER] import error for module {name} (path={path}): {e}")
            print(traceback.format_exc())
        except Exception:
            pass
        return None


def load_enabled_plugins() -> Dict[str, List[object]]:
    loaded: Dict[str, List[object]] = {"image": [], "audio": []}

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    plugins_root = os.path.join(root, "plugins")

    enabled = list(getattr(system_config, "ENABLED_PLUGINS", []))
    print(f"[PLUGIN_LOADER] enabled plugins: {enabled}")
    for name in enabled:
        plugin_dir = os.path.join(plugins_root, name)
        if not os.path.isdir(plugin_dir):
            print(f"[PLUGIN_LOADER] plugin directory not found: {plugin_dir}")
            continue

        # try to load plugin_config if present
        config_path = os.path.join(plugin_dir, "plugin_config.py")
        config_mod = _import_module_from_path(f"plugin_config_{name}", config_path) if os.path.isfile(config_path) else None
        if not os.path.isfile(config_path):
            print(f"[PLUGIN_LOADER] no plugin_config.py for {name}, defaulting to image")
        plugin_type = "image"
        if config_mod is not None:
            try:
                plugin_type = getattr(config_mod, "PLUGIN_TYPE", "image").strip().lower()
                print(f"[PLUGIN_LOADER] {name} plugin_type from config: {plugin_type}")
            except Exception as e:
                print(f"[PLUGIN_LOADER] error reading PLUGIN_TYPE for {name}: {e}")
                plugin_type = "image"

        # import index module
        index_path = os.path.join(plugin_dir, "index.py")
        if not os.path.isfile(index_path):
            print(f"[PLUGIN_LOADER] missing index.py for plugin {name}")
            continue
        index_mod = _import_module_from_path(f"plugin_index_{name}", index_path)
        if index_mod is None:
            print(f"[PLUGIN_LOADER] failed to import index.py for plugin {name}")
            continue

        print(f"[PLUGIN_LOADER] loaded plugin {name} as type {plugin_type}")
        loaded[plugin_type].append(index_mod)

    return loaded

