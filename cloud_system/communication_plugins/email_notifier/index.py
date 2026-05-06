from typing import Dict, Any
import os
import sys
import importlib.util

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

def send_communication(message: str, config: Dict[str, Any]) -> Dict[str, Any]:
    print("Sending email notification with message:")
    print(message)
    # using SendGrid's Python Library
    # https://github.com/sendgrid/sendgrid-python
    
    message = Mail(
        from_email=plugin_config.EMAIL_FROM,
        to_emails=plugin_config.EMAIL_TO,
        subject=config.get("SUBJECT", plugin_config.SUBJECT),
        html_content=f'<strong>{message}</strong>')
    
    try:
        sg = SendGridAPIClient(plugin_config.SENDGRID_API_KEY)
        # sg.set_sendgrid_data_residency("eu")
        # uncomment the above line if you are sending mail using a regional EU subuser
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
        return {"ok": True, "status_code": getattr(response, "status_code", None)}
    except Exception as e:
        err = str(e)
        print(err)
        return {"ok": False, "error": err}

def run_communication(message: str, config: Dict[str, Any]) -> Dict[str, Any]:
    return send_communication(message, config)

