#!/usr/bin/env bash
set -euo pipefail

# Uninstall Cloud System services:
# - stop services
# - disable (if previously enabled)
# - remove unit files
# - daemon-reload and reset-failed

API_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-api"
VERIF_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_verification"
AI_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_ai"

SERVICES=("$API_SERVICE" "$VERIF_SERVICE" "$AI_SERVICE")

for svc in "${SERVICES[@]}"; do
  echo "⏹️  Stopping ${svc}"
  sudo systemctl stop "${svc}.service" 2>/dev/null || true

  echo "🚫 Disabling ${svc}"
  sudo systemctl disable "${svc}.service" 2>/dev/null || true

  echo "🗑️  Removing unit /etc/systemd/system/${svc}.service"
  sudo rm -f "/etc/systemd/system/${svc}.service" 2>/dev/null || true
  sudo rm -f "/lib/systemd/system/${svc}.service" 2>/dev/null || true
done

sudo systemctl daemon-reload
sudo systemctl reset-failed

echo "✅ Cloud services uninstalled."
