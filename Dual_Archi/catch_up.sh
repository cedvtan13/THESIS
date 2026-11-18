#!/bin/bash
# @reboot catch-up (limited by fixkit, Nov 2026): only inside the noon window.
sleep 120
NOW=$(date +%H%M)
TODAY=$(date +%Y-%m-%d)
LOG=/home/crk/THESIS/Dual_Archi/cron.log
if ls /home/crk/agrisentry_data/frames/D*_${TODAY}_*.png >/dev/null 2>&1; then exit 0; fi
if [[ 10#$NOW -ge 1200 && 10#$NOW -le 1255 ]]; then
    /usr/bin/python3 /home/crk/THESIS/Dual_Archi/capture_gpr.py >> "$LOG" 2>&1
else
    echo "[catch_up] reboot at $(date '+%F %H:%M'): outside 12:00-12:55, no capture (the noon cron will run)" >> "$LOG"
fi
