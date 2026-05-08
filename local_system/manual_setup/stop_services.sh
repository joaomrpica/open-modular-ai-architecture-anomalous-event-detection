#!/usr/bin/env bash
set -euo pipefail

# Stop Local System services (do not disable)

SERVICES=(
  "open-modular-ai-architecture-anomalous-event-detection-routines_audio"
  "open-modular-ai-architecture-anomalous-event-detection-routines_images"
  "open-modular-ai-architecture-anomalous-event-detection-routines_detection"
  "open-modular-ai-architecture-anomalous-event-detection-routines_verification"
)

for svc in "${SERVICES[@]}"; do
  echo "⏹️  Stopping ${svc}"
  sudo systemctl stop "${svc}.service" 2>/dev/null || true
done

echo "✅ All local services stopped."
