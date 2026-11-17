#!/usr/bin/env bash
# backup.sh -- second copy of the run's data, made on the Pi itself.
#
# Runs ON THE PI (by cron after install_cron.sh, or by hand). Needs no internet.
#   1. packs every CSV/JSON/TXT of ~/thesis and ~/agrisentry_data into
#      ~/backups/data_YYYY-MM-DD_HHMM.tar.gz (keeps the newest 20)
#   2. copies any new noon frame into ~/backups/frames/ (never deletes)
#   3. if a USB stick is plugged in, copies both to <stick>/agrisentry_backup/
#   4. runs daily_check.py so a report is waiting in ~/fixkit/reports/
# It only reads the live files; it never changes or moves them.
set -uo pipefail

THESIS="$HOME/thesis"
DATA="$HOME/agrisentry_data"
DUAL="$HOME/THESIS/Dual_Archi"
B="$HOME/backups"
KIT="$HOME/fixkit"
STAMP=$(date +%Y-%m-%d_%H%M)
mkdir -p "$B/frames"

# 1. data tarball (follow the ~/thesis symlink if there is one)
LIST=$(mktemp)
for d in "$THESIS/" "$DUAL/" "$DATA/"; do
  [[ -d $d ]] || continue
  find -L "$d" -maxdepth 1 -type f \( -name '*.csv' -o -name '*.json' -o -name '*.txt' -o -name '*.log' \) 2>/dev/null
done | sort -u > "$LIST"
tar -czf "$B/data_$STAMP.tar.gz" -T "$LIST" 2>/dev/null
rm -f "$LIST"
echo "[backup] $B/data_$STAMP.tar.gz ($(du -h "$B/data_$STAMP.tar.gz" | cut -f1))"
ls -1t "$B"/data_*.tar.gz 2>/dev/null | tail -n +21 | xargs -r rm -f

# 2. frames (copy only the ones not backed up yet)
n=0
for f in "$DATA"/frames/*.png; do
  [[ -e $f ]] || continue
  [[ -e "$B/frames/$(basename "$f")" ]] || { cp -p "$f" "$B/frames/"; n=$((n+1)); }
done
echo "[backup] $n new frame(s) copied to $B/frames/"

# 3. USB stick, if any
for m in /media/"$USER"/*; do
  if mountpoint -q "$m" 2>/dev/null; then
    mkdir -p "$m/agrisentry_backup/frames"
    cp -p "$B/data_$STAMP.tar.gz" "$m/agrisentry_backup/" && \
    cp -pn "$B"/frames/*.png "$m/agrisentry_backup/frames/" 2>/dev/null
    sync
    echo "[backup] copied to USB: $m/agrisentry_backup/"
    break
  fi
done

# 4. health report
[[ -f $KIT/daily_check.py ]] && python3 "$KIT/daily_check.py" > /dev/null 2>&1 \
  && echo "[backup] report saved in $KIT/reports/"
exit 0
