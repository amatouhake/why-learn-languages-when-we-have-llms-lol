#!/bin/bash
# Deploy to Raspberry Pi
# Usage: ./deploy.sh [--reimport]
#   --reimport: re-run import_data.py on Pi (needed when adding HSK levels, updating data/)

set -e

CONF="$(dirname "$0")/deploy.conf"
if [[ ! -f "$CONF" ]]; then
    echo "Error: deploy.conf not found. Copy deploy.conf.example to deploy.conf and fill in your values."
    exit 1
fi
source "$CONF"

PI="${PI_SSH_ALIAS}"

echo "=== Syncing files to Pi ==="
rsync -avz --delete \
    --exclude='.venv' \
    --exclude='hsk.db' \
    --exclude='.claude' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='complete-hsk-vocabulary/.git' \
    --exclude='audio-cmn/.git' \
    --exclude='audio-cmn/18k-abr' \
    --exclude='audio-cmn/24k-abr' \
    --exclude='audio-cmn/96k-abr' \
    ./ "${PI}:${REMOTE_DIR}/"

if [[ "$1" == "--reimport" ]]; then
    echo "=== Re-importing data (play data preserved) ==="
    ssh "$PI" "cd ${REMOTE_DIR} && source .venv/bin/activate && python import_data.py"
fi

echo "=== Restarting service ==="
ssh "$PI" "sudo systemctl restart hsk.service"

echo "=== Status ==="
ssh "$PI" "sudo systemctl status hsk.service --no-pager -l"

echo "=== Done ==="
