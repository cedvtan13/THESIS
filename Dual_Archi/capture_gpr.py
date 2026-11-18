#!/usr/bin/env python3
"""
capture_gpr.py -- daily noon vision pipeline on the Raspberry Pi Zero 2W.  v5

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Implements Appendix G. One frame at 12:00, HSV threshold inside each pot's ROI,
Green Pixel Ratio per pot, appended to growth_dataset.csv together with the soil
moisture pulled from the ESP32-S3. From D12 (2026-10-17) the raw noon frame is
also kept as a lossless PNG in ~/agrisentry_data/frames/ (~3 MB/day), so the GPR
can be recomputed if the ROIs or mask ever change; before that it was discarded.

Deliverable 3 (per-pot GPR time-series) and Deliverable 5 (the SM column of the
training dataset, 9 pots x D8-D30 = 207 rows) both come out of this script.

-----------------------------------------------------------------------------
CHANGES FROM v4 -- read these before running
-----------------------------------------------------------------------------
 1. SYNTAX FIX. v4 had a stray shell command ("sh ced@10.195...") pasted between
    validate_rois() and main(). The file would not even parse.

 2. MORPH_K: 9 -> 3.  The v4 comment claimed "a 5x5 opening only removes bridges
    up to 2 px wide -- a 3 px bridge survives it intact". That was measured and
    is FALSE. A k x k opening destroys anything NARROWER than k px:

        bridge  3x3   5x5   7x7   9x9
          2px   GONE  GONE  GONE  GONE
          3px   ok    GONE  GONE  GONE
          5px   ok    ok    GONE  GONE
          9px   ok    ok    ok    ok

    Measured against the real D=5 seedling photo (test_2.png), fraction of
    genuine green pixels retained:  3x3 = 98.4%,  5x5 = 95.4%,  9x9 = 75.0%.
    At 9x9 pot P-05 read 0.000% for a seedling plainly visible in the frame.
    At 1.34 px/mm, 9x9 erases anything thinner than 6.7 mm -- wider than a
    pechay cotyledon. It is sized to delete the plant during weeks 1-2.

    Note also that cross-pot leaf bridges are not inside ANY ROI: the ROI is
    90% of the rim and there is ~130 mm of bare soil between rims at 330 mm
    pitch. The guard margin already does the job Section III.C credits to the
    opening. The kernel's remaining useful role is killing speckle noise.

 3. SOWING_DATE is now read from ~/thesis/sowing_date.txt when present, and
    day_index() refuses to run outside D = 1..35. v4 shipped a hardcoded past
    date with no bounds check -- running it before sowing wrote a wrong D, and
    D is a term in the model.

 4. DUPLICATE-DAY GUARD. v4 appended unconditionally, so a second run in one day
    silently wrote 18 rows instead of 9. Duplicated plant-days over-weight that
    day in every LOOCV fold it appears in, inflating R². Now it refuses.

 5. pi_link is imported lazily, so --no-sm --test-image works on a machine with
    no pyserial installed.

 6. Camera height. v4's docstring said 1350 mm for a 900 mm array, measured to
    the floor. Both were wrong. Clearance must be measured to the CANOPY plane
    (pot height + plant height ~= 430 mm), not the floor, because the canopy is
    closer to the lens and clips first. For the real 860 mm pot bounding box at
    330 mm pitch, the v3's 41 deg vertical FOV needs the camera at 1600-1650 mm
    above the floor. Section III.B still needs updating -- it also still names
    the Camera Module V2 (48.8 deg VFOV), which is not the camera in use.

 7. NEW DIAGNOSTIC COLUMNS (GPR itself is unchanged -- these are additions):
      raw_gpr_noopen  same GPR with the opening skipped. Run both for the first
                      week; if they track, the kernel is not eating your plants.
      terr_gpr        green fraction inside a TERRITORY circle (the pot's
                      Voronoi cell at your pitch) instead of the pot rim. The
                      rim ROI saturates once canopy diameter exceeds ~180 mm,
                      which happens around D=24-28 while fresh weight is still
                      climbing. terr_gpr keeps rising. Costs one extra mask.
      canopy_w_px/h_px  bounding box of the largest green blob in the ROI. Keeps
                      growing after area saturates.

 8. validate_rois() now does a circle-distance check when circular=True. v4
    tested bounding boxes, which can overlap while the circles do not -- it
    could refuse a perfectly good ROI file on planting day.

 9. The anomaly flag now scales with the gap between readings. v4 compared to
    the previous ROW regardless of how many days had passed, so one missed
    capture guaranteed a false flag during the fast-growth window.

10. Debug overlay draws circles when circular=True (v4 always drew rectangles,
    which did not show the ROI actually being measured).

-----------------------------------------------------------------------------
Install (Bookworm):
    python3 -m venv --system-site-packages ~/thesis-env
    source ~/thesis-env/bin/activate
    pip install opencv-python-headless numpy pyserial

  --system-site-packages is REQUIRED. Picamera2 is installed system-wide by apt
  and cannot be pip-installed into an isolated venv.

Cron (crontab -e).  flock stops a hung run from overlapping tomorrow's:
    0 12 * * * /usr/bin/flock -n /tmp/gpr.lock /home/USER/thesis-env/bin/python3 \
               /home/USER/thesis/capture_gpr.py >> /home/USER/thesis/cron.log 2>&1

  Check `whoami` -- Bookworm's default user is usually NOT "pi".
  Set the timezone ONCE before D=1 and never change it mid-run:
      sudo timedatectl set-timezone Asia/Manila

Offline testing, no camera and no ESP32 required:
    python3 capture_gpr.py --test-image frame.jpg --no-write --no-sm
    python3 capture_gpr.py --test-image frame.jpg --debug-overlay /tmp/ov.png

CAMERA MODULE 3 -- autofocus MUST be locked. If focus hunts between days, edge
sharpness changes and the green pixel count drifts independently of growth.
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime

import cv2
import numpy as np

BASE = os.path.expanduser("~/thesis")
ROI_FILE = os.path.join(BASE, "pot_rois.json")
OUT_CSV = os.path.join(BASE, "growth_dataset.csv")
OUT_CLEAN_CSV = os.path.join(BASE, "growth_dataset_clean.csv")
SOWING_FILE = os.path.join(BASE, "sowing_date.txt")
FRAME_DIR = os.path.expanduser("~/agrisentry_data/frames")   # daily raw noon frames

# Fallback only. Prefer writing the real date into ~/thesis/sowing_date.txt on
# sowing day so nobody has to edit source on a live rig.
SOWING_DATE_FALLBACK = "2026-08-15"
CYCLE_DAYS = 30          # grow-out shortened to 30 days (harvest on D30)

CAPTURE_SIZE = (1296, 1296)                  # 2x binned from 4608x2592

# ---------------------------------------------------------------------------
# RIG GEOMETRY -- measure these on the finished rig
# ---------------------------------------------------------------------------
# PX_PER_MM: photograph a ruler lying at the POT RIM plane and count.
# At 1650 mm camera height over an 860 mm pot box this comes out near 1.34.
PX_PER_MM = 1.34
POT_PITCH_MM = 330.0        # centre-to-centre. Territory circle diameter.

# ---------------------------------------------------------------------------
# HSV THRESHOLD
# ---------------------------------------------------------------------------
# The manuscript writes the mask as "35 deg <= Hue <= 85 deg". Those NUMBERS
# are correct, but the degree symbols are not: 35 and 85 are OpenCV hue units,
# not degrees. OpenCV stores hue on a 0-179 scale, so 35-85 spans 70-170 deg on
# the true colour wheel, which is exactly where leaf green lives.
#
# VERIFIED on a real outdoor foliage frame: accepted pixels had median hue 67,
# 5th-95th percentile 43-82. Comfortably inside the band.
#
# Do NOT "convert" 35-85 to 18-42 by halving. That returns 0.00 % GPR on a
# healthy green canopy, because it selects orange-yellow instead of green.
# Keep these values in OpenCV units. Fix the manuscript text, not the code.
HUE_LO, HUE_HI = 38, 85
SAT_MIN, VAL_MIN = 100, 55      # Filters out dry soil and shade cloth glare
CLEAN_HUE_LO, CLEAN_HUE_HI = 36, 85
CLEAN_SAT_MIN, CLEAN_VAL_MIN = 100, 55
WEAK_HUE_LO, WEAK_HUE_HI = 34, 88
WEAK_SAT_MIN, WEAK_VAL_MIN = 80, 48
MIN_BLOB_AREA = 12
POT_INNER_R_PX = 68.0
REF_R, REF_G, REF_B = 62.3, 72.3, 60.5

# Opening kernel, in PIXELS but chosen from a PHYSICAL size. A k x k opening
# erases anything thinner than k px. At PX_PER_MM = 1.34, k = 3 erases features
# thinner than 2.2 mm -- below a pechay petiole, above single-pixel noise.
# Raising this deletes real plant. See CHANGES note 2.
MORPH_MM = 2.2               # thinnest real feature we are willing to lose
MORPH_K = max(3, int(round(MORPH_MM * PX_PER_MM)) | 1)   # odd, never below 3
MORPH_KERNEL = np.ones((MORPH_K, MORPH_K), np.uint8)

# GPR jumping more than this PER DAY is implausible and usually means the rig
# moved or the lighting changed. Scaled by the gap between readings so a missed
# capture does not auto-flag the next one. Flagged, not discarded.
ANOMALY_DELTA_PER_DAY = 8.0

CSV_HEADER = ["day", "timestamp", "pot_id", "sm_pct",
              "raw_gpr", "smooth_gpr", "green_px", "total_px", "flag",
              "raw_gpr_noopen", "terr_gpr", "terr_green_px", "terr_total_px",
              "canopy_w_px", "canopy_h_px", "morph_k",
              "cell_gpr", "cell_green_px", "cell_total_px"]

# Pot-area ("cell") GPR, live from run 2 (sown 2026-10-29). Each pot owns the
# pixels closer to its centre than to any other pot's centre, up to CELL_R_PX.
# Cells never overlap, and a plant leaning past its rim stays in its own cell
# (run 1: the pot circle read 0 for leaning P-01/P-05/P-07).
CELL_R_PX = 175          # ~13 cm at 1.34 px/mm; half the closest pot spacing is ~160-180 px


# ---------------------------------------------------------------------------
# DAY INDEX
# ---------------------------------------------------------------------------
def sowing_date():
    """Read the sowing date from a file so nobody edits source on a live rig."""
    if os.path.exists(SOWING_FILE):
        with open(SOWING_FILE) as f:
            txt = f.read().strip()
        if txt:
            return txt
    return SOWING_DATE_FALLBACK


def day_index(allow_any=False):
    """D, with D = 1 the sowing date. Refuses to run outside the cycle.

    D is a term in the regression model. A wrong D is not recoverable after the
    fact, and the CSV looks perfectly well-formed either way -- so fail loudly."""
    sown_txt = sowing_date()
    try:
        sown = datetime.strptime(sown_txt, "%Y-%m-%d").date()
    except ValueError:
        sys.exit(f"[capture_gpr] bad sowing date {sown_txt!r} "
                 f"(want YYYY-MM-DD, from {SOWING_FILE} or the fallback)")
    d = (datetime.now().date() - sown).days + 1
    if not allow_any and not 1 <= d <= CYCLE_DAYS:
        sys.exit(f"[capture_gpr] D={d} is outside the 1..{CYCLE_DAYS} cycle "
                 f"(sowing date {sown_txt}) -- refusing to write.\n"
                 f"  If sowing has happened, put the real date in {SOWING_FILE}.\n"
                 f"  For a deliberate out-of-cycle test, pass --allow-any-day.")
    return d


# ---------------------------------------------------------------------------
# CAPTURE
# ---------------------------------------------------------------------------
# Capture light (relay 12). When USE_CAPTURE_LIGHT is True it is switched on for
# every capture so illumination is identical day to day. OFF since 2026-10-12:
# the light plus camera load was suspected of browning out the Pi, and noon
# daylight is used instead. Flip back to True once the light is proven safe.
USE_CAPTURE_LIGHT = False
# The ESP32 turns it off by itself after LIGHT_PULSE_MS even if this
# script dies; we also switch it off explicitly as soon as the frame is taken.
LIGHT_PULSE_MS = 20000

# Brightness normalisation (since 2026-10-14). One fixed exposure fails across
# weather: 24 ms washed seedlings out on a sunny noon (Oct 13), 6 ms left them too
# dark to pass V >= VAL_MIN on an overcast noon (Oct 14, mean V 13 vs 73). So each
# capture starts at 6 ms and rescales the exposure until the frame's mean V matches
# the calibrated reference frame (Oct 13 12:00, 6 ms, mean V = 73). Gain and white
# balance stay locked, so colour/hue are unchanged -- only brightness is matched.
# The exposure used is logged to exposure_log.csv every day.
AUTO_EXPOSURE = True
TARGET_MEAN_V = 73.0
EXPOSURE_START_US = 6000
EXPOSURE_MIN_US, EXPOSURE_MAX_US = 1000, 100000
LAST_EXPOSURE = {}          # filled by capture_frame(): exposure_us, mean_v, steps
EXPOSURE_LOG = os.path.join(BASE, "exposure_log.csv")

# Light only when it is really dark: if even the longest exposure cannot bring the
# frame within 20 % of the target brightness, the capture light is switched on and
# the brightness is matched again. Light days are marked light_used=1 in
# exposure_log.csv, because lit frames read higher GPR (more saturated green) --
# flag/check those days in the analysis.
AUTO_LIGHT_WHEN_DARK = True
DARK_V = 0.8 * TARGET_MEAN_V
LIGHT_SETTLE_S = 1.5        # let the light reach full, steady output first


def _light(on):
    """Capture light on (as a self-expiring pulse) or off. Returns success."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pi_link                                # lazy: needs pyserial
    ok = pi_link.light_pulse(LIGHT_PULSE_MS) if on else pi_link.set_light_state(False)
    if not ok and on:                             # one retry before giving up
        time.sleep(0.5)
        ok = pi_link.light_pulse(LIGHT_PULSE_MS)
    return ok


def open_locked_camera():
    """Started Picamera2 with the exact configuration and locked controls used
    for every GPR capture. live_feed.py uses this too, so what the alignment
    stream shows is framed, focused and exposed like the real capture.

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
        "LensPosition": 0.42,
        "AeEnable": False,
        "ExposureTime": 6000,       # 6 ms. Sweep 2026-10-13 11:54 (noon daylight, no capture
                                    # light): 24 ms washed seedlings out (57 green px total);
                                    # 4-8 ms all ~1500 px, seedlings only, <1% clipped
        "AnalogueGain": 1.0,         # Minimum gain
        "AwbEnable": False,
        "ColourGains": (1.8, 1.6),
    })
    return cam


def _mean_v(frame):
    small = cv2.resize(frame, (324, 324), interpolation=cv2.INTER_AREA)
    # capture_array() gives RGB here; V (= max channel) is the same either way
    return float(small.max(axis=2).mean())


def _match_brightness(cam, frame):
    """Rescale ExposureTime until mean V is within 5 % of TARGET_MEAN_V."""
    exp = EXPOSURE_START_US
    v = _mean_v(frame)
    steps = []
    for _ in range(5):
        steps.append((exp, round(v, 1)))
        if abs(v - TARGET_MEAN_V) <= 0.05 * TARGET_MEAN_V or v <= 0:
            break
        new = int(min(max(exp * TARGET_MEAN_V / v, EXPOSURE_MIN_US), EXPOSURE_MAX_US))
        if new == exp:
            break
        exp = new
        cam.set_controls({"ExposureTime": exp})
        time.sleep(0.6)
        cam.capture_array()            # flush a frame taken with the old setting
        frame = cam.capture_array()
        v = _mean_v(frame)
    LAST_EXPOSURE.update(exposure_us=exp, mean_v=round(v, 1), steps=steps)  # keeps light_used
    print(f"[capture_gpr] exposure {exp / 1000:.1f} ms -> mean V {v:.1f} "
          f"(target {TARGET_MEAN_V:.0f}; steps {steps})")
    return frame


def capture_frame(use_light=USE_CAPTURE_LIGHT):
    """One stabilised frame from open_locked_camera(), under the capture light.

    Picamera2's format names are inverted -- the default still config hands back
    an array OpenCV can use directly. Verify once with a known-red object: if it
    photographs as blue, drop the cvtColor below."""
    if use_light:
        if _light(True):
            print("[capture_gpr] capture light ON")
            time.sleep(LIGHT_SETTLE_S)
        else:
            print("[capture_gpr] WARNING: capture light did NOT switch on -- this "
                  "frame is lit differently from the others", file=sys.stderr)

    light_on = use_light
    LAST_EXPOSURE["light_used"] = int(bool(use_light))
    try:
        cam = open_locked_camera()
        time.sleep(2)                   # let the locked settings take effect
        frame = cam.capture_array()
        if AUTO_EXPOSURE:
            frame = _match_brightness(cam, frame)
            too_dark = (LAST_EXPOSURE["exposure_us"] >= EXPOSURE_MAX_US
                        and LAST_EXPOSURE["mean_v"] < DARK_V)
            if too_dark and AUTO_LIGHT_WHEN_DARK and not light_on:
                print(f"[capture_gpr] too dark even at {EXPOSURE_MAX_US / 1000:.0f} ms "
                      f"(mean V {LAST_EXPOSURE['mean_v']}) -- switching the capture light on")
                if _light(True):
                    light_on = True
                    LAST_EXPOSURE["light_used"] = 1
                    time.sleep(LIGHT_SETTLE_S)
                    cam.set_controls({"ExposureTime": EXPOSURE_START_US})
                    time.sleep(0.6)
                    cam.capture_array()
                    frame = _match_brightness(cam, cam.capture_array())
                else:
                    print("[capture_gpr] WARNING: capture light did NOT switch on",
                          file=sys.stderr)
        cam.stop()
        cam.close()
    finally:
        if light_on:
            _light(False)
            print("[capture_gpr] capture light OFF")
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# MASKS
# ---------------------------------------------------------------------------
def circle_mask(shape_hw, cx, cy, r):
    m = np.zeros(shape_hw, np.uint8)
    cv2.circle(m, (int(cx), int(cy)), int(r), 255, -1)
    return m


def roi_geometry(roi):
    """Centre and radius of one pot ROI, in pixels."""
    cx = roi["x"] + roi["w"] / 2.0
    cy = roi["y"] + roi["h"] / 2.0
    r = min(roi["w"], roi["h"]) / 2.0
    return cx, cy, r


def roi_mask(shape_hw, roi, circular):
    """Pixels belonging to this pot.

    A square ROI drawn around a circular pot puts ~21.5 % bench and rim inside
    the denominator, so 'GPR' stops being the fraction of POT area covered and
    becomes the fraction of a rectangle. Circular is the truer denominator and
    is the default; set "circular": false in pot_rois.json to fall back."""
    if circular:
        cx, cy, r = roi_geometry(roi)
        return circle_mask(shape_hw, cx, cy, r)
    m = np.zeros(shape_hw, np.uint8)
    m[roi["y"]:roi["y"] + roi["h"], roi["x"]:roi["x"] + roi["w"]] = 255
    return m


def sunny_wb_bgr(frame):
    """Normalize BGR frame to sunny-day neutral reference on mid-tone pixels."""
    f = frame.astype(np.float32)
    lum = f.mean(axis=2)
    valid = (lum > 15) & (lum < 235)
    if np.count_nonzero(valid) < 1000:
        valid = np.ones(frame.shape[:2], dtype=bool)
    bm = float(f[..., 0][valid].mean())
    gm = float(f[..., 1][valid].mean())
    rm = float(f[..., 2][valid].mean())
    out = np.empty_like(f)
    out[..., 0] = f[..., 0] * (REF_B / max(bm, 1.0))
    out[..., 1] = f[..., 1] * (REF_G / max(gm, 1.0))
    out[..., 2] = f[..., 2] * (REF_R / max(rm, 1.0))
    return np.clip(out, 0, 255).astype(np.uint8)


def hsv_mask(hsv):
    """Raw HSV threshold, no morphology."""
    return cv2.inRange(hsv,
                       np.array([HUE_LO, SAT_MIN, VAL_MIN], np.uint8),
                       np.array([HUE_HI, 255, 255], np.uint8))


def green_mask(hsv):
    """Original validated threshold + 3x3 opening for the whole frame."""
    return cv2.morphologyEx(hsv_mask(hsv), cv2.MORPH_OPEN, MORPH_KERNEL)


def clean_green_mask(frame, rois):
    """Sunny-reference WB + 3x3 opening + pot-anchored blob filter + 1-px edge recovery.

    Returns (clean_final_uint8, clean_raw_inner_uint8) without modifying frame."""
    wb = sunny_wb_bgr(frame)
    hsv = cv2.cvtColor(wb, cv2.COLOR_BGR2HSV)
    raw_hsv = cv2.inRange(hsv,
                          np.array([CLEAN_HUE_LO, CLEAN_SAT_MIN, CLEAN_VAL_MIN], np.uint8),
                          np.array([CLEAN_HUE_HI, 255, 255], np.uint8))
    core = cv2.morphologyEx(raw_hsv, cv2.MORPH_OPEN, MORPH_KERNEL)
    h, w = hsv.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    inner = np.zeros((h, w), dtype=bool)
    for r in rois.values():
        cx, cy, _ = roi_geometry(r)
        inner |= ((xx - cx) ** 2 + (yy - cy) ** 2) <= (POT_INNER_R_PX ** 2)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(core, connectivity=8)
    clean_core = np.zeros((h, w), dtype=np.uint8)
    for idx in range(1, n):
        if stats[idx, cv2.CC_STAT_AREA] >= MIN_BLOB_AREA:
            comp = (labels == idx)
            if np.any(comp & inner):
                clean_core[comp] = 255
    weak = cv2.inRange(hsv,
                       np.array([WEAK_HUE_LO, WEAK_SAT_MIN, WEAK_VAL_MIN], np.uint8),
                       np.array([WEAK_HUE_HI, 255, 255], np.uint8))
    dil = cv2.dilate(clean_core, MORPH_KERNEL)
    final = ((clean_core > 0) | ((dil > 0) & (weak > 0))) & inner
    inner_raw = (raw_hsv > 0) & inner
    return (final.astype(np.uint8) * 255), (inner_raw.astype(np.uint8) * 255)


def cell_masks(shape_hw, rois, r_px=CELL_R_PX):
    """{pot_id: uint8 mask} -- each pot's Voronoi cell, capped at r_px.

    Running min over the 9 centres in float32, so it stays small on the Zero 2W
    (a full 9-layer distance stack would be ~120 MB)."""
    h, w = shape_hw
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    best = np.full((h, w), np.inf, np.float32)
    owner = np.full((h, w), -1, np.int8)
    ids = sorted(rois)
    for i, pid in enumerate(ids):
        cx, cy, _ = roi_geometry(rois[pid])
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        closer = d2 < best
        best[closer] = d2[closer]
        owner[closer] = i
    owner[best > r_px * r_px] = -1
    return {pid: ((owner == i).astype(np.uint8) * 255) for i, pid in enumerate(ids)}


def masked_count(mask, area):
    return int(np.count_nonzero(cv2.bitwise_and(mask, mask, mask=area)))


def canopy_bbox(mask, area):
    """Bounding box of the largest green blob inside `area`, in pixels.

    Keeps growing after GPR saturates, so it survives the ceiling effect."""
    sub = cv2.bitwise_and(mask, mask, mask=area)
    n, _, stats, _ = cv2.connectedComponentsWithStats(sub, connectivity=8)
    if n <= 1:
        return 0, 0
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT])


# ---------------------------------------------------------------------------
# HISTORY
# ---------------------------------------------------------------------------
def previous_gpr_all(csv_path=OUT_CSV):
    """{pot_id: (day, raw_gpr)} for the most recent row of each pot."""
    if not os.path.exists(csv_path):
        return {}
    out = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[row["pot_id"]] = (int(row["day"]), float(row["raw_gpr"]))
            except (KeyError, ValueError, TypeError):
                continue
    return out


def already_written(d):
    """True if day d is already in the CSV.

    Without this, a second run in one day silently appends 9 more rows. The
    duplicate plant-days then over-weight that day in every LOOCV fold they
    appear in, inflating R² and shrinking MAE -- and the CSV looks fine."""
    if not os.path.exists(OUT_CSV):
        return False
    with open(OUT_CSV, newline="") as f:
        return any(r.get("day") == str(d) for r in csv.DictReader(f))


# ---------------------------------------------------------------------------
# CAMERA ALIGNMENT (added D10, 2026-11-07)
# ---------------------------------------------------------------------------
# The camera mount moved by up to ~150 px within hours on D10. pot_rois.json was
# fitted on ALIGN_REF; each new frame is matched to that reference photo (phase
# correlation on edges, so a change in light or shade does not count as movement)
# and the pot circles are shifted by the camera's movement before anything is
# measured. Same circles, same sizes, same mask: only their position follows the
# camera. Every shift is written to align_log.csv. A weak or implausible match is
# not applied (the circles stay where pot_rois.json puts them) and is logged.
ALIGN_REF = os.path.join(BASE, "align_ref.png")
ALIGN_LOG = os.path.join(BASE, "align_log.csv")
ALIGN_MIN_CONF = 0.12      # phase-correlation peak; real matches here were 0.35-0.45
ALIGN_MAX_PX = 250         # beyond this the pots would be leaving the frame


def _align_edges(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 3)
    return cv2.Laplacian(g, cv2.CV_32F, ksize=3)


def camera_shift(frame, ref_path=ALIGN_REF):
    """(dx, dy, confidence) of this frame against the ROI reference photo, or None."""
    if not os.path.exists(ref_path):
        return None
    ref = cv2.imread(ref_path)
    if ref is None or ref.shape != frame.shape:
        return None
    win = cv2.createHanningWindow((frame.shape[1], frame.shape[0]), cv2.CV_32F)
    (dx, dy), conf = cv2.phaseCorrelate(_align_edges(ref), _align_edges(frame), win)
    return float(dx), float(dy), float(conf)


def shift_rois(rois, dx, dy):
    out = {}
    for pid, r in rois.items():
        r2 = dict(r)
        r2["x"] = int(round(r["x"] + dx))
        r2["y"] = int(round(r["y"] + dy))
        out[pid] = r2
    return out


def aligned_rois(frame, rois, day="", stamp="", source="capture", log=True):
    """ROIs moved with the camera. Returns (rois, dx, dy, conf, applied)."""
    s = camera_shift(frame)
    if s is None:
        return rois, 0.0, 0.0, 0.0, False
    dx, dy, conf = s
    applied = conf >= ALIGN_MIN_CONF and (dx * dx + dy * dy) ** 0.5 <= ALIGN_MAX_PX
    if log:
        new = not os.path.exists(ALIGN_LOG)
        with open(ALIGN_LOG, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["day", "timestamp", "source", "dx_px", "dy_px", "confidence",
                            "applied"])
            w.writerow([day, stamp or datetime.now().strftime("%Y-%m-%d %H:%M"), source,
                        f"{dx:.1f}", f"{dy:.1f}", f"{conf:.2f}", int(applied)])
    print(f"[capture_gpr] camera shift vs reference: {dx:+.1f}, {dy:+.1f} px "
          f"(confidence {conf:.2f}) -> {'circles moved' if applied else 'NOT applied'}")
    return (shift_rois(rois, dx, dy) if applied else rois), dx, dy, conf, applied


# ---------------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------------
def validate_rois(rois, shape_hw, circular):
    """Refuse to run on ROIs that fall outside the frame or genuinely overlap.

    Cheap insurance: a bad pot_rois.json silently produces plausible-looking
    numbers for 35 days, and there is no way to recover the run afterwards."""
    h, w = shape_hw
    problems = []
    present = {}
    for pid in [f"P-0{i}" for i in range(1, 10)]:
        r = rois.get(pid)
        if r is None:
            problems.append(f"{pid}: missing from pot_rois.json")
            continue
        if r["w"] <= 0 or r["h"] <= 0:
            problems.append(f"{pid}: non-positive size {r['w']}x{r['h']}")
            continue
        if r["x"] < 0 or r["y"] < 0 or r["x"] + r["w"] > w or r["y"] + r["h"] > h:
            problems.append(f"{pid}: box {r['x']},{r['y']} {r['w']}x{r['h']} "
                            f"falls outside the {w}x{h} frame")
        present[pid] = r

    ids = list(present)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = present[ids[i]], present[ids[j]]
            if circular:
                # circle-distance: two boxes can overlap while the inscribed
                # circles do not, and refusing that would be a false alarm
                ax, ay, ar = roi_geometry(a)
                bx, by, br = roi_geometry(b)
                if math_hypot(ax - bx, ay - by) < ar + br:
                    problems.append(f"{ids[i]} and {ids[j]} circles overlap")
            elif (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and
                  a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]):
                problems.append(f"{ids[i]} and {ids[j]} overlap")
    return problems


def math_hypot(dx, dy):
    return (dx * dx + dy * dy) ** 0.5


def _measure_pot_row(d, stamp, pot_id, sm_str, area, total, t_area, t_total,
                     c_mask, c_total, mask_all, mask_raw, prev):
    """Compute one CSV row for a pot given its masks and previous baseline."""
    g = masked_count(mask_all, area)
    g_raw = masked_count(mask_raw, area)
    gpr = g / total * 100.0 if total else 0.0
    gpr_raw = g_raw / total * 100.0 if total else 0.0
    cw, ch = canopy_bbox(mask_all, area)
    t_green = masked_count(mask_all, t_area)
    t_gpr = t_green / t_total * 100.0 if t_total else 0.0
    c_green = masked_count(mask_all, c_mask)
    c_gpr = c_green / c_total * 100.0 if c_total else 0.0

    flag = 0
    if pot_id in prev:
        pday, pgpr = prev[pot_id]
        gap = max(1, d - pday)
        if abs(gpr - pgpr) > ANOMALY_DELTA_PER_DAY * gap:
            flag = 1

    row = [d, stamp, pot_id, sm_str, f"{gpr:.2f}", "",
           g, total, flag,
           f"{gpr_raw:.2f}", f"{t_gpr:.2f}", t_green, t_total,
           cw, ch, MORPH_K,
           f"{c_gpr:.2f}", c_green, c_total]
    return row, (gpr, gpr_raw, t_gpr, c_gpr, g, cw, ch, flag)


def _save_overlay(frame, mask, cells, rois, out_path):
    """Draw magenta green mask and yellow cell contours to a JPEG."""
    ov = frame.copy()
    ov[mask > 0] = (255, 0, 255)
    for pid, m in cells.items():
        cnt, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(ov, cnt, -1, (0, 255, 255), 2)
        cx, cy, _ = roi_geometry(rois[pid])
        cv2.putText(ov, pid, (int(cx) - 30, int(cy) - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, ov, [cv2.IMWRITE_JPEG_QUALITY, 85])


def _append_csv_rows(csv_path, rows):
    new_file = not os.path.exists(csv_path)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(CSV_HEADER)
        w.writerows(rows)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Daily noon GPR capture")
    ap.add_argument("--test-image", help="use this image instead of the camera")
    ap.add_argument("--no-write", action="store_true", help="do not touch the CSV")
    ap.add_argument("--no-sm", action="store_true", help="skip the ESP32 read")
    ap.add_argument("--no-light", action="store_true",
                    help="force the capture light OFF for this run")
    ap.add_argument("--light", action="store_true",
                    help="force the capture light ON for this run")
    ap.add_argument("--debug-overlay", help="write an annotated PNG here")
    ap.add_argument("--roi-file", default=ROI_FILE)
    ap.add_argument("--allow-any-day", action="store_true",
                    help=f"permit D outside 1..{CYCLE_DAYS} (testing only)")
    ap.add_argument("--no-align", action="store_true",
                    help="do not move the pot circles with the camera (see CAMERA ALIGNMENT)")
    ap.add_argument("--force", action="store_true",
                    help="write even if this day is already in the CSV "
                         "(you almost never want this)")
    args = ap.parse_args()

    with open(args.roi_file) as f:
        cfg = json.load(f)
    rois = cfg.get("rois", cfg)                    # tolerate the flat v3 layout
    circular = bool(cfg.get("circular", True))

    d = day_index(args.allow_any_day)

    # No RTC on the Pi: after a reboot without internet the clock resumes from
    # the last hourly save and can be behind. Say so in cron.log, so a wrong D or
    # timestamp can be traced later.
    try:
        synced = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
        if synced == "no":
            print(f"[capture_gpr] WARNING: system clock not internet-synced since boot "
                  f"(now {datetime.now():%Y-%m-%d %H:%M}, D={d}); time/D may be off",
                  file=sys.stderr)
    except (OSError, subprocess.SubprocessError):
        pass

    # refuse BEFORE doing the expensive work, unless we are not writing anyway
    if not args.no_write and not args.force and already_written(d):
        sys.exit(f"[capture_gpr] day {d} is already in {OUT_CSV} -- refusing to "
                 f"duplicate.\n  Duplicated plant-days corrupt the LOOCV result. "
                 f"If today's rows are genuinely bad, delete them by hand and "
                 f"re-run, or pass --force deliberately.")

    if args.test_image:
        frame = cv2.imread(args.test_image)
        if frame is None:
            sys.exit(f"could not read {args.test_image}")
        print(f"[capture_gpr] TEST MODE on {args.test_image} "
              f"{frame.shape[1]}x{frame.shape[0]}")
    else:
        use_light = (USE_CAPTURE_LIGHT or args.light) and not args.no_light
        frame = capture_frame(use_light=use_light)

    if not args.no_align:
        rois, _, _, aconf, applied = aligned_rois(
            frame, rois, day=d,
            source="test_image" if args.test_image else
            ("no_write" if args.no_write else "noon_capture"),
            log=not args.no_write)
        # Never write a day on circles that may not sit on the pots: if the match
        # with the reference photo is too weak, leave it to the next 10-min retry.
        # The last retry (12:50 or later) writes anyway; align_log.csv shows applied=0.
        if (not applied and os.path.exists(ALIGN_REF) and not args.no_write
                and not args.test_image and not args.force and datetime.now().minute < 50):
            sys.exit(f"[capture_gpr] camera alignment too weak (confidence {aconf:.2f}) -- "
                     f"day {d} not written; the next retry will try again")

    # Colour-cast guard (fixkit, Nov 2026). Overcast light under the locked daylight
    # white balance turns the frame blue; leaf pixels then fall under SAT_MIN and
    # GPR reads low (D19: blue/red 1.84, GPR about half). Leave such a frame to the
    # next 10-min retry. The last retry (12:50) writes anyway; the value is printed
    # to cron.log either way.
    _med = np.median(frame.reshape(-1, 3), axis=0)
    _cast = float(_med[0]) / max(float(_med[2]), 1.0)
    print(f"[capture_gpr] colour cast blue/red = {_cast:.2f} (normal about 1.0)")
    if (_cast > 1.25 and not args.no_write and not args.test_image
            and not args.force and datetime.now().minute < 50):
        sys.exit(f"[capture_gpr] blue colour cast {_cast:.2f} -- day {d} not written; "
                 f"the next retry will try again")

    problems = validate_rois(rois, frame.shape[:2], circular)
    if problems:
        for p in problems:
            print(f"[capture_gpr] ROI ERROR: {p}", file=sys.stderr)
        sys.exit("refusing to run on invalid ROIs -- fix pot_rois.json "
                 "(see make_rois.py)")

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green_all = green_mask(hsv)          # original baseline, computed once
    green_raw = hsv_mask(hsv)            # diagnostic: same thing, no opening
    clean_all, clean_raw = clean_green_mask(frame, rois)

    # --- soil moisture, via the daemon so the serial port has one owner ---
    sm_values = None
    if not args.no_sm:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from pi_link import get_sm_snapshot        # lazy: needs pyserial
        sm_values = get_sm_snapshot()
    if sm_values is None or len(sm_values) != 9:
        if sm_values is not None:
            print(f"[capture_gpr] SM snapshot had {len(sm_values)} values, "
                  "expected 9 -- writing NaN", file=sys.stderr)
        sm_values = [None] * 9

    prev = previous_gpr_all(OUT_CSV)
    prev_clean = previous_gpr_all(OUT_CLEAN_CSV)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    overlay = frame.copy() if args.debug_overlay else None
    terr_r_px = (POT_PITCH_MM * PX_PER_MM) / 2.0
    cells = cell_masks(frame.shape[:2], rois)
    rows = []
    clean_rows = []

    print(f"[capture_gpr] D={d}  kernel {MORPH_K}x{MORPH_K} "
          f"({MORPH_K / PX_PER_MM:.1f} mm)  territory r={terr_r_px:.0f} px")

    for i in range(9):
        pot_id = f"P-0{i + 1}"
        roi = rois[pot_id]
        cx, cy, r = roi_geometry(roi)

        area = roi_mask(frame.shape[:2], roi, circular)
        total = int(np.count_nonzero(area))
        t_area = circle_mask(frame.shape[:2], cx, cy, terr_r_px)
        t_total = int(np.count_nonzero(t_area))
        c_total = int(np.count_nonzero(cells[pot_id]))

        sm = sm_values[i]
        sm_str = "NaN" if sm is None else f"{sm:.1f}"

        # smooth_gpr is intentionally blank. The 3-day centred moving average
        # needs days either side of each point, so it is computed offline after
        # harvest, not here (Appendix G closing note).
        row, (gpr, gpr_raw, t_gpr, c_gpr, g, cw, ch, flag) = _measure_pot_row(
            d, stamp, pot_id, sm_str, area, total, t_area, t_total,
            cells[pot_id], c_total, green_all, green_raw, prev)
        clean_row, (_, _, _, cc_gpr, cg_px, _, _, _) = _measure_pot_row(
            d, stamp, pot_id, sm_str, area, total, t_area, t_total,
            cells[pot_id], c_total, clean_all, clean_raw, prev_clean)
        rows.append(row)
        clean_rows.append(clean_row)

        print(f"{pot_id}  SM={sm_str:>6}  cell={c_gpr:6.2f}% (clean={cc_gpr:5.2f}%)  "
              f"GPR={gpr:6.2f}%  (noopen {gpr_raw:5.2f}%, terr {t_gpr:5.2f}%)  "
              f"({g}/{total} px)  bbox {cw}x{ch}  flag={flag}")

        if overlay is not None:
            sub = cv2.bitwise_and(green_all, green_all, mask=area)
            overlay[sub > 0] = (0, 0, 255)
            cv2.circle(overlay, (int(cx), int(cy)), int(terr_r_px), (120, 120, 120), 1)
            if circular:
                cv2.circle(overlay, (int(cx), int(cy)), int(r), (255, 255, 0), 2)
            else:
                cv2.rectangle(overlay, (roi["x"], roi["y"]),
                              (roi["x"] + roi["w"], roi["y"] + roi["h"]),
                              (255, 255, 0), 2)
            cv2.putText(overlay, f"{pot_id} {gpr:.1f}%",
                        (int(cx - r), int(cy - r) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    if overlay is not None:
        cv2.imwrite(args.debug_overlay, overlay)
        print(f"[capture_gpr] overlay -> {args.debug_overlay}")

    if args.no_write:
        print("[capture_gpr] --no-write: CSV untouched")
        return

    _append_csv_rows(OUT_CSV, rows)
    print(f"[capture_gpr] day {d} written to {OUT_CSV}")
    try:
        _append_csv_rows(OUT_CLEAN_CSV, clean_rows)
        print(f"[capture_gpr] day {d} written to {OUT_CLEAN_CSV}")
    except Exception as e:
        print(f"[capture_gpr] WARNING: clean CSV not saved ({e})", file=sys.stderr)

    # Keep the raw frame (lossless, so HSV is unchanged) for recomputation. The
    # rows are already written; a failed save must not cost the day.
    if not args.test_image:
        try:
            os.makedirs(FRAME_DIR, exist_ok=True)
            fp = os.path.join(FRAME_DIR, f"D{d:02d}_{datetime.now():%Y-%m-%d_%H%M}.png")
            if cv2.imwrite(fp, frame):
                print(f"[capture_gpr] frame -> {fp}")
            else:
                print(f"[capture_gpr] WARNING: could not save frame to {fp}", file=sys.stderr)
        except OSError as e:
            print(f"[capture_gpr] WARNING: frame not saved ({e})", file=sys.stderr)
        try:      # daily check picture: magenta = counted green, yellow = each pot's cell
            _save_overlay(frame, green_all, cells, rois,
                          os.path.join(FRAME_DIR, "overlay", f"D{d:02d}_overlay.jpg"))
        except Exception as e:      # never cost the day for a check picture
            print(f"[capture_gpr] WARNING: overlay not saved ({e})", file=sys.stderr)
        try:
            _save_overlay(frame, clean_all, cells, rois,
                          os.path.join(FRAME_DIR, "overlay_clean", f"D{d:02d}_overlay.jpg"))
        except Exception as e:
            print(f"[capture_gpr] WARNING: clean overlay not saved ({e})", file=sys.stderr)
    if LAST_EXPOSURE:
        new_log = not os.path.exists(EXPOSURE_LOG)
        with open(EXPOSURE_LOG, "a", newline="") as f:
            w = csv.writer(f)
            if new_log:
                w.writerow(["day", "timestamp", "exposure_us", "mean_v", "target_v",
                            "light_used"])
            w.writerow([d, stamp, LAST_EXPOSURE["exposure_us"], LAST_EXPOSURE["mean_v"],
                        TARGET_MEAN_V, LAST_EXPOSURE.get("light_used", 0)])


if __name__ == "__main__":
    main()
