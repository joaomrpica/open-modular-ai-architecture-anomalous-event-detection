#!/usr/bin/env bash
set -euo pipefail

# Stop Cloud System services (do not disable)

API_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-api"
VERIF_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_verification"
AI_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_ai"

for svc in "$API_SERVICE" "$VERIF_SERVICE" "$AI_SERVICE"; do
  echo "⏹️  Stopping ${svc}"
  sudo systemctl stop "${svc}.service" 2>/dev/null || true
done

echo "✅ All cloud services stopped."
