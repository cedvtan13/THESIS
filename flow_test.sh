#!/usr/bin/env bash
# flow_test.sh -- measure each valve's real flow rate, from the Mac.
#   ./flow_test.sh                          all 9 pots, 5 s pump per run
#   ./flow_test.sh --pots 1,4,7 --runs 3    chosen pots, 3 runs each
#   ./flow_test.sh --seconds 10             longer runs (max 15 s)
# Each run: valve opens -> pump 5 s -> pump off -> valve closes. Type the mL
# you collected; it prints mL/s per valve and what PUMP_FLOW_ML_PER_S should be.
set -uo pipefail
cd "$(dirname "$0")"
source .pi_host.sh
./sync_pi.sh push >/dev/null || true
$SSH -t "$PI" "python3 -u ~/THESIS/Dual_Archi/tools/flow_test.py $*"
