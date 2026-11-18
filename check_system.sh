#!/usr/bin/env bash
# ==============================================================================
# check_system.sh -- Comprehensive Daily System & ROI Alignment Inspector
# ==============================================================================
# Usage:
#   ./check_system.sh             Standard daily inspection (status + ROI check + pull)
#   ./check_system.sh --live-roi  Take a fresh live frame right now and check ROI drift
#   ./check_system.sh --quick     Skip data pull, show rapid status & alignment check
#   PI_HOST=172.20.10.x ./check_system.sh   Manually specify Pi IP
# ==============================================================================
set -uo pipefail

cd "$(dirname "$0")"

# ANSI Colors
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
DIM="\033[2m"
RESET="\033[0m"

LIVE_ROI=false
QUICK_MODE=false
for arg in "$@"; do
  case "$arg" in
    --live-roi) LIVE_ROI=true ;;
    --quick) QUICK_MODE=true ;;
    -h|--help)
      echo "Usage: $0 [--live-roi] [--quick]"
      echo "  --live-roi   Take a live photo via Camera Module 3 to test pot alignment"
      echo "  --quick      Skip rsync data pull (fast check)"
      exit 0
      ;;
  esac
done

echo -e "${BOLD}${CYAN}======================================================${RESET}"
echo -e "${BOLD}${CYAN}    Pechay Growth Monitoring — Daily System & ROI Health Check        ${RESET}"
echo -e "${BOLD}${CYAN}======================================================${RESET}"
echo -e "${DIM}Timestamp: $(date '+%Y-%m-%d %H:%M:%S %Z')${RESET}\n"

# ------------------------------------------------------------------------------
# 1. Network Discovery & Host Resolution
# ------------------------------------------------------------------------------
echo -e "${BOLD}[1/5] Discovering Raspberry Pi Zero 2W...${RESET}"
if ! source .pi_host.sh 2>/dev/null; then
  echo -e "${RED}✘ Pi not detected on the network.${RESET}"
  echo -e "\n${YELLOW}Troubleshooting Steps:${RESET}"
  echo "  1. Verify the iPhone/Android Personal Hotspot is turned ON."
  echo "     (On iPhone 12+, make sure 'Maximize Compatibility' is enabled)."
  echo "  2. Confirm the Raspberry Pi is powered (green ACT LED blinking or steady)."
  echo "  3. Wait 15-30 seconds for the Pi to auto-join the Wi-Fi."
  echo "  4. Check the hotspot client list or ARP table:"
  echo "     arp -an | grep -i '88:a2:9e:51:89:a0'"
  echo "  5. If you know the IP, run: PI_HOST=<ip> $0"
  exit 1
fi

echo -e "${GREEN}✔ Connected to Pi at ${BOLD}$PI${RESET} (Host: $PI_HOST)"

# ------------------------------------------------------------------------------
# 2. Clock Synchronization & Time Offset
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[2/5] Checking System Clock & Network Time (NTP)...${RESET}"
ntp_status=$($SSH "$PI" "timedatectl show -p NTPSynchronized --value 2>/dev/null" || echo "unknown")
pi_epoch=$($SSH "$PI" "date +%s" 2>/dev/null || echo 0)
mac_epoch=$(date +%s)
offset=$(( pi_epoch - mac_epoch ))

if [[ "$ntp_status" == "yes" && ${offset#-} -le 5 ]]; then
  echo -e "${GREEN}✔ NTP Synchronized${RESET} (Offset vs Mac: ${offset}s)"
elif [[ "$ntp_status" == "yes" ]]; then
  echo -e "${YELLOW}▲ NTP Synced, but offset vs Mac is ${offset}s${RESET} (Check Mac or Pi timezone)"
else
  echo -e "${RED}✘ NTP NOT SYNCHRONIZED${RESET} (Offset: ${offset}s). Noon capture requires synced clock!"
fi

# ------------------------------------------------------------------------------
# 3. Remote Panel Summary (Sensors, Watering, Run 2 Progress)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[3/5] Querying System Telemetry & Run Status...${RESET}"
$SSH "$PI" "bash ~/THESIS/Dual_Archi/tools/panel.sh" || {
  echo -e "${RED}✘ Failed to retrieve panel status from Pi.${RESET}"
}

# ------------------------------------------------------------------------------
# 4. ROI Alignment & Camera Drift Check
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[4/5] Evaluating Pot ROI Alignment & Camera Drift...${RESET}"

mkdir -p "$HOME/Desktop" _pi_data/latest_inspection

if [ "$LIVE_ROI" = true ]; then
  echo -e "${CYAN}→ Taking live picture with Camera Module 3...${RESET}"
  $SSH "$PI" "cd ~/THESIS/Dual_Archi && python3 tools/roi_drift.py --capture --out /tmp/check_roi_drift.jpg" > /tmp/roi_drift_out.txt 2>&1 || true
else
  latest_frame=$($SSH "$PI" "ls -t ~/agrisentry_data/frames/D*.png 2>/dev/null | head -n 1" || true)
  if [[ -n "$latest_frame" ]]; then
    frame_name=$(basename "$latest_frame")
    echo -e "${DIM}→ Testing alignment on latest noon frame: ${frame_name}${RESET}"
    $SSH "$PI" "cd ~/THESIS/Dual_Archi && python3 tools/roi_drift.py --frame '$latest_frame' --out /tmp/check_roi_drift.jpg" > /tmp/roi_drift_out.txt 2>&1 || true
  else
    echo -e "${YELLOW}▲ No archived noon frames found in ~/agrisentry_data/frames/. Taking live photo instead...${RESET}"
    $SSH "$PI" "cd ~/THESIS/Dual_Archi && python3 tools/roi_drift.py --capture --out /tmp/check_roi_drift.jpg" > /tmp/roi_drift_out.txt 2>&1 || true
  fi
fi

if [ -f /tmp/roi_drift_out.txt ]; then
  cat /tmp/roi_drift_out.txt

  # Extract median shift
  median_line=$(grep "median shift:" /tmp/roi_drift_out.txt || true)
  rims_found=$(grep -o "[0-9]/9 rims found" /tmp/roi_drift_out.txt || echo "0/9")
  
  # Parse shift magnitudes
  shift_x=$(echo "$median_line" | awk '{print $3}' | tr -d '+px')
  shift_y=$(echo "$median_line" | awk '{print $5}' | tr -d '+px')
  
  # Fetch the annotated alignment verification image
  scp -q -o HostKeyAlias=groupb.local "$PI:/tmp/check_roi_drift.jpg" "_pi_data/latest_inspection/roi_drift_check.jpg" 2>/dev/null || true
  scp -q -o HostKeyAlias=groupb.local "$PI:/tmp/check_roi_drift.jpg" "$HOME/Desktop/Thesis_ROI_Check.jpg" 2>/dev/null || true

  echo ""
  if [[ -n "$shift_x" && -n "$shift_y" ]]; then
    # Calculate approximate Euclidean shift
    mag=$(python3 -c "import math; print(int(math.hypot(float('${shift_x:-0}'), float('${shift_y:-0}'))))" 2>/dev/null || echo 0)
    if [ "$mag" -le 10 ]; then
      echo -e "${GREEN}${BOLD}✔ ROI STATUS: EXCELLENT ALIGNMENT${RESET} (Drift: ${mag} px, $rims_found)"
      echo -e "  Camera is solidly positioned. Yellow circles closely match physical pots."
    elif [ "$mag" -le 25 ]; then
      echo -e "${YELLOW}${BOLD}▲ ROI STATUS: MINOR DRIFT DETECTED${RESET} (Drift: ${mag} px, $rims_found)"
      echo -e "  Pots or camera have shifted slightly. Still acceptable, but inspect:"
      echo -e "  $HOME/Desktop/Thesis_ROI_Check.jpg"
    else
      echo -e "${RED}${BOLD}✘ ROI STATUS: SIGNIFICANT MISALIGNMENT${RESET} (Drift: ${mag} px, $rims_found)"
      echo -e "  Camera or pots moved! Run recentering or inspect camera mount:"
      echo -e "  ssh $PI 'cd ~/THESIS/Dual_Archi && python3 tools/roi_drift.py --capture --apply'"
    fi
  else
    echo -e "${YELLOW}▲ Rim detection incomplete. Please review Desktop image by eye.${RESET}"
  fi
  echo -e "${DIM}  Inspection image saved to: $HOME/Desktop/Thesis_ROI_Check.jpg${RESET}"
fi

# ------------------------------------------------------------------------------
# 5. Local Backup & Data Pull
# ------------------------------------------------------------------------------
if [ "$QUICK_MODE" = false ]; then
  echo -e "\n${BOLD}[5/5] Backing up telemetry and logs to _pi_data/...${RESET}"
  ./sync_pi.sh pull | grep -E "sent|received|total size" || true
  echo -e "${GREEN}✔ Local backup complete.${RESET}"
else
  echo -e "\n${DIM}[5/5] Skipping data pull (--quick enabled).${RESET}"
fi

echo -e "\n${BOLD}${CYAN}======================================================${RESET}"
echo -e "${BOLD}${GREEN}✔ Daily Check Complete.${RESET}"
echo -e "${BOLD}${CYAN}======================================================${RESET}"
