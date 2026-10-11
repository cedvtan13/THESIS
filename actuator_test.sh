#!/usr/bin/env bash
# actuator_test.sh -- interactive relay tester (solenoids, pump, fans, light), from the Mac.
# Relays only switch when the firmware has ACTUATORS_ENABLED = true (top of main.cpp)
# and was flashed with ./flash_esp.sh. Leaves pi-link stopped.
set -uo pipefail
cd "$(dirname "$0")"
source .pi_host.sh
./sync_pi.sh push >/dev/null || true
$SSH -t "$PI" "python3 -u ~/THESIS/Dual_Archi/tools/actuator_test.py"
