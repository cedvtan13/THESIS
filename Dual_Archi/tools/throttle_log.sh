#!/usr/bin/env bash
# throttle_log.sh -- run every 5 min by cron (installed by agrisentry.sh).
# Records the Pi's own power flags so a freeze or restart can be checked against
# them afterwards. The Pi cannot read its input voltage, but the firmware sets a
# flag when the supply drops below ~4.63 V (vcgencmd get_throttled):
#   bit 0  under-voltage now          bit 16 under-voltage since boot
#   bit 2  CPU throttled now          bit 18 throttled since boot
# Output: ~/agrisentry_data/throttle_log.csv (next to power_log.csv)
LOG=$HOME/agrisentry_data/throttle_log.csv
[[ -f $LOG ]] || echo "logged_at,uptime_s,throttled,undervolt_now,undervolt_since_boot,throttled_since_boot,temp_c,wifi,clock_synced" > "$LOG"

raw=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)
t=$(( ${raw:-0} ))
temp=$(vcgencmd measure_temp 2>/dev/null | grep -o '[0-9.]*')
wifi=$(nmcli -t -f STATE general 2>/dev/null)
sync=$(timedatectl show -p NTPSynchronized --value 2>/dev/null)
up=$(cut -d. -f1 /proc/uptime)

echo "$(date '+%FT%T'),$up,${raw:-unknown},$(( t & 1 )),$(( (t >> 16) & 1 )),$(( (t >> 18) & 1 )),$temp,${wifi:-unknown},${sync:-unknown}" >> "$LOG"
