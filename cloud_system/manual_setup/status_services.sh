#!/usr/bin/env bash
set -euo pipefail

# Show status for Cloud System services

API_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-api"
VERIF_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_verification"
AI_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_ai"

SERVICES=("$API_SERVICE" "$VERIF_SERVICE" "$AI_SERVICE")

echo "Cloud services status:" 
echo

for svc in "${SERVICES[@]}"; do
  echo "==> ${svc}"
  active="$(systemctl is-active "${svc}.service" 2>/dev/null || echo unknown)"
  enabled="$(systemctl is-enabled "${svc}.service" 2>/dev/null || echo unknown)"
  mainpid="$(systemctl show "${svc}.service" -p MainPID --value 2>/dev/null || echo -)"
  echo "  Active : ${active}"
  echo "  Enabled: ${enabled}"
  echo "  MainPID: ${mainpid}"
  # Show brief status line without logs
  systemctl status "${svc}.service" --no-pager -n 0 | sed '1,3!d' || true
  echo
done

echo "Tip: view logs with 'journalctl -u <service>.service -f'"
