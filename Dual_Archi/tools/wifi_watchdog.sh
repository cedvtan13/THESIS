#!/usr/bin/env bash
# wifi_watchdog.sh -- run every 2 min by wifi-watchdog.timer.
# If the Pi is not on any Wi-Fi, rescan and try the known networks again, so it
# joins the hotspot within ~2 min of it being switched on. Cheap and harmless
# when already connected (it just exits).
state=$(nmcli -t -f STATE general 2>/dev/null)
[[ $state == connected* ]] && exit 0
LOG=/home/crk/agrisentry_data/wifi_watchdog.log
nmcli radio wifi on
nmcli device wifi rescan >/dev/null 2>&1
sleep 5
for c in Cvtan preconfigured; do
  if nmcli -w 20 connection up "$c" >/dev/null 2>&1; then
    echo "$(date '+%F %T') reconnected via $c" >> "$LOG"; exit 0
  fi
done
echo "$(date '+%F %T') no known network in range (state: ${state:-unknown})" >> "$LOG"
# keep the log small
tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
