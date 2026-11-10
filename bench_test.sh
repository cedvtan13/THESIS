#!/usr/bin/env bash
# bench_test.sh -- full rig health check. Run it on the Mac OR on the Pi.
#   ESP32 link, BMP388, soil moisture (raw + %), optional relays, and a real
#   camera capture with the ROI/HSV masking overlay. The photo always ends up
#   on the MAC in ~/Desktop/AgriSentry Bench Photos/ and is opened there.
#   Writes no data CSVs. Leaves the pi-link service STOPPED (testing mode).
#
#   ./bench_test.sh                 sensors + camera
#   ./bench_test.sh --relays        also click every relay (needs actuators enabled)
#   ./bench_test.sh --no-camera     skip the photo
#
# Run on the Pi (over ssh from the Mac), the photo is sent back to the Mac you
# connected from. That needs the Pi's key in the Mac's ~/.ssh/authorized_keys
# (one-time setup, see DEPLOYMENT_NOTES.md). Override the target with
# MAC_HOST=<ip> / MAC_USER=<name>.
set -uo pipefail
cd "$(dirname "$0")"

PHOTO_DIR="Desktop/AgriSentry Bench Photos"          # relative to the Mac's home
NAME="overlay_$(date +%Y-%m-%d_%H%M%S).png"
PI_IMG=/tmp/agrisentry_bench/bench_overlay.png
want_photo() { [[ " $* " != *" --no-camera "* ]]; }

if [[ "$(uname)" == Darwin ]]; then
  # ---- on the Mac: run the check on the Pi, pull the photo back ----
  source .pi_host.sh
  ./sync_pi.sh push >/dev/null || echo "(code push failed -- running whatever is on the Pi)"
  $SSH -t "$PI" "python3 -u ~/THESIS/Dual_Archi/tools/bench_check.py $*"
  rc=$?
  if want_photo "$@"; then
    mkdir -p "$HOME/$PHOTO_DIR"
    out="$HOME/$PHOTO_DIR/$NAME"
    if scp -q -o HostKeyAlias=groupb.local "$PI:$PI_IMG" "$out"; then
      echo "photo saved on the Mac: $out"
      open "$out"
    else
      echo "no photo came back (camera step failed?)"
    fi
  fi
  exit $rc
fi

# ---- on the Pi: run the check here, push the photo to the Mac ----
python3 -u Dual_Archi/tools/bench_check.py "$@"
rc=$?
if want_photo "$@" && [[ -f $PI_IMG ]]; then
  MAC_HOST="${MAC_HOST:-${SSH_CLIENT%% *}}"     # the Mac you ssh'd in from
  MAC_USER="${MAC_USER:-moapilaw}"
  MAC_SSH=(ssh -o BatchMode=yes -o ConnectTimeout=5 "$MAC_USER@$MAC_HOST")
  if [[ -n "$MAC_HOST" ]] &&
     "${MAC_SSH[@]}" "mkdir -p '$PHOTO_DIR' && cat > '$PHOTO_DIR/$NAME'" < "$PI_IMG"; then
    echo "photo sent to the Mac: ~/$PHOTO_DIR/$NAME"
    "${MAC_SSH[@]}" "open '$PHOTO_DIR/$NAME'" || true
  else
    echo "could not send the photo to the Mac (${MAC_HOST:-no Mac address}) -- it is on the Pi at $PI_IMG"
    echo "  fix: run ./bench_test.sh from the Mac instead, or see 'Bench photos when running on the Pi'"
    echo "       in DEPLOYMENT_NOTES.md (one-time key setup)"
  fi
fi
exit $rc
