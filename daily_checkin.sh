#!/usr/bin/env bash
# daily_checkin.sh -- the daily few minutes on the hotspot, from the Mac.
#   1. waits until the Pi's clock has synced over the internet
#   2. compares the Pi's time with this Mac's
#   3. shows system status (running? day number, row counts, last log lines)
#   4. copies the Pi's data to THESIS/_pi_data/ (backup)
set -uo pipefail
cd "$(dirname "$0")"
source .pi_host.sh

echo "== waiting for the Pi clock to sync (up to 60 s)"
for i in $(seq 1 30); do
  s=$($SSH "$PI" "timedatectl show -p NTPSynchronized --value" 2>/dev/null)
  [[ $s == yes ]] && break
  sleep 2
done
pi_epoch=$($SSH "$PI" "date +%s"); mac_epoch=$(date +%s)
off=$(( pi_epoch - mac_epoch ))
if [[ $s == yes ]]; then
  echo "   Pi clock synced, offset vs Mac: ${off}s"
else
  echo "   !! Pi clock NOT synced after 60 s (offset vs Mac: ${off}s). Is the Pi on the hotspot with internet?"
fi

echo "== status"
$SSH "$PI" "bash ~/THESIS/Dual_Archi/tools/agrisentry.sh status"

echo "== backing up data to _pi_data/"
./sync_pi.sh pull | tail -n 2
