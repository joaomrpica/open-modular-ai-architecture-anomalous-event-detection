#!/usr/bin/env bash
set -euo pipefail

# Detect the real logged-in user (not root from sudo)
USER_NAME="$(logname)"

# Resolve project base directory relative to this script (repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Python executable from the virtual environment (local_system venv)
VENV_DIR="${BASE}/local_system/venv"
VENV_PY="${VENV_DIR}/bin/python"

# Routines directory
ROUTINES_DIR="${BASE}/local_system/routines"

# Service name -> Python script mapping
declare -A SERVICE_TO_SCRIPT=(
  ["open-modular-ai-architecture-anomalous-event-detection-routines_audio"]="routines_audio.py"
  ["open-modular-ai-architecture-anomalous-event-detection-routines_images"]="routines_images.py"
  ["open-modular-ai-architecture-anomalous-event-detection-routines_detection"]="routines_detection.py"
  ["open-modular-ai-architecture-anomalous-event-detection-routines_verification"]="routines_verification.py"
)

create_service () {
  local service_name="$1"
  local script_name="$2"
  local unit="/etc/systemd/system/${service_name}.service"

  sudo tee "$unit" >/dev/null <<EOF
[Unit]
Description=Modular System - ${script_name} on boot (venv)
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${ROUTINES_DIR}
ExecStart=${VENV_PY} ${ROUTINES_DIR}/${script_name}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  echo "✅ Created/updated: ${service_name}.service"
}

echo "👤 Detected user: ${USER_NAME}"
echo "📁 Project base directory: ${BASE}"
echo "🐍 Virtualenv python: ${VENV_PY}"
echo "📂 Routines directory: ${ROUTINES_DIR}"

# Basic validations (fail early if paths are wrong)
# Create venv only if it does not already exist
if [[ ! -x "$VENV_PY" ]]; then
  echo "ℹ️  Virtualenv not found; creating at: ${VENV_DIR}"
  python3 -m venv --system-site-packages "$VENV_DIR"
fi

# Validate venv again after attempting creation
if [[ ! -x "$VENV_PY" ]]; then
  echo "❌ Virtualenv python still not found at: $VENV_PY"
  echo "   Tip: Run 'bash local_system/manual_setup/setup_local.sh' to provision dependencies."
  exit 1
fi

if [[ ! -d "$ROUTINES_DIR" ]]; then
  echo "❌ Routines directory not found at: $ROUTINES_DIR"
  exit 1
fi

# Create systemd services
for svc in "${!SERVICE_TO_SCRIPT[@]}"; do
  script="${SERVICE_TO_SCRIPT[$svc]}"
  if [[ ! -f "${ROUTINES_DIR}/${script}" ]]; then
    echo "❌ Script not found: ${ROUTINES_DIR}/${script}"
    exit 1
  fi
  create_service "$svc" "$script"
done

# Reload systemd and enable/start services
sudo systemctl daemon-reload

for svc in "${!SERVICE_TO_SCRIPT[@]}"; do
  sudo systemctl enable "${svc}.service"
  sudo systemctl restart "${svc}.service"
done

echo "🎉 All services installed and running!"
echo "➡️ View logs with: journalctl -u <service-name>.service -f"
