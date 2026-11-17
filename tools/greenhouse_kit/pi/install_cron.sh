#!/usr/bin/env bash
# install_cron.sh -- schedule backup.sh on the Pi (13:15 and 23:45 every day).
# Safe to run more than once: it replaces its own lines and leaves the
# experiment's cron lines (capture_gpr, light_log, glare_check, throttle) alone.
#   bash ~/fixkit/install_cron.sh          install
#   bash ~/fixkit/install_cron.sh remove   take the backup lines out again
set -euo pipefail
KIT="$HOME/fixkit"
chmod +x "$KIT"/*.sh "$KIT"/*.py 2>/dev/null || true
cur=$(crontab -l 2>/dev/null | grep -v 'fixkit/backup.sh' || true)
if [[ ${1:-} == remove ]]; then
  printf '%s\n' "$cur" | crontab -
  echo "backup cron removed"; exit 0
fi
printf '%s\n%s\n%s\n' "$cur" \
  "15 13 * * * /bin/bash $KIT/backup.sh >> $KIT/backup.log 2>&1" \
  "45 23 * * * /bin/bash $KIT/backup.sh >> $KIT/backup.log 2>&1" | crontab -
echo "installed. Current crontab:"
crontab -l
