#!/usr/bin/env bash
set -euo pipefail

# One-command local setup for Raspberry Pi
# - Creates venv with system site packages
# - Installs required apt packages
# - Installs Python requirements
# - Delegates to install_services.sh to create/start services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$LOCAL_DIR/venv"
REQ_FILE="$LOCAL_DIR/requirements.txt"

echo "[LOCAL SETUP] Local dir: $LOCAL_DIR"

# 1) Create venv (system site packages for RPi camera/libcamera bindings)
if [ ! -d "$VENV_DIR" ]; then
  echo "[LOCAL SETUP] Creating virtualenv (system site packages): $VENV_DIR"
  python3 -m venv --system-site-packages "$VENV_DIR"
fi

PIP="$VENV_DIR/bin/pip"

# 2) APT dependencies (audio, camera, GPIO, dev headers)
echo "[LOCAL SETUP] Updating apt and installing dependencies (sudo required)"
sudo apt update
sudo apt install -y libportaudio2 portaudio19-dev libsndfile1 libsndfile1-dev
sudo apt install -y python3-picamera2 python3-libcamera libcamera-apps
sudo apt install -y rpicam-apps
sudo apt install -y libcap-dev python3-dev pkg-config

# 3) Python requirements
echo "[LOCAL SETUP] Upgrading pip and installing Python requirements"
"$PIP" install --upgrade pip
if [ -f "$REQ_FILE" ]; then
  "$PIP" install -r "$REQ_FILE"
else
  echo "[LOCAL SETUP][WARN] $REQ_FILE not found; skipping pip requirements"
fi

# 4) Install and start services
echo "[LOCAL SETUP] Running: install_services.sh"
if [ ! -x "$SCRIPT_DIR/install_services.sh" ]; then
  chmod +x "$SCRIPT_DIR/install_services.sh" || true
fi
bash "$SCRIPT_DIR/install_services.sh"

echo "[LOCAL SETUP] Completed. Uninstall with:"
echo "  bash $SCRIPT_DIR/uninstall_services.sh"
