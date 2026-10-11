#!/usr/bin/env bash
# bench_test.sh -- full rig health check, run from the Mac.
#   ESP32 link, BMP388, soil moisture (raw + %), optional relays, and a real
#   camera capture with the ROI/HSV masking overlay, copied to
#   ~/Desktop/AgriSentry Bench Photos/ on the Mac and opened.
#   Writes no data CSVs. Leaves the pi-link service STOPPED (testing mode).
#
#   ./bench_test.sh                 sensors + camera
#   ./bench_test.sh --relays        also click every relay (needs actuators enabled)
#   ./bench_test.sh --no-camera     skip the photo
set -uo pipefail
cd "$(dirname "$0")"
source .pi_host.sh

./sync_pi.sh push >/dev/null || echo "(code push failed -- running whatever is on the Pi)"
$SSH -t "$PI" "python3 -u ~/THESIS/Dual_Archi/tools/bench_check.py $*"
rc=$?

if [[ " $* " != *" --no-camera "* ]]; then
  # Photos land on the Mac desktop, one per run, named by date/time.
  DEST="$HOME/Desktop/AgriSentry Bench Photos"
  mkdir -p "$DEST"
  out="$DEST/overlay_$(date +%Y-%m-%d_%H%M%S).png"
  if scp -q -o HostKeyAlias=groupb.local "$PI:/tmp/agrisentry_bench/bench_overlay.png" "$out"; then
    echo "overlay saved to $out"
    open "$out"
  else
    echo "no overlay image came back (camera step failed?)"
  fi
fi
exit $rc
