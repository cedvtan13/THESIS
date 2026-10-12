#!/usr/bin/env python3
"""
capture_gpr.py -- daily noon vision pipeline on the Raspberry Pi Zero 2W.  v5

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Implements Appendix G. One frame at 12:00, HSV threshold inside each pot's ROI,
Green Pixel Ratio per pot, appended to growth_dataset.csv together with the soil
moisture pulled from the ESP32-S3. The raw frame is discarded afterwards to
enforce storage autonomy.

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
SOWING_FILE = os.path.join(BASE, "sowing_date.txt")

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
              "canopy_w_px", "canopy_h_px", "morph_k"]


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
        "ExposureTime": 24000,      # 24 ms
        "AnalogueGain": 1.0,         # Minimum gain
        "AwbEnable": False,
        "ColourGains": (1.8, 1.6),
    })
    return cam


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

    try:
        cam = open_locked_camera()
        time.sleep(2)                   # let the locked settings take effect
        frame = cam.capture_array()
        cam.stop()
        cam.close()
    finally:
        if use_light:
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


def hsv_mask(hsv):
    """Raw HSV threshold, no morphology."""
    return cv2.inRange(hsv,
                       np.array([HUE_LO, SAT_MIN, VAL_MIN], np.uint8),
                       np.array([HUE_HI, 255, 255], np.uint8))


def green_mask(hsv):
    """Threshold + opening for the WHOLE frame, computed once.

    Hoisted out of the per-pot loop: on a Zero 2W the opening is the single most
    expensive step, and running it nine times over the full 2304x1296 frame was
    ~9x more work than needed. Opening the whole frame is also slightly more
    correct -- per-ROI opening would treat each ROI edge as a boundary."""
    return cv2.morphologyEx(hsv_mask(hsv), cv2.MORPH_OPEN, MORPH_KERNEL)


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
def previous_gpr_all():
    """{pot_id: (day, raw_gpr)} for the most recent row of each pot."""
    if not os.path.exists(OUT_CSV):
        return {}
    out = {}
    with open(OUT_CSV, newline="") as f:
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
    ap.add_argument("--force", action="store_true",
                    help="write even if this day is already in the CSV "
                         "(you almost never want this)")
    args = ap.parse_args()

    with open(args.roi_file) as f:
        cfg = json.load(f)
    rois = cfg.get("rois", cfg)                    # tolerate the flat v3 layout
    circular = bool(cfg.get("circular", True))

    if args.test_image:
        frame = cv2.imread(args.test_image)
        if frame is None:
            sys.exit(f"could not read {args.test_image}")
        print(f"[capture_gpr] TEST MODE on {args.test_image} "
              f"{frame.shape[1]}x{frame.shape[0]}")
    else:
        use_light = (USE_CAPTURE_LIGHT or args.light) and not args.no_light
        frame = capture_frame(use_light=use_light)

    problems = validate_rois(rois, frame.shape[:2], circular)
    if problems:
        for p in problems:
            print(f"[capture_gpr] ROI ERROR: {p}", file=sys.stderr)
        sys.exit("refusing to run on invalid ROIs -- fix pot_rois.json "
                 "(see make_rois.py)")

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

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green_all = green_mask(hsv)          # computed once, not nine times
    green_raw = hsv_mask(hsv)            # diagnostic: same thing, no opening

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

    prev = previous_gpr_all()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    overlay = frame.copy() if args.debug_overlay else None
    terr_r_px = (POT_PITCH_MM * PX_PER_MM) / 2.0
    rows = []

    print(f"[capture_gpr] D={d}  kernel {MORPH_K}x{MORPH_K} "
          f"({MORPH_K / PX_PER_MM:.1f} mm)  territory r={terr_r_px:.0f} px")

    for i in range(9):
        pot_id = f"P-0{i + 1}"
        roi = rois[pot_id]
        cx, cy, r = roi_geometry(roi)

        area = roi_mask(frame.shape[:2], roi, circular)
        total = int(np.count_nonzero(area))
        g = masked_count(green_all, area)
        g_raw = masked_count(green_raw, area)
        gpr = g / total * 100.0 if total else 0.0
        gpr_raw = g_raw / total * 100.0 if total else 0.0
        cw, ch = canopy_bbox(green_all, area)

        # territory: the pot's Voronoi cell. Does not saturate when the canopy
        # outgrows the rim, which happens around D=24-28.
        t_area = circle_mask(frame.shape[:2], cx, cy, terr_r_px)
        t_total = int(np.count_nonzero(t_area))
        t_green = masked_count(green_all, t_area)
        t_gpr = t_green / t_total * 100.0 if t_total else 0.0

        # anomaly flag, scaled by the gap since this pot was last recorded
        flag = 0
        if pot_id in prev:
            pday, pgpr = prev[pot_id]
            gap = max(1, d - pday)
            if abs(gpr - pgpr) > ANOMALY_DELTA_PER_DAY * gap:
                flag = 1

        sm = sm_values[i]
        sm_str = "NaN" if sm is None else f"{sm:.1f}"

        # smooth_gpr is intentionally blank. The 3-day centred moving average
        # needs days either side of each point, so it is computed offline after
        # harvest, not here (Appendix G closing note).
        rows.append([d, stamp, pot_id, sm_str, f"{gpr:.2f}", "",
                     g, total, flag,
                     f"{gpr_raw:.2f}", f"{t_gpr:.2f}", t_green, t_total,
                     cw, ch, MORPH_K])

        print(f"{pot_id}  SM={sm_str:>6}  GPR={gpr:6.2f}%  "
              f"(noopen {gpr_raw:5.2f}%, terr {t_gpr:5.2f}%)  "
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
