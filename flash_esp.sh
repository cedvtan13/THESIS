#!/usr/bin/env bash
# flash_esp.sh -- build firmware on the Mac and flash it to the ESP32 via the Pi.
#
#   ./flash_esp.sh                 the REAL system firmware:
#                                  Dual_Archi/Dual_Archi_Firmware/src/main.cpp
#   ./flash_esp.sh <project dir>   any other PlatformIO project for the ESP32-S3,
#                                  e.g. ./flash_esp.sh Test/TestBench
#
#   1. pio run  (builds main.cpp + libraries from that project's platformio.ini)
#   2. copy bootloader/partitions/firmware.bin to the Pi
#   3. Pi drives EN/BOOT (BCM 23/24), flashes, resets, shows the BOOT lines
#
# Flashing another project REPLACES the system firmware on the ESP32. Run
# ./flash_esp.sh with no argument afterwards to put the real firmware back.
set -euo pipefail
cd "$(dirname "$0")"
source .pi_host.sh

PIO=$(command -v pio || echo "$HOME/.platformio/penv/bin/pio")
MAIN_FW=Dual_Archi/Dual_Archi_Firmware
FW="${1:-$MAIN_FW}"
FW="${FW%/}"
[[ -f "$FW/platformio.ini" ]] || { echo "no platformio.ini in $FW"; exit 1; }
# The board is an ESP32-S3; a project built for another chip would not run.
grep -q "esp32-s3" "$FW/platformio.ini" || {
  echo "$FW is not built for the ESP32-S3 (check 'board =' in its platformio.ini)"; exit 1; }

if [[ "$FW" == "$MAIN_FW" ]]; then
  echo "== flashing the SYSTEM firmware ($FW/src/main.cpp)"
  PI_DIR=fw_main
else
  echo "== flashing a TEST project ($FW) -- this replaces the system firmware"
  echo "   restore it afterwards with: ./flash_esp.sh"
  PI_DIR=fw_test
fi

echo "== build"
"$PIO" run -d "$FW" | tail -n 3
B=$(ls -td "$FW"/.pio/build/*/ | head -n 1)

echo "== copy to $PI_HOST"
./sync_pi.sh push >/dev/null
$SSH "$PI" "mkdir -p ~/$PI_DIR"
scp -q -o HostKeyAlias=groupb.local "$B"/{bootloader,partitions,firmware}.bin "$PI:$PI_DIR/"
# ~/*.bin is the Pi's copy of the system firmware (used by ~/tests/flash_esp.py)
[[ $PI_DIR == fw_main ]] && $SSH "$PI" "cp ~/fw_main/*.bin ~/"

echo "== flash"
$SSH -t "$PI" "python3 -u ~/THESIS/Dual_Archi/tools/flash_esp.py ~/$PI_DIR"
