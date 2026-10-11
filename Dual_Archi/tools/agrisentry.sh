#!/usr/bin/env bash
# agrisentry.sh -- start / stop / check the AgriSentry system on the Pi.
#
#   agrisentry.sh start       start + enable pi-link (ESP32 logger) and the 12:00 GPR cron job
#   agrisentry.sh stop        stop + disable both (testing mode)
#   agrisentry.sh status      what's running, today's day number, CSV row counts, last log lines
#   agrisentry.sh reset-data  archive all data CSVs/logs and start empty ones (asks first)
#
# From the Mac:  ./system.sh start|stop|status
set -uo pipefail

DUAL="$HOME/THESIS/Dual_Archi"
DATA="$HOME/agrisentry_data"
CRON_LINE="0 12 * * * /usr/bin/python3 $DUAL/capture_gpr.py >> $DUAL/cron.log 2>&1"

cron_set() {   # cron_set on|off
  local cur; cur=$(crontab -l 2>/dev/null | grep -v 'capture_gpr.py')
  if [[ $1 == on ]]; then printf '%s\n%s\n' "$cur" "$CRON_LINE" | crontab -
  else printf '%s\n# %s\n' "$cur" "$CRON_LINE" | crontab -; fi
}

day_info() {
  python3 - "$DUAL/sowing_date.txt" <<'EOF'
import sys, datetime as dt
s = open(sys.argv[1]).read().strip()
d = (dt.date.today() - dt.date.fromisoformat(s)).days + 1
print(f"sowing date {s} -> today is D={d} (capture_gpr numbering, D=1 on sowing day)")
EOF
}

rows() { [[ -f $1 ]] && echo $(( $(wc -l < "$1") - 1 )) || echo "missing"; }

status() {
  echo "pi-link service : $(systemctl is-active pi-link) ($(systemctl is-enabled pi-link 2>/dev/null))"
  if crontab -l 2>/dev/null | grep -q '^[^#].*capture_gpr.py'; then
    echo "12:00 GPR cron  : ON"
  else
    echo "12:00 GPR cron  : OFF"
  fi
  echo "$(day_info)"
  echo "data rows       : growth_dataset=$(rows "$DUAL/growth_dataset.csv")" \
       " sm_log=$(rows "$DATA/sm_log.csv") irrigation=$(rows "$DATA/irrigation_log.csv")" \
       " errors=$(rows "$DATA/error_log.csv")"
  if [[ -f $DUAL/pi_link.log ]]; then
    echo "--- last pi_link.log lines"; tail -n 6 "$DUAL/pi_link.log"
  fi
}

case "${1:-status}" in
  start)
    sudo -n systemctl enable --now pi-link
    cron_set on
    sleep 4
    if grep -q "ACK,TIME" <(tail -n 20 "$DUAL/pi_link.log" 2>/dev/null); then
      echo "ESP32 link OK (time sync acknowledged)"
    else
      echo "WARNING: no ACK,TIME from the ESP32 yet -- check pi_link.log"
    fi
    status ;;
  stop)
    sudo -n systemctl disable --now pi-link
    cron_set off
    status ;;
  status)
    status ;;
  reset-data)
    A="$DATA/archive_$(date +%Y%m%d_%H%M%S)"
    read -r -p "Archive all current CSVs/logs to $A and start fresh? [y/N] " ok
    [[ $ok == [yY] ]] || { echo "cancelled"; exit 1; }
    was=$(systemctl is-active pi-link)
    sudo -n systemctl stop pi-link
    mkdir -p "$A"
    mv "$DATA"/*.csv "$DATA"/sm_snapshot.json "$DUAL"/growth_dataset.csv "$DUAL"/cron.log "$A"/ 2>/dev/null
    [[ -f $DUAL/pi_link.log ]] && sudo -n mv "$DUAL/pi_link.log" "$A/" && sudo -n chown "$USER" "$A/pi_link.log"
    python3 "$DUAL/tools/init_csvs.py"
    [[ $was == active ]] && sudo -n systemctl start pi-link
    echo "archived to $A"; status ;;
  *)
    echo "usage: $0 start|stop|status|reset-data"; exit 1 ;;
esac
