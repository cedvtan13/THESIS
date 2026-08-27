#!/usr/bin/env python3
"""
capture_gpr.py -- daily noon vision pipeline on the Raspberry Pi Zero 2W.  v4

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Implements Appendix G. One frame at 12:00, HSV threshold inside each pot's ROI,
Green Pixel Ratio per pot, appended to growth_dataset.csv together with the soil
moisture pulled from the ESP32-S3. The raw frame is discarded afterwards to
enforce storage autonomy.

Deliverable 3 (per-pot GPR time-series) and Deliverable 5 (the SM column of the
315-row training dataset) both come out of this script.

Install (Bookworm):
    python3 -m venv --system-site-packages ~/thesis-env
    source ~/thesis-env/bin/activate
    pip install opencv-python-headless numpy pyserial

  --system-site-packages is REQUIRED. Picamera2 is installed system-wide by apt
  and cannot be pip-installed into an isolated venv.

Cron (crontab -e):
    0 12 * * * /home/pi/thesis-env/bin/python3 /home/pi/thesis/capture_gpr.py >> /home/pi/thesis/cron.log 2>&1

Offline testing, no camera and no ESP32 required -- use this now, before the
rig exists:
    python3 capture_gpr.py --test-image vision/test_img/pechay_test.jpeg --no-write
    python3 capture_gpr.py --test-image frame.jpg --debug-overlay /tmp/ov.png

CAMERA MODULE 3 -- TWO THINGS THAT DIFFER FROM v2
  1. Vertical FOV is 41 deg, not 48.8 deg. Covering the 900 mm array needs a
     minimum of 1204 mm, so the nominal mounting height is about 1350 mm, NOT
     the 1100 mm derived for v2. At 1100 mm the v3 cannot see the whole array.
     Section III.B needs updating.
  2. v3 has autofocus. It MUST be locked. If focus hunts between days, edge
     sharpness changes and the green pixel count drifts independently of growth.
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pi_link import get_sm_snapshot          # noqa: E402

BASE = os.path.expanduser("~/thesis")
ROI_FILE = os.path.join(BASE, "pot_rois.json")
OUT_CSV = os.path.join(BASE, "growth_dataset.csv")
SOWING_DATE = "2026-08-15"                   # D = 1. UPDATE AT ACTUAL SOWING.

CAPTURE_SIZE = (2304, 1296)                  # 2x binned from 4608x2592

# ---------------------------------------------------------------------------
# HSV THRESHOLD
# ---------------------------------------------------------------------------
# The manuscript writes the mask as "35 deg <= Hue <= 85 deg". Those NUMBERS
# are correct, but the degree symbols are not: 35 and 85 are OpenCV hue units,
# not degrees. OpenCV stores hue on a 0-179 scale, so 35-85 spans 70-170 deg on
# the true colour wheel, which is exactly where leaf green lives (measured:
# real Pechay-type greens land at OpenCV H 41-57).
#
# Do NOT "convert" 35-85 to 18-42 by halving. That was tested and returns
# 0.00 % GPR on a healthy green canopy, because it selects orange-yellow
# instead of green. Keep these values in OpenCV units. Fix the manuscript text,
# not the code.
HUE_LO, HUE_HI = 35, 85                      # OpenCV units == 70-170 deg
SAT_MIN, VAL_MIN = 40, 40                    # reject grey soil and shadow
MORPH_KERNEL = np.ones((5, 5), np.uint8)     # opening, severs leaf bridges

# GPR jumping more than this in one day is implausible biologically and usually
# means the rig moved or the lighting changed. Flagged, not discarded.
ANOMALY_DELTA = 8.0

CSV_HEADER = ["day", "timestamp", "pot_id", "sm_pct", "raw_gpr", "smooth_gpr",
              "green_px", "total_px", "flag"]


def day_index():
    sown = datetime.strptime(SOWING_DATE, "%Y-%m-%d").date()
    return (datetime.now().date() - sown).days + 1


# ---------------------------------------------------------------------------
# CAPTURE
# ---------------------------------------------------------------------------
def capture_frame():
    """One stabilised frame with every automatic control locked.

    Locking matters more than it looks. The methodology treats lighting as a
    strict control variable, but auto-exposure and auto-white-balance actively
    fight that: if the camera compensates for a duller day the HSV values shift
    and the GPR moves without the plant changing."""
    from picamera2 import Picamera2
    from libcamera import controls

    cam = Picamera2()
    cfg = cam.create_still_configuration(main={"size": CAPTURE_SIZE})
    cam.configure(cfg)
    cam.start()

    cam.set_controls({
        "AfMode": controls.AfModeEnum.Manual,
        "LensPosition": 2.5,        # MEASURE ONCE on the rig, then never change
        "AeEnable": False,
        "ExposureTime": 8000,       # MEASURE under the final LED array
        "AnalogueGain": 1.0,
        "AwbEnable": False,
        "ColourGains": (1.8, 1.6),  # MEASURE ONCE
    })

    time.sleep(2)                   # let the locked settings take effect
    frame = cam.capture_array()
    cam.stop()
    cam.close()
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# GPR
# ---------------------------------------------------------------------------
def roi_mask(shape_hw, roi, circular):
    """Pixels belonging to this pot.

    A square ROI drawn around a circular pot puts ~21.5 % bench and rim inside
    the denominator, so 'GPR' stops being the fraction of POT area covered and
    becomes the fraction of a rectangle. Circular is the truer denominator and
    is the default; set "circular": false in pot_rois.json to fall back."""
    h, w = shape_hw
    m = np.zeros((h, w), np.uint8)
    if circular:
        cx, cy = roi["x"] + roi["w"] // 2, roi["y"] + roi["h"] // 2
        r = min(roi["w"], roi["h"]) // 2
        cv2.circle(m, (cx, cy), r, 255, -1)
    else:
        m[roi["y"]:roi["y"] + roi["h"], roi["x"]:roi["x"] + roi["w"]] = 255
    return m


def green_mask(hsv):
    """Threshold + opening for the WHOLE frame, computed once.

    This used to run inside the per-pot loop, i.e. nine times over the full
    2304x1296 frame. On a Zero 2W the 5x5 opening alone is the most expensive
    step in the script, so that was ~9x more work than needed. Hoisting it out
    is also slightly more correct: opening the whole frame severs leaf bridges
    globally, whereas per-ROI opening would treat each ROI edge as a boundary."""
    m = cv2.inRange(hsv,
                    np.array([HUE_LO, SAT_MIN, VAL_MIN], np.uint8),
                    np.array([HUE_HI, 255, 255], np.uint8))
    # Severs thin leaf bridges spanning adjacent regions (Section III.C).
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, MORPH_KERNEL)


def gpr_for_roi(green_all, shape_hw, roi, circular):
    """Green Pixel Ratio inside one pot, as a percentage.

    Spatial attribution rule, Section III.C: every green pixel inside this ROI
    belongs to this pot; anything outside is discarded regardless of which
    plant it grew from."""
    area = roi_mask(shape_hw, roi, circular)
    green = cv2.bitwise_and(green_all, green_all, mask=area)

    g = int(np.count_nonzero(green))
    total = int(np.count_nonzero(area))
    return (g / total * 100.0 if total else 0.0), g, total, green


def previous_gpr_all():
    """{pot_id: last raw_gpr} in one pass instead of re-reading the CSV 9x."""
    if not os.path.exists(OUT_CSV):
        return {}
    out = {}
    with open(OUT_CSV, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[row["pot_id"]] = float(row["raw_gpr"])
            except (KeyError, ValueError):
                continue
    return out


def validate_rois(rois, shape_hw):
    """Refuse to run on ROIs that fall outside the frame or overlap.

    Cheap insurance: a bad pot_rois.json silently produces plausible-looking
    numbers for 35 days, and there is no way to recover the run afterwards."""
    h, w = shape_hw
    problems = []
    boxes = {}
    for pid in [f"P-0{i}" for i in range(1, 10)]:
        if pid not in rois:
            problems.append(f"{pid}: missing from pot_rois.json")
            continue
        r = rois[pid]
        if r["x"] < 0 or r["y"] < 0 or r["x"] + r["w"] > w or r["y"] + r["h"] > h:
            problems.append(f"{pid}: box {r['x']},{r['y']} {r['w']}x{r['h']} "
                            f"falls outside the {w}x{h} frame")
        boxes[pid] = r
    ids = list(boxes)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = boxes[ids[i]], boxes[ids[j]]
            if (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and
                    a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]):
                problems.append(f"{ids[i]} and {ids[j]} overlap")
    return problems


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Daily noon GPR capture")
    ap.add_argument("--test-image", help="use this image instead of the camera")
    ap.add_argument("--no-write", action="store_true", help="do not touch the CSV")
    ap.add_argument("--no-sm", action="store_true", help="skip the ESP32 read")
    ap.add_argument("--debug-overlay", help="write an annotated PNG here")
    ap.add_argument("--roi-file", default=ROI_FILE)
    args = ap.parse_args()

    with open(args.roi_file) as f:
        cfg = json.load(f)
    rois = cfg.get("rois", cfg)                    # tolerate the flat v3 layout
    circular = bool(cfg.get("circular", True))

    if args.test_image:
        frame = cv2.imread(args.test_image)
        if frame is None:
            sys.exit(f"could not read {args.test_image}")
        print(f"[capture_gpr] TEST MODE on {args.test_image} {frame.shape[1]}x{frame.shape[0]}")
    else:
        frame = capture_frame()

    problems = validate_rois(rois, frame.shape[:2])
    if problems:
        for p in problems:
            print(f"[capture_gpr] ROI ERROR: {p}", file=sys.stderr)
        sys.exit("refusing to run on invalid ROIs -- fix pot_rois.json "
                 "(see make_rois.py)")

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green_all = green_mask(hsv)          # computed once, not nine times

    # --- soil moisture, via the daemon so the serial port has one owner ---
    sm_values = None if args.no_sm else get_sm_snapshot()
    if sm_values is None or len(sm_values) != 9:
        if sm_values is not None:
            print(f"[capture_gpr] SM snapshot had {len(sm_values)} values, "
                  "expected 9 -- writing NaN", file=sys.stderr)
        sm_values = [None] * 9

    prev = previous_gpr_all()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    d = day_index()
    overlay = frame.copy() if args.debug_overlay else None
    rows = []

    for i in range(9):
        pot_id = f"P-0{i + 1}"
        gpr, green, total, mask = gpr_for_roi(
            green_all, frame.shape[:2], rois[pot_id], circular)

        p = prev.get(pot_id)
        flag = 1 if (p is not None and abs(gpr - p) > ANOMALY_DELTA) else 0

        sm = sm_values[i]
        sm_str = "NaN" if sm is None else f"{sm:.1f}"

        # smooth_gpr is intentionally blank. The 3-day centred moving average
        # needs days either side of each point, so it is computed offline after
        # harvest, not here (Appendix G closing note).
        rows.append([d, stamp, pot_id, sm_str, f"{gpr:.2f}", "",
                     green, total, flag])
        print(f"{pot_id}  SM={sm_str:>6}  GPR={gpr:6.2f}%  "
              f"({green}/{total} px)  flag={flag}")

        if overlay is not None:
            r = rois[pot_id]
            overlay[mask > 0] = (0, 0, 255)
            cv2.rectangle(overlay, (r["x"], r["y"]),
                          (r["x"] + r["w"], r["y"] + r["h"]), (255, 255, 0), 2)
            cv2.putText(overlay, f"{pot_id} {gpr:.1f}%", (r["x"], r["y"] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    if overlay is not None:
        cv2.imwrite(args.debug_overlay, overlay)
        print(f"[capture_gpr] overlay -> {args.debug_overlay}")

    if args.no_write:
        print("[capture_gpr] --no-write: CSV untouched")
        return

    new_file = not os.path.exists(OUT_CSV)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(CSV_HEADER)
        w.writerows(rows)

    # The raw frame was never written to disk in the first place -- it lives in
    # memory only and dies with the process. Storage autonomy by construction.
    print(f"[capture_gpr] day {d} written to {OUT_CSV}")


if __name__ == "__main__":
    main()
