#!/usr/bin/env bash
set -euo pipefail

# Install systemd services for Cloud System (no enable at boot).
# - Creates venv and installs requirements
# - Writes unit files for API, verification, and AI routines
# - Reloads systemd and starts services NOW (without enabling on boot)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUD_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$CLOUD_DIR/venv"
REQ_FILE="$CLOUD_DIR/requirements.txt"

USER_NAME="$(logname)"

API_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-api"
VERIF_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_verification"
AI_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_ai"

API_EXEC="%VENV%/bin/uvicorn api:app --host 0.0.0.0 --port 8000"
VERIF_EXEC="%VENV%/bin/python %CLOUD%/routines/routines_verification.py"
AI_EXEC="%VENV%/bin/python %CLOUD%/routines/routines_ai.py"

API_WD="%CLOUD%/core"
VERIF_WD="%CLOUD%/routines"
AI_WD="%CLOUD%/routines"

echo "👤 Using user: $USER_NAME"
echo "📁 Cloud dir: $CLOUD_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 not found in PATH" >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "🐍 Creating virtualenv: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
if [[ -f "$REQ_FILE" ]]; then
  echo "📦 Installing requirements from $REQ_FILE"
  "$VENV_DIR/bin/pip" install -r "$REQ_FILE"
else
  echo "⚠️ $REQ_FILE missing; installing minimal dependencies"
  "$VENV_DIR/bin/pip" install fastapi uvicorn pymongo cryptography google-genai sendgrid python-multipart
fi

# Ensure temp storage dirs exist
mkdir -p "$CLOUD_DIR/temp_cloud_storage" "$CLOUD_DIR/temp_cloud_storage_processed"

create_service () {
  local svc="$1"
  local exec_cmd="$2"
  local wd="$3"
  exec_cmd="${exec_cmd//%VENV%/$VENV_DIR}"
  exec_cmd="${exec_cmd//%CLOUD%/$CLOUD_DIR}"
  wd="${wd//%CLOUD%/$CLOUD_DIR}"

  local unit="/etc/systemd/system/${svc}.service"
  sudo tee "$unit" >/dev/null <<EOF
[Unit]
Description=Cloud System - ${svc}
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${wd}
ExecStart=${exec_cmd}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  echo "✅ Created/updated unit: ${svc}.service"
}

create_service "$API_SERVICE"  "$API_EXEC"  "$API_WD"
create_service "$VERIF_SERVICE" "$VERIF_EXEC" "$VERIF_WD"
create_service "$AI_SERVICE"    "$AI_EXEC"   "$AI_WD"

echo "🔄 Reloading systemd daemon"
sudo systemctl daemon-reload

echo "▶️ Starting services (not enabling at boot)"
sudo systemctl start "${API_SERVICE}.service"
sudo systemctl start "${VERIF_SERVICE}.service"
sudo systemctl start "${AI_SERVICE}.service"

echo "🎉 Services started. Use stop_services.sh to stop them."
echo "🔎 View logs: journalctl -u ${API_SERVICE}.service -f (and others)"
