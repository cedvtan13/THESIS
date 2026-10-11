#!/usr/bin/env bash
# sync_pi.sh -- live sync between this Mac's THESIS folder and the Pi's ~/THESIS.
#
#   ./sync_pi.sh push   Mac -> Pi : code and config only (.py, firmware, json, ...)
#   ./sync_pi.sh pull   Pi  -> Mac: the Pi's data (CSVs, logs, agrisentry_data)
#                                   into THESIS/_pi_data/ for backup / analysis
#
# Push never sends CSVs, logs or images, so it can't clobber data the Pi is
# collecting. Nothing is deleted on either side (no --delete).
# GitHub is still fine for snapshots; this is for day-to-day edits.
set -euo pipefail

cd "$(dirname "$0")"

source .pi_host.sh   # sets PI_HOST, PI, SSH

case "${1:-}" in
  push)
    echo "push -> crk@$PI_HOST:~/THESIS"
    rsync -avz -e "$SSH" \
      --exclude .git --exclude .pio --exclude .vscode --exclude .DS_Store \
      --exclude __pycache__ --exclude _pi_data --exclude _archive --exclude _bench \
      --exclude '*.csv' --exclude '*.log' --exclude '*.jpg' --exclude '*.png' \
      --exclude sowing_date.txt \
      ./ "crk@$PI_HOST:THESIS/"
    ;;
  pull)
    echo "pull <- crk@$PI_HOST"
    mkdir -p _pi_data/Dual_Archi _pi_data/agrisentry_data
    rsync -avz -e "$SSH" --include '*/' --include '*.csv' --include '*.log' \
      --include sowing_date.txt --exclude '*' --prune-empty-dirs \
      "crk@$PI_HOST:THESIS/Dual_Archi/" _pi_data/Dual_Archi/
    rsync -avz -e "$SSH" "crk@$PI_HOST:agrisentry_data/" _pi_data/agrisentry_data/
    ;;
  *)
    echo "usage: $0 push|pull"; exit 1 ;;
esac
