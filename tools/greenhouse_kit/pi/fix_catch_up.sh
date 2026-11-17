#!/usr/bin/env bash
# fix_catch_up.sh -- limit the @reboot catch-up capture to the noon window.
# Runs ON THE PI. The existing ~/THESIS/Dual_Archi/catch_up.sh runs a capture
# 2 minutes after ANY reboot if today has no frame. On Nov 17 the Pi rebooted
# about 09:31, so D20 was captured at 09:36 in morning light, and the 12:00 cron
# then refused because the day was already written.
# New behaviour: after a reboot it only captures between 12:00 and 12:55 (the
# protocol window). Outside it, it writes one line to cron.log and does nothing;
# the normal 12:00-12:50 cron still runs. Backup kept; undo with: bash fix_catch_up.sh undo
set -euo pipefail
F="$HOME/THESIS/Dual_Archi/catch_up.sh"
if [[ ${1:-} == undo ]]; then cp "$F.before_fixkit" "$F"; echo "restored $F"; exit 0; fi
[[ -f $F.before_fixkit ]] || cp "$F" "$F.before_fixkit"
cat > "$F" <<'NEW'
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
NEW
chmod +x "$F"
echo "catch_up.sh now captures only between 12:00 and 12:55 (backup: $F.before_fixkit)"
