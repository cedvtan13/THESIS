#!/usr/bin/env bash
# system.sh -- start / stop / check the AgriSentry system on the Pi, from the Mac.
#   ./system.sh start        pi-link logger + 12:00 GPR capture ON  (deployment)
#   ./system.sh stop         both OFF                                (testing)
#   ./system.sh status       what's running, day number, CSV row counts
#   ./system.sh reset-data   archive current CSVs and start empty ones (asks first)
#   ./system.sh ups-test     logger only + mark the start of a UPS runtime test
#   ./system.sh new-run 2026-10-29   archive the old run, new sowing date = D1, ESP32 reset
#   ./system.sh bands-on     end germination mode, start the three treatments
# On the Pi itself:  ~/thesis/tools/agrisentry.sh start|stop|status|reset-data
set -uo pipefail
cd "$(dirname "$0")"
# Typed on the Pi itself? Run it locally instead of ssh-ing to ourselves.
if [[ "$(uname)" != Darwin ]]; then
  exec bash Dual_Archi/tools/agrisentry.sh "${1:-status}" ${2:+"$2"}
fi
source .pi_host.sh
./sync_pi.sh push >/dev/null || true
$SSH -t "$PI" "bash ~/THESIS/Dual_Archi/tools/agrisentry.sh ${1:-status} ${2:-}"
