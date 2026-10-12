#!/usr/bin/env bash
# system.sh -- start / stop / check the AgriSentry system on the Pi, from the Mac.
#   ./system.sh start        pi-link logger + 12:00 GPR capture ON  (deployment)
#   ./system.sh stop         both OFF                                (testing)
#   ./system.sh status       what's running, day number, CSV row counts
#   ./system.sh reset-data   archive current CSVs and start empty ones (asks first)
#   ./system.sh ups-test     logger only + mark the start of a UPS runtime test
# On the Pi itself:  ~/thesis/tools/agrisentry.sh start|stop|status|reset-data
set -uo pipefail
cd "$(dirname "$0")"
source .pi_host.sh
./sync_pi.sh push >/dev/null || true
$SSH -t "$PI" "bash ~/THESIS/Dual_Archi/tools/agrisentry.sh ${1:-status}"
