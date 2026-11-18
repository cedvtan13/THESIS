#!/usr/bin/env bash
# gpr_view.sh -- see what the GPR algorithm measures, right now.
# Takes a fresh frame on the Pi with the same locked camera + mask + ROIs as the
# noon capture (the noon frame itself is never stored), draws the counted plant
# pixels, and opens the picture on this Mac:  Desktop/Thesis GPR Views/.
# Writes no data. Don't run it while ./live_feed.sh has the camera.
set -uo pipefail
cd "$(dirname "$0")"
source .pi_host.sh
./sync_pi.sh push >/dev/null || true
$SSH "$PI" "cd ~/THESIS/Dual_Archi && LIBCAMERA_LOG_LEVELS='*:ERROR' python3 tools/gpr_view.py --out /tmp/gpr_view.png" || exit 1
DEST="$HOME/Desktop/Thesis GPR Views"
mkdir -p "$DEST"
out="$DEST/gpr_view_$(date +%Y-%m-%d_%H%M%S).png"
scp -q -o HostKeyAlias=groupb.local "$PI:/tmp/gpr_view.png" "$out" && echo "saved: $out" && open "$out"
