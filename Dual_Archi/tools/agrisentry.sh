#!/usr/bin/env bash
# agrisentry.sh -- start / stop / check the AgriSentry system on the Pi.
#
#   agrisentry.sh start       start + enable pi-link (ESP32 logger) and the 12:00 GPR cron job
#   agrisentry.sh stop        stop + disable both (testing mode)
#   agrisentry.sh status      what's running, today's day number, CSV row counts, last log lines
#   agrisentry.sh reset-data  archive all data CSVs/logs and start empty ones (asks first)
#   agrisentry.sh new-run YYYY-MM-DD
#                             NEW PLANTING: archive the whole previous run (CSVs, logs,
#                             frames, field log) to ~/archive/, set the sowing date (= D1),
#                             reset the ESP32 (counters cleared, germination mode ON:
#                             all pots 50-60 %), and turn logging back on
#   agrisentry.sh bands-on    end germination mode: start the low/optimal/high treatments
#   agrisentry.sh ups-test    start ONLY the logger (no noon capture) and mark the start
#                             of a UPS runtime test; the result is written to
#                             ~/agrisentry_data/power_log.csv after power comes back
#
# From the Mac:  ./system.sh start|stop|status
set -uo pipefail

DUAL="$HOME/THESIS/Dual_Archi"
DATA="$HOME/agrisentry_data"
# 12:00, with retries every 10 min until 12:50 in case the Pi was rebooting or the camera
# was busy. The duplicate-day guard makes every run after the first successful one a no-op.
CRON_LINE="0,10,20,30,40,50 12 * * * /usr/bin/python3 $DUAL/capture_gpr.py >> $DUAL/cron.log 2>&1"
# Hourly light reading from the camera (tools/light_log.py). Skips 12:xx so it never
# fights the noon capture for the camera.
LIGHT_LINE="30 6-11,13-18 * * * /usr/bin/python3 $DUAL/tools/light_log.py >> $DUAL/light_cron.log 2>&1"

cron_set() {   # cron_set on|off
  local cur; cur=$(crontab -l 2>/dev/null | grep -v -e 'capture_gpr.py' -e 'light_log.py')
  if [[ $1 == on ]]; then printf '%s\n%s\n%s\n' "$cur" "$CRON_LINE" "$LIGHT_LINE" | crontab -
  else printf '%s\n# %s\n# %s\n' "$cur" "$CRON_LINE" "$LIGHT_LINE" | crontab -; fi
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
  if [[ $(timedatectl show -p NTPSynchronized --value) == yes ]]; then
    echo "clock           : OK, internet-synced ($(date '+%Y-%m-%d %H:%M'))"
  else
    echo "clock           : NOT SYNCED since boot ($(date '+%Y-%m-%d %H:%M')) -- rebooted offline?"
    echo "                  connect the hotspot for a minute so the time corrects"
  fi
  echo "$(day_info)"
  echo "data rows       : growth_dataset=$(rows "$DUAL/growth_dataset.csv")" \
       " sm_log=$(rows "$DATA/sm_log.csv") irrigation=$(rows "$DATA/irrigation_log.csv")" \
       " errors=$(rows "$DATA/error_log.csv") above-band notices=$(rows "$DATA/band_log.csv")"
  if [[ -f $DATA/sm_log.csv ]] && (( $(wc -l < "$DATA/sm_log.csv") > 1 )); then
    python3 - "$DATA/sm_log.csv" <<'EOF'
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
r = rows[-1]
band = {1: "30-40", 2: "30-40", 3: "30-40", 4: "50-60", 5: "50-60", 6: "50-60",
        7: "70-80", 8: "70-80", 9: "70-80"}
print(f"latest moisture : {r['wall_time'].replace('T', ' ')[:16]}  (logged every 30 min)")
for i in range(1, 10):
    v = r[f"P-0{i}"]
    lo, hi = (float(x) for x in band[i].split("-"))
    note = "" if v == "NaN" else ("  below band -> will water" if float(v) < lo else
                                   "  above band (no water)" if float(v) > hi else "  in band")
    print(f"   P-0{i}  {v:>6}%   band {band[i]}%{note}")
EOF
  fi
  if [[ -f $DATA/ups_test_start ]]; then
    echo "UPS test        : RUNNING since $(date -d @"$(cat "$DATA/ups_test_start")" '+%Y-%m-%d %H:%M')"
  fi
  if [[ -f $DATA/power_log.csv ]]; then
    echo "--- power events (power_log.csv)"
    tail -n 3 "$DATA/power_log.csv" | cut -d, -f2,3,4,5,9
  fi
  if [[ -f $DUAL/pi_link.log ]]; then
    echo "--- last pi_link.log lines (above-band notices hidden)"
    grep -v "ABOVE_BAND" "$DUAL/pi_link.log" | tail -n 6
  fi
}

case "${1:-status}" in
  start)
    if [[ -f $DATA/ups_test_start ]]; then
      echo "Ending the UPS test that started $(date -d @"$(cat "$DATA/ups_test_start")" '+%Y-%m-%d %H:%M') (no power loss recorded for it)"
      rm -f "$DATA/ups_test_start"
    fi
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
  ups-test)
    if [[ $(timedatectl show -p NTPSynchronized --value) != yes ]]; then
      echo "Pi clock is not internet-synced -- connect the hotspot first so the start time is right"; exit 1
    fi
    date +%s > "$DATA/ups_test_start"
    sudo -n systemctl enable --now pi-link
    sleep 4
    echo "UPS test started $(date '+%Y-%m-%d %H:%M'). Logger running (noon capture NOT enabled)."
    echo "Unplug mains now and leave it. After power returns and the Pi boots, run:"
    echo "  ./system.sh status      (or: cat ~/agrisentry_data/power_log.csv)"
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
  new-run)
    NEW=${2:-}
    if ! [[ $NEW =~ ^20[0-9]{2}-[01][0-9]-[0-3][0-9]$ ]] || ! date -d "$NEW" >/dev/null 2>&1; then
      echo "usage: $0 new-run YYYY-MM-DD   (the sowing date, which becomes D1)"; exit 1
    fi
    OLD=$(cat "$DUAL/sowing_date.txt" 2>/dev/null || echo unknown)
    A="$HOME/archive/run_sown_${OLD}_archived_$(date +%Y%m%d_%H%M%S)"
    [[ -e $A ]] && { echo "$A already exists -- wait a second and run again"; exit 1; }
    echo "This will:"
    echo "  1. move ALL data of the run sown $OLD (CSVs, logs, frames, field log) to"
    echo "     $A   (nothing is deleted)"
    echo "  2. set the sowing date to $NEW (D1). Code and pot_rois.json stay as they are."
    echo "  3. reset the ESP32: watering counters cleared, germination mode ON (all pots 50-60 %)"
    echo "  4. turn the logger, the 12:00 capture and the hourly light log ON"
    read -r -p "Go ahead? [y/N] " ok
    [[ $ok == [yY] ]] || { echo "cancelled"; exit 1; }
    sudo -n systemctl stop pi-link
    cron_set off
    mkdir -p "$A/agrisentry_data" "$A/thesis"
    shopt -s dotglob nullglob
    for f in "$DATA"/*; do mv "$f" "$A/agrisentry_data/"; done
    for f in "$DUAL"/growth_dataset*.csv "$DUAL"/exposure_log*.csv "$DUAL"/field_log*.csv \
             "$DUAL"/cell_gpr* "$DUAL"/light_log*.csv "$DUAL"/harvest_weights*.csv \
             "$DUAL"/cron.log "$DUAL"/light_cron.log; do
      [[ -e $f ]] && mv "$f" "$A/thesis/"
    done
    shopt -u dotglob nullglob
    [[ -f $DUAL/pi_link.log ]] && sudo -n mv "$DUAL/pi_link.log" "$A/thesis/" && sudo -n chown "$USER" "$A/thesis/pi_link.log"
    cp "$DUAL"/pot_rois*.json "$DUAL/sowing_date.txt" "$A/thesis/" 2>/dev/null
    echo "$NEW" > "$DUAL/sowing_date.txt"
    python3 "$DUAL/tools/init_csvs.py"
    printf 'date,day,pot_id,note\n%s,,ALL,"New run, sowing date %s = D1. Previous run (sown %s) archived to %s."\n' \
      "$(date +%F)" "$NEW" "$OLD" "$A" > "$DUAL/field_log.csv"
    echo "--- resetting the ESP32 (counters, germination mode ON)"
    if python3 "$DUAL/pi_link.py" --reset-state; then echo "ESP32 reset OK"
    else echo "WARNING: ESP32 did not acknowledge RESET_STATE -- run it again later:"
         echo "  sudo systemctl stop pi-link; python3 ~/thesis/pi_link.py --reset-state; sudo systemctl start pi-link"; fi
    sudo -n systemctl enable --now pi-link
    cron_set on
    echo "archived to $A"
    echo "Next: re-fit the pot circles (make_rois.py) once the camera is mounted, BEFORE 12:00 on $NEW."
    sleep 4; status ;;
  bands-on)
    sudo -n systemctl stop pi-link
    if python3 "$DUAL/pi_link.py" --bands-on; then
      echo "Treatments ON (low 30-40 / optimal 50-60 / high 70-80)"
      printf '%s,%s,ALL,Germination mode OFF -- treatment bands ON\n' "$(date +%F)" \
        "$(( ($(date +%s) - $(date -d "$(cat "$DUAL/sowing_date.txt")" +%s)) / 86400 + 1 ))" >> "$DUAL/field_log.csv"
    else
      echo "WARNING: no ACK from the ESP32 -- bands NOT changed"
    fi
    sudo -n systemctl start pi-link
    status ;;
  *)
    echo "usage: $0 start|stop|status|reset-data|new-run YYYY-MM-DD|bands-on|ups-test"; exit 1 ;;
esac
