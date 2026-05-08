#!/usr/bin/env bash
set -euo pipefail

# Start Cloud System services (do not enable)

API_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-api"
VERIF_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_verification"
AI_SERVICE="open-modular-ai-architecture-anomalous-event-detection-cloud-routines_ai"

for svc in "$API_SERVICE" "$VERIF_SERVICE" "$AI_SERVICE"; do
  echo "▶️  Starting ${svc}"
  sudo systemctl start "${svc}.service" 2>/dev/null || true
done

echo "✅ All cloud services started."