#!/usr/bin/env bash
# kit.sh -- Mac/Linux version of the Windows .bat files (same Pi-side scripts in ~/fixkit).
# Usage (from THESIS/tools/greenhouse_kit/mac_linux):
#   ./kit.sh check            health report from the Pi (read-only)
#   ./kit.sh pull             copy all Pi data + frames to ../../../../pi_pulls/<date_time>/ (outside the repo)
#   ./kit.sh pull-new [days]  QUICK pull: all data/log files + frames from the last 2 days (or [days])
#   ./kit.sh send             copy the pi/ scripts to ~/fixkit on the Pi (+ backup schedule)
#   ./kit.sh fixes            protect data from git, light_log off, field notes, check
#   ./kit.sh fix-d20          limit catch_up.sh to 12:00-12:55 and resolve D20 duplicate rows
#   ./kit.sh mask             run the read-only mask comparison
# Override the host: PI_HOST=172.20.10.3 ./kit.sh check
# Never run git on the Pi. Never run these between 11:45 and 12:55.
set -uo pipefail
cd "$(dirname "$0")"
KIT="../pi"
HOST="${PI_HOST:-groupb.local}"
PI="crk@$HOST"
case "${1:-}" in
  check) ssh -t "$PI" "python3 ~/fixkit/daily_check.py" ;;
  pull)
    TS=$(date +%Y-%m-%d_%H%M); DEST="../../../../pi_pulls/$TS"; mkdir -p "$DEST/fixkit"
    scp -r "$PI:thesis/" "$DEST/thesis"
    scp -r "$PI:agrisentry_data/" "$DEST/agrisentry_data"
    scp -r "$PI:fixkit/reports" "$DEST/fixkit/reports" 2>/dev/null
    scp -r "$PI:fixkit/mask_compare" "$DEST/fixkit/mask_compare" 2>/dev/null
    echo "Done: $(cd "$DEST" && pwd)" ;;
  pull-new)
    DAYS="${2:-2}"; TS=$(date +%Y-%m-%d_%H%M); DEST="../../../../pi_pulls/${TS}_quick"; mkdir -p "$DEST"
    ssh "$PI" "cd ~ && F=\$(find agrisentry_data/frames -maxdepth 2 -type f -mtime -$DAYS \\( -name 'D*.png' -o -name '*.jpg' \\) 2>/dev/null); R=\$(find fixkit/reports -type f -mtime -$DAYS 2>/dev/null); tar --ignore-failed-read -czf - thesis/*.csv thesis/*.log thesis/*.txt agrisentry_data/*.csv agrisentry_data/*.log agrisentry_data/*.json \$F \$R" | tar -xzf - -C "$DEST" \
      && { find "$DEST/agrisentry_data/frames" -type f 2>/dev/null; tail -n 9 "$DEST/thesis/growth_dataset.csv"; tail -n 4 "$DEST/agrisentry_data/sm_log.csv"; echo "Done: $(cd "$DEST" && pwd)"; } ;;
  send)
    ssh "$PI" "mkdir -p ~/fixkit/reports"
    scp "$KIT"/*.py "$KIT"/*.sh "$PI:fixkit/"
    ssh "$PI" "sed -i 's/\r$//' ~/fixkit/*.sh ~/fixkit/*.py; bash ~/fixkit/install_cron.sh && bash ~/fixkit/backup.sh" ;;
  fixes)
    scp "$KIT"/*.py "$KIT"/*.sh "$PI:fixkit/"
    ssh -t "$PI" "sed -i 's/\r$//' ~/fixkit/*.sh ~/fixkit/*.py; bash ~/fixkit/protect_data.sh; python3 ~/fixkit/add_field_notes.py; python3 ~/fixkit/daily_check.py" ;;
  fix-d20)
    scp "$KIT/fix_duplicate_day.py" "$KIT/fix_catch_up.sh" "$PI:fixkit/"
    ssh "$PI" "sed -i 's/\r$//' ~/fixkit/fix_catch_up.sh ~/fixkit/fix_duplicate_day.py; bash ~/fixkit/fix_catch_up.sh; python3 ~/fixkit/fix_duplicate_day.py --day 20"
    read -r -p "Time of the D20 set to KEEP (agreed: 12:42), Enter = change nothing: " KEEP
    [[ -n $KEEP ]] && ssh "$PI" "python3 ~/fixkit/fix_duplicate_day.py --day 20 --keep $KEEP --write" ;;
  mask) ssh "$PI" "python3 ~/fixkit/mask_compare.py" ;;
  *) sed -n 2,12p "$0"; exit 1 ;;
esac
