#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[SETUP] Using systemd-managed services for Cloud System"
echo "[SETUP] Running: install_services.sh"

# Ensure installer is executable, then invoke with bash to avoid exec bit issues
if [ ! -x "$SCRIPT_DIR/install_services.sh" ]; then
	chmod +x "$SCRIPT_DIR/install_services.sh" || true
fi

bash "$SCRIPT_DIR/install_services.sh"

echo "[SETUP] Done. Manage with:"
echo "  bash $SCRIPT_DIR/stop_services.sh"
echo "  bash $SCRIPT_DIR/uninstall_services.sh"
