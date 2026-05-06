from typing import Dict, Any, List
import os
import sys
import base64
import mimetypes
import json
import traceback
import tempfile
import re

# Ensure project root (parent of `cloud_system`) is on the path so
# `import cloud_system.plugins...` resolves correctly when this file
# is executed directly.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def _prepare_files(input_files: List[Any]) -> List[Dict[str, Any]]:
    out = []
    for f in input_files:
        try:
            if isinstance(f, dict):
                # already in expected shape
                if f.get("content_b64"):
                    out.append({"name": f.get("name"), "mime": f.get("mime"), "content_b64": f.get("content_b64")})
                    continue
            # otherwise assume it's a file path
            path = str(f)
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    raw = fh.read()
                mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
                out.append({"name": os.path.basename(path), "mime": mime, "content_b64": base64.b64encode(raw).decode("ascii")})
        except Exception:
            # skip problematic files
            continue
    return out


def _build_prompt(meta: Dict[str, Any]) -> str:
    lines = [
        "You are a multimodal assistant. Given the attached files (images and/or audio) and metadata, determine whether the event corresponds to a human help request (from audio) or a fall (from image).",
        "Provide a simple and clear explanation of what is heard in the audio (e.g., words, tone, signs of distress or request for help) and what is visible in the image (e.g., person lying down, posture, possible fall indicators).",
        "Return a short JSON with the following fields: label (help/fall/none), confidence (0.0-1.0), description (a brief, simple explanation combining what is heard and/or seen, justifying the label).",
        "Metadata:",
        json.dumps({
            "system_id": meta.get("system_id"),
            "device_id": meta.get("device_id"),
            "client_id": meta.get("client_id"),
            "timestamp": meta.get("timestamp"),
        }),
    ]
    return "\n".join(lines)

def _call_genai(prompt: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Call Google Generative AI SDK (lite) using uploaded temp files and the provided prompt.
    Falls back to returning {'ok': False, ...} when SDK not available or call fails.
    """

    from google import genai
    from plugins.ai_multimodal import plugin_config as plugin_conf

    api_key = getattr(plugin_conf, "GEMINI_API_KEY", None) or getattr(plugin_conf, "API_KEY", None)

    if not api_key:
        return {"ok": False, "error": "GEMINI_API_KEY not set in environment or plugin_config"}

    try:
        import socket

        # Universal IPv4 Patch
        # Forces Python to ignore IPv6 addresses to prevent TCP handshake hangs
        _old_getaddrinfo = socket.getaddrinfo

        def new_getaddrinfo(*args, **kwargs):
            responses = _old_getaddrinfo(*args, **kwargs)
            return [r for r in responses if r[0] == socket.AF_INET]

        socket.getaddrinfo = new_getaddrinfo

        client = genai.Client(api_key=api_key)
        model_name = ["gemini-2.5-flash", "gemini-3-flash-preview"]
    except Exception as e:
        return {"ok": False, "error": f"model init failed: {e}", "trace": traceback.format_exc()}

    # write files to temp dir and build upload args
    with tempfile.TemporaryDirectory() as td:
        upload_args = [prompt]
        for f in files:
            try:
                name = f.get("name") or f"file_{len(upload_args)}"
                content_b64 = f.get("content_b64")
                if not content_b64:
                    continue
                data = base64.b64decode(content_b64)
                path = os.path.join(td, name)
                with open(path, "wb") as fh:
                    fh.write(data)
                # user example: genai.upload_file("image1.jpg")
                upload_args.append(client.files.upload(file=path))
            except Exception:
                print(f"[ai_multimodal] Warning: failed to prepare file {name} for upload and path {path}")
                continue

        
        last_error = None
        for mname in model_name:
            try:
                print(f"[ai_multimodal] Calling Gemini model '{mname}' with {len(upload_args) - 1} files...")
                response = client.models.generate_content(
                    model=mname,
                    contents=upload_args
                )
                return {"ok": True, "text": response.text}
            except Exception as e:
                print(f"[ai_multimodal] Model '{mname}' failed: {e}")
                last_error = {"ok": False, "error": f"genai call failed for model '{mname}': {e}", "trace": traceback.format_exc()}
        return last_error if last_error else {"ok": False, "error": "No model names provided or all attempts failed."}

    #extract text from response
    text = None
    try:
        # try common attributes
        if hasattr(response, "candidates"):
            cand = response.candidates[0]
            text = getattr(cand, "content", None) or getattr(cand, "display", None) or str(cand)
        elif isinstance(response, dict) and response.get("candidates"):
            text = response["candidates"][0].get("content")
        elif hasattr(response, "text"):
            text = response.text
        else:
            text = str(response)
    except Exception:
        text = str(response)

    # extract JSON object from text
    try:
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            parsed = json.loads(m.group(1))
            return {"ok": True, **parsed}
        # try parsing entire text
        parsed = json.loads(text)

        return {"ok": True, **parsed}
    except Exception:
        return {"ok": False, "error": "could not parse JSON from model response", "text": text}


def run_inference(files: List[Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Run multimodal inference using remote Lite Gemini when configured, else fallback stub.

    `files` can be a list of file paths or file dicts with `content_b64`.
    """
    prepared = _prepare_files(files)
    prompt = _build_prompt(meta or {})

    # Try Google Generative AI SDK first
    remote = _call_genai(prompt, prepared)
    print(f"[ai_multimodal] Remote model response: {remote}")
    if isinstance(remote, dict) and remote.get("ok"):
        # remote may include parsed fields directly or return raw text under 'text'
        label = remote.get("label") or remote.get("result") or None
        confidence = remote.get("confidence") or remote.get("score") or remote.get("precision")
        description = remote.get("description") or remote.get("explanation") or ""

        # If the SDK returned raw text (e.g. code-fenced JSON), try to extract JSON
        raw_text = remote.get("text")
        if (not label or confidence is None or not description) and isinstance(raw_text, str):
            try:
                m = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
                if not m:
                    m = re.search(r"(\{.*\})", raw_text, re.DOTALL)
                if m:
                    parsed = json.loads(m.group(1))
                    # prefer parsed values when present
                    label = label or parsed.get("label") or parsed.get("result")
                    confidence = confidence or parsed.get("confidence") or parsed.get("score") or parsed.get("precision") 
                    description = description or parsed.get("description") or parsed.get("explanation")
                    # attach parsed JSON for debugging
                    remote["parsed"] = parsed
            except Exception:
                # ignore parse errors and fall back to existing values
                pass

        # Normalize types and defaults
        try:
            if confidence is not None:
                confidence = float(confidence)
        except Exception:
            confidence = 0
        label = str(label or "unknown")

        status = "DETECTION_CONFIRMED" if (str(label).lower() in ("help", "fall") or (confidence is not None and float(confidence) >= 0.5)) else "DETECTION_NOT_CONFIRMED"

        return {
            "plugin": "ai_multimodal",
            "num_files": len(prepared),
            "meta": {"system_id": meta.get("system_id"), "device_id": meta.get("device_id"), "client_id": meta.get("client_id")},
            "label": label,
            "precision": float(confidence) if confidence is not None else None,
            "status": status,
            "description": description
        }

    # Fallback stub behavior
    num = len(prepared)
    if num > 0:
        status = "DETECTION_CONFIRMED"
        description = "Fallback stub: files received; raising alert for incident."
        precision = 90.0
    else:
        status = "DETECTION_NOT_CONFIRMED"
        description = "Fallback stub: no evidence provided; likely false alarm."
        precision = 5.0

    return {
        "plugin": "ai_multimodal",
        "num_files": num,
        "meta": {"system_id": meta.get("system_id"), "device_id": meta.get("device_id"), "client_id": meta.get("client_id")},
        "label": "stub-ai-inference",
        "precision": precision,
        "status": status,
        "description": description,
        "notes": "Used local fallback; configure LITEST_GEMINI_URL to call remote model",
    }

