#!/usr/bin/env bash
set -euo pipefail

# Show status for Local System services

SERVICES=(
  "open-modular-ai-architecture-anomalous-event-detection-routines_audio"
  "open-modular-ai-architecture-anomalous-event-detection-routines_images"
  "open-modular-ai-architecture-anomalous-event-detection-routines_detection"
  "open-modular-ai-architecture-anomalous-event-detection-routines_verification"
)

echo "Local services status:" 
echo

for svc in "${SERVICES[@]}"; do
  echo "==> ${svc}"
  active="$(systemctl is-active "${svc}.service" 2>/dev/null || echo unknown)"
  enabled="$(systemctl is-enabled "${svc}.service" 2>/dev/null || echo unknown)"
  mainpid="$(systemctl show "${svc}.service" -p MainPID --value 2>/dev/null || echo -)"
  echo "  Active : ${active}"
  echo "  Enabled: ${enabled}"
  echo "  MainPID: ${mainpid}"
  systemctl status "${svc}.service" --no-pager -n 0 | sed '1,3!d' || true
  echo
done

echo "Tip: view logs with 'journalctl -u <service>.service -f'"
