#!/usr/bin/env bash
# roi_view.sh -- take a fresh picture on the Pi with the pot circles (ROIs) drawn,
# copy it to this Mac's Desktop and open it. Writes no data on the Pi.
#   ./roi_view.sh
# Don't run it at 12:00-12:50 (the noon capture needs the camera).
set -uo pipefail
cd "$(dirname "$0")"
PI_HOST="${PI_HOST:-172.20.10.7}"
PI="crk@$PI_HOST"
SSH=(ssh -o HostKeyAlias=groupb.local -o ConnectTimeout=8)
scp -q -o HostKeyAlias=groupb.local Dual_Archi/tools/roi_view.py "$PI:THESIS/Dual_Archi/tools/roi_view.py" || {
  echo "Pi not reachable at $PI_HOST -- is the laptop on the hotspot?"; exit 1; }
echo "taking a picture on the Pi..."
"${SSH[@]}" "$PI" "cd ~/THESIS/Dual_Archi && LIBCAMERA_LOG_LEVELS='*:ERROR' python3 tools/roi_view.py /tmp/roi_view.jpg" 2>&1 \
  | grep -v '^\[capture_gpr\]' || true
out="$HOME/Desktop/ROI_view_$(date +%H%M%S).jpg"
scp -q -o HostKeyAlias=groupb.local "$PI:/tmp/roi_view.jpg" "$out" && echo "saved: $out" && open "$out"
