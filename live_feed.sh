#!/usr/bin/env bash
# live_feed.sh -- start the pot-alignment stream on the Pi and open it in the browser.
#   ./live_feed.sh               1 fps
#   ./live_feed.sh --fps 3
#   ./live_feed.sh --light       capture light on while streaming
# Ctrl+C stops it (and frees the camera for captures / bench tests).
set -uo pipefail
cd "$(dirname "$0")"
source .pi_host.sh
./sync_pi.sh push >/dev/null || true
( sleep 12; open "http://$PI_HOST:5000" ) &
echo "opening http://$PI_HOST:5000 in ~12 s (camera warm-up) -- Ctrl+C here to stop"
$SSH -t "$PI" "cd ~/THESIS/Dual_Archi && LIBCAMERA_LOG_LEVELS='*:ERROR' python3 -u live_feed.py $*"
