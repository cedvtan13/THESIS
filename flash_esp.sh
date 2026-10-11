#!/usr/bin/env bash
# flash_esp.sh -- build the firmware on the Mac and flash it to the ESP32 via the Pi.
#   1. pio run  (Dual_Archi/Dual_Archi_Firmware)
#   2. copy bootloader/partitions/firmware.bin to the Pi (~/fw_main, also ~/*.bin)
#   3. Pi drives EN/BOOT (BCM 23/24), flashes, resets, shows the BOOT lines
set -euo pipefail
cd "$(dirname "$0")"
source .pi_host.sh

PIO=$(command -v pio || echo "$HOME/.platformio/penv/bin/pio")
FW=Dual_Archi/Dual_Archi_Firmware
echo "== build"
"$PIO" run -d "$FW" | tail -n 3
B="$FW/.pio/build/esp32-s3-devkitc-1"

echo "== copy to $PI_HOST"
./sync_pi.sh push >/dev/null
$SSH "$PI" "mkdir -p ~/fw_main"
scp -q -o HostKeyAlias=groupb.local "$B"/{bootloader,partitions,firmware}.bin "$PI:fw_main/"
$SSH "$PI" "cp ~/fw_main/*.bin ~/"

echo "== flash"
$SSH -t "$PI" "python3 -u ~/THESIS/Dual_Archi/tools/flash_esp.py ~/fw_main"
