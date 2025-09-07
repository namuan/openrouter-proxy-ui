#!/bin/bash
set -euo pipefail

log() { printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]]; then
    log "Cleaning up temporary directory: $TMP_DIR"
    rm -rf "$TMP_DIR" || true
  fi
}
trap cleanup EXIT

log "=== Step 1: Checking for uv ==="
if command -v uv >/dev/null 2>&1; then
    log "uv is already installed."
else
    log "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    log "uv installed"
fi

log "=== Step 2: Downloading latest source zip to a temporary directory ==="
LATEST_URL="https://github.com/namuan/openrouter-proxy-ui/archive/refs/heads/main.zip"
TMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'orproxy')
log "Created temporary directory: $TMP_DIR"
cd "$TMP_DIR"
log "Downloading: $LATEST_URL"
curl -fL "$LATEST_URL" -o app.zip
log "Download complete: $(du -h app.zip | awk '{print $1}')"

log "Unzipping archive in temporary directory"
unzip -oq app.zip
# Determine the top-level directory name inside the zip
APP_DIR=$(unzip -Z -1 app.zip | head -1 | cut -d/ -f1)
if [[ -z "$APP_DIR" || ! -d "$APP_DIR" ]]; then
  log "ERROR: Failed to determine extracted directory from zip."
  exit 1
fi
log "Extracted directory: $APP_DIR"

log "=== Step 3: Moving extracted app into ~/Applications ==="
mkdir -p "$HOME/Applications"
cd "$APP_DIR"
make setup

log "✅ Installation complete! The application is now in ~/Applications ($TARGET_DIR)."
