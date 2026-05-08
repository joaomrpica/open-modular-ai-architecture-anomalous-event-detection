#!/usr/bin/env bash
set -euo pipefail

# Detect the real logged-in user (for consistency with installer)
USER_NAME="$(logname)"

# List of services to remove
SERVICES=(
  "open-modular-ai-architecture-anomalous-event-detection-routines_audio"
  "open-modular-ai-architecture-anomalous-event-detection-routines_images"
  "open-modular-ai-architecture-anomalous-event-detection-routines_detection"
  "open-modular-ai-architecture-anomalous-event-detection-routines_verification"
)

echo "🧹 Removing Modular services for user: ${USER_NAME}"
echo

for svc in "${SERVICES[@]}"; do
  echo "⏹️  Stopping service: ${svc}"
  sudo systemctl stop "${svc}.service" 2>/dev/null || true

  echo "🚫 Disabling service: ${svc}"
  sudo systemctl disable "${svc}.service" 2>/dev/null || true

  echo "🗑️  Removing service file: /etc/systemd/system/${svc}.service"
  sudo rm -f "/etc/systemd/system/${svc}.service" 2>/dev/null || true

  # Optional: also remove it if it was placed in /lib/systemd/system
  sudo rm -f "/lib/systemd/system/${svc}.service" 2>/dev/null || true

  echo
done

# Reload systemd configuration and clear failed states
sudo systemctl daemon-reload
sudo systemctl reset-failed

echo "✅ Uninstall completed."
echo "➡️ Verify with: systemctl list-unit-files | grep modular-system"
