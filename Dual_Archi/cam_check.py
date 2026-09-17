#!/usr/bin/env python3
"""
cam_check.py -- camera acceptance test for the GPR pipeline. Group B thesis rig.

This is NOT a live view. cam_stream.py already shows you a picture. This asks a
different question: is the picture GOOD ENOUGH TO MEASURE FROM?

A stream that looks fine to your eye can still be:
  * hunting focus between days      -> edge sharpness drifts -> GPR drifts
  * auto-exposing                   -> HSV values move when the weather does
  * cropped to a smaller sensor mode-> narrower FOV than capture_gpr.py assumes
  * framed so a pot ROI falls off   -> that pot silently reads 0 for 35 days
None of those show up as "the camera is broken". All of them corrupt the data.

RUN IN THIS ORDER
  1. python3 cam_check.py --info          is the camera there, what modes exist
  2. python3 cam_check.py --capture       one still + quality numbers
  3. python3 cam_check.py --focus-sweep   find the LensPosition to lock
  4. python3 cam_check.py --rois          are all nine pots inside the frame
  5. python3 cam_check.py --check         full pass/fail, run before D=1

WHERE THE IMAGES GO
  Default: a camcheck/ folder NEXT TO THIS SCRIPT. Run it from
  ~/THESIS/Dual_Archi and they land in ~/THESIS/Dual_Archi/camcheck.
  Every run prints the destination as its first line. Change it with:

      python3 cam_check.py --check --out-dir ~/Pictures/day0
      python3 cam_check.py --check --out-dir /media/usb/camcheck
      export CAMCHECK_OUT=~/Pictures/camcheck        # for this shell session

  Every run OVERWRITES the same filenames (capture.jpg, check_1.jpg, ...), so
  use a per-session --out-dir if you want to compare two mounting heights or
  two days side by side. Nothing here is ever deleted -- it just gets replaced.

Look at the images. The numbers narrow down where to look; your eyes make the
call.
"""

import argparse
import json
import os
import sys
import time

# WHERE THINGS GO
# ---------------
# Output lands in camcheck/ NEXT TO THIS SCRIPT, wherever you put the script.
# Copy cam_check.py into ~/THESIS/Dual_Archi and the images appear in
# ~/THESIS/Dual_Archi/camcheck -- not in some other directory you have to
# remember. "Beside the script" is the least surprising default there is.
#
# Note this is deliberately NOT ~/thesis. capture_gpr.py uses ~/thesis as its
# runtime data directory, and on this Pi ~/thesis and ~/THESIS are two
# different folders (Linux is case-sensitive). Diagnostic images are not
# runtime data, so they do not belong in the same place.
#
# Override, in increasing priority:
#   env CAMCHECK_OUT   / --out-dir DIR
#   env CAMCHECK_ROIS  / --roi-file FILE
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

OUT_DIR = os.path.expanduser(os.environ.get("CAMCHECK_OUT",
                                            os.path.join(SCRIPT_DIR, "camcheck")))


def _find_rois():
    """pot_rois.json beside the script wins; fall back to capture_gpr.py's
    ~/thesis so this still works if you run the script from elsewhere."""
    env = os.environ.get("CAMCHECK_ROIS")
    if env:
        return os.path.expanduser(env)
    here = os.path.join(SCRIPT_DIR, "pot_rois.json")
    if os.path.exists(here):
        return here
    return os.path.expanduser("~/thesis/pot_rois.json")


ROI_FILE = _find_rois()

# Must match capture_gpr.py EXACTLY, or this test proves nothing about it.
HUE_LO, HUE_HI   = 35, 85          # OpenCV hue units (0-179), NOT degrees
SAT_MIN, VAL_MIN = 40, 40
CAPTURE_SIZE     = (1296, 1296)    # 2x2 binned from 4608x2592

# Camera height above the CANOPY plane, not the floor. LensPosition is in
# dioptres = 1 / (distance in metres). Override with --distance.
DEFAULT_SUBJECT_M = 1.22           # 1650 mm camera - 430 mm canopy top

try:
    import cv2
    import numpy as np
except ImportError:
    sys.exit("opencv missing:  sudo apt install python3-opencv")


def need_picamera2():
    try:
        from picamera2 import Picamera2
        return Picamera2
    except ImportError:
        sys.exit("picamera2 missing. It is installed system-wide by apt:\n"
                 "  sudo apt install python3-picamera2\n"
                 "If you are in a venv it must have been made with "
                 "--system-site-packages.")


def ensure_out():
    """Create the output directory, and fail with a readable message rather
    than a traceback if the path is not writable (a USB stick that is mounted
    read-only, or a folder owned by root, are the usual causes)."""
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
    except OSError as e:
        sys.exit(f"cannot create {OUT_DIR}: {e}\n"
                 f"  pick another with  --out-dir /some/writable/path")
    if not os.access(OUT_DIR, os.W_OK):
        sys.exit(f"{OUT_DIR} is not writable.\n"
                 f"  pick another with  --out-dir /some/writable/path")


# --------------------------------------------------------------------- 1 ---
def cmd_info():
    Picamera2 = need_picamera2()
    cams = Picamera2.global_camera_info()
    if not cams:
        print("NO CAMERA DETECTED.\n"
              "  * check the CSI ribbon at BOTH ends -- contacts face the board\n"
              "  * a Pi Zero 2W needs the narrow-to-standard adapter cable\n"
              "  * libcamera-hello --list-cameras should agree with this")
        return False

    for i, c in enumerate(cams):
        print(f"camera {i}: {c.get('Model','?')}   {c.get('Location','')}")
        print(f"           id: {c.get('Id','?')}")

    model = cams[0].get("Model", "").lower()
    if "imx708" in model:
        print("\n  imx708 = Camera Module 3. HFOV 66 deg, VFOV 41 deg, autofocus.")
        print("  NOTE: your manuscript Section III.B still names the Module V2")
        print("  (VFOV 48.8 deg). Different geometry, different mounting height.")
    elif "imx219" in model:
        print("\n  imx219 = Camera Module V2. No autofocus, VFOV 48.8 deg.")
        print("  If you expected a v3, you have the wrong camera on the rig.")

    picam2 = Picamera2()
    print("\nsensor modes available:")
    for m in picam2.sensor_modes:
        print(f"  {m['size'][0]}x{m['size'][1]}  bit_depth={m.get('bit_depth')}  "
              f"crop_limits={m.get('crop_limits')}")
    print(f"\ncapture_gpr.py asks for {CAPTURE_SIZE[0]}x{CAPTURE_SIZE[1]}.")
    print("If no mode matches that, libcamera will crop or scale -- and a CROP")
    print("means a narrower field of view than your height calculation assumed.")
    picam2.close()
    return True


# --------------------------------------------------------------- helpers ---
# The literal values hardcoded in capture_gpr.py's capture_frame(). Every one
# is marked "MEASURE ONCE" in that file and none has been measured yet. Keep
# these in sync by hand -- --as-gpr is only honest if they match.
GPR_CONTROLS = {
    "LensPosition":  2.5,          # = 40 cm. Almost certainly wrong for the rig.
    "ExposureTime":  8000,         # microseconds = 1/125 s
    "AnalogueGain":  1.0,
    "ColourGains":   (1.8, 1.6),
}


def open_camera(lock=True, lens_position=None, distance_m=DEFAULT_SUBJECT_M,
                exposure_us=None, gain=None, as_gpr=False):
    """Open the camera the way capture_gpr.py does.

    Three lock behaviours, and the difference between them matters:

      lock=False      everything automatic. What your eye would call "correct".
      lock=True       let AE/AWB converge for 2 s, THEN freeze whatever they
                      chose. Stable, and adapted to the light in the room.
      as_gpr=True     force capture_gpr.py's hardcoded ExposureTime/gain. This
                      is what the real pipeline will actually record, and it
                      does NOT adapt to anything.

    lock=True and as_gpr=True give different frames whenever the ambient light
    differs from what the hardcoded values assume -- which is the whole reason
    --as-gpr exists."""
    Picamera2 = need_picamera2()
    picam2 = Picamera2()
    cfg = picam2.create_still_configuration(
        main={"size": CAPTURE_SIZE, "format": "RGB888"})   # -> BGR array
    picam2.configure(cfg)
    picam2.start()
    time.sleep(2.0)                     # let AE/AWB settle before we freeze them

    if lock or as_gpr:
        from libcamera import controls
        if as_gpr:
            ctrl = {"AfMode": controls.AfModeEnum.Manual,
                    "AeEnable": False, "AwbEnable": False}
            ctrl.update(GPR_CONTROLS)
        else:
            lp = lens_position if lens_position is not None else 1.0 / distance_m
            ctrl = {"AfMode": controls.AfModeEnum.Manual,
                    "LensPosition": lp,
                    "AeEnable": False, "AwbEnable": False}
            if exposure_us is not None:
                ctrl["ExposureTime"] = int(exposure_us)
            if gain is not None:
                ctrl["AnalogueGain"] = float(gain)
        picam2.set_controls(ctrl)
        time.sleep(1.5)
    return picam2


def cmd_as_gpr(args):
    """Show what capture_gpr.py will actually record, right now."""
    print("CAPTURE USING capture_gpr.py's HARDCODED CONTROLS")
    for k, v in GPR_CONTROLS.items():
        print(f"    {k:<14} {v}")
    print("\n  Every one of these is marked 'MEASURE ONCE' in capture_gpr.py.")
    print("  None has been measured. This is what the rig would record today.\n")

    picam2 = open_camera(as_gpr=True)
    try:
        bgr = picam2.capture_array()
        st, g = report_frame(bgr, "as_gpr")
    finally:
        picam2.stop(); picam2.close()

    lp = GPR_CONTROLS["LensPosition"]
    print(f"\n  LensPosition {lp} focuses at {1.0/lp:.2f} m.")
    print(f"  Your camera sits about {args.distance:.2f} m from the canopy.")
    if abs(1.0 / lp - args.distance) > 0.25:
        print("  ! These disagree. The frame above is out of focus by design.")
        print("    Run --focus-sweep and put the result into capture_gpr.py.")


def cmd_exposure_sweep(args):
    """Find the ExposureTime to hardcode, the same way --focus-sweep finds
    LensPosition. Run this at the hour the cron job runs -- noon."""
    steps = [2000, 4000, 8000, 12000, 16000, 24000, 33000, 50000, 75000]
    print("EXPOSURE SWEEP -- run this AT NOON, under the light the rig will")
    print("actually have. An exposure chosen at dusk is wrong by 5-6 stops.\n")
    print(f"  (capture_gpr.py currently hardcodes {GPR_CONTROLS['ExposureTime']} us)\n")

    picam2 = open_camera(lock=True, distance_m=args.distance,
                         exposure_us=steps[0], gain=1.0)
    ensure_out()
    rows = []
    try:
        print("  exposure   shutter    mean   blown%   crushed%   green%")
        for us in steps:
            picam2.set_controls({"ExposureTime": int(us), "AnalogueGain": 1.0})
            time.sleep(1.2)
            bgr = picam2.capture_array()
            st = exposure_stats(bgr)
            g, _ = green_fraction(bgr)
            rows.append((us, st, g))
            print(f"  {us:>7} us  1/{1000000//us:<6} {st['mean']:7.1f} "
                  f"{st['clip_hi']:7.2f} {st['clip_lo']:9.2f} {g:8.2f}")
            cv2.imwrite(os.path.join(OUT_DIR, f"exp_{us}.jpg"), bgr)
    finally:
        picam2.stop(); picam2.close()

    ok = [r for r in rows
          if 80 <= r[1]["mean"] <= 180 and r[1]["clip_hi"] < 1.0 and r[1]["clip_lo"] < 1.0]
    print()
    if ok:
        best = min(ok, key=lambda r: abs(r[1]["mean"] - 130))
        print(f"  best: ExposureTime = {best[0]} us   (mean {best[1]['mean']:.1f}, "
              f"green {best[2]:.2f} %)")
        print(f"\n  Put this in capture_gpr.py:   \"ExposureTime\": {best[0]},")
    else:
        print("  NOTHING in this range lands in the target window.")
        print("  Too dark everywhere -> add light, or raise AnalogueGain (adds noise).")
        print("  Too bright everywhere -> the scene is brighter than a 1/500 s")
        print("  shutter can handle; shade it or extend the sweep downward.")
    print(f"\n  Frames in {OUT_DIR}/exp_*.jpg -- confirm by eye.")
    print("  Watch the green% column: if it swings with exposure, your GPR is")
    print("  sensitive to lighting and the lock is doing real work.")


def sharpness(gray):
    """Variance of the Laplacian. Higher = crisper edges.

    The ABSOLUTE number is scene-dependent and means nothing on its own. It is
    only meaningful COMPARED between shots of the SAME scene -- which is exactly
    what --focus-sweep does."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def exposure_stats(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    total = gray.size
    return {
        "mean":      float(gray.mean()),
        "clip_hi":   100.0 * int((gray >= 250).sum()) / total,
        "clip_lo":   100.0 * int((gray <= 5).sum()) / total,
        "sharpness": sharpness(gray),
    }


def green_fraction(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv,
                    np.array([HUE_LO, SAT_MIN, VAL_MIN], np.uint8),
                    np.array([HUE_HI, 255, 255], np.uint8))
    return 100.0 * int(np.count_nonzero(m)) / m.size, m


def report_frame(bgr, tag):
    ensure_out()
    st = exposure_stats(bgr)
    gpct, mask = green_fraction(bgr)
    h, w = bgr.shape[:2]

    img_p  = os.path.join(OUT_DIR, f"{tag}.jpg")
    mask_p = os.path.join(OUT_DIR, f"{tag}_mask.png")
    cv2.imwrite(img_p, bgr)
    cv2.imwrite(mask_p, mask)

    print(f"\n  resolution     {w} x {h}")
    if (w, h) != CAPTURE_SIZE:
        print(f"    !! capture_gpr.py expects {CAPTURE_SIZE[0]}x{CAPTURE_SIZE[1]}. "
              f"ROI pixel coordinates will not line up.")
    print(f"  mean brightness{st['mean']:8.1f}      (want roughly 80-180)")
    print(f"  blown-out      {st['clip_hi']:8.2f} %    (want < 1 %)")
    print(f"  crushed black  {st['clip_lo']:8.2f} %    (want < 1 %)")
    print(f"  sharpness      {st['sharpness']:8.1f}      (compare, never absolute)")
    print(f"  green pixels   {gpct:8.2f} %    HSV H{HUE_LO}-{HUE_HI} S>{SAT_MIN} V>{VAL_MIN}")
    print(f"\n  saved  {img_p}")
    print(f"  saved  {mask_p}   <- OPEN THIS. Leaves white, everything else black.")

    if st["clip_hi"] > 1.0:
        print("\n  ! blown highlights. Leaves that clip to white lose saturation and")
        print("    drop out of the HSV band -- GPR reads LOW in bright sun.")
    if st["mean"] < 60:
        print("\n  ! dark frame. V>40 will reject shadowed leaf and GPR reads low.")
    return st, gpct


# --------------------------------------------------------------------- 2 ---
def cmd_capture(args):
    picam2 = open_camera(lock=not args.auto, distance_m=args.distance)
    try:
        bgr = picam2.capture_array()
        print("SINGLE CAPTURE" + ("  (auto exposure/focus)" if args.auto
                                  else "  (locked, as capture_gpr.py runs it)"))
        report_frame(bgr, "capture")
    finally:
        picam2.stop(); picam2.close()


# --------------------------------------------------------------------- 3 ---
def cmd_focus_sweep(args):
    """Autofocus MUST be locked for a 35-day series -- if focus hunts between
    days, edge sharpness changes and the green pixel count drifts with no
    change in the plant. This finds the value to lock it AT."""
    Picamera2 = need_picamera2()
    cams = Picamera2.global_camera_info()
    if cams and "imx708" not in cams[0].get("Model", "").lower():
        print("This camera has no autofocus -- nothing to sweep. Focus is fixed.")
        return

    nominal = 1.0 / args.distance
    positions = [round(nominal + d, 2) for d in
                 (-0.40, -0.25, -0.15, -0.05, 0.0, 0.05, 0.15, 0.25, 0.40)]
    positions = [p for p in positions if p >= 0.0]

    print(f"FOCUS SWEEP around {nominal:.2f} dioptres "
          f"(= {args.distance:.2f} m to the canopy)\n")
    print("  Put a leaf, or a printed page of text, at the CANOPY plane first --")
    print("  not on the floor. Focusing on the floor leaves the leaves soft.\n")

    picam2 = open_camera(lock=True, lens_position=positions[0],
                         distance_m=args.distance)
    ensure_out()
    results = []
    try:
        print("  LensPosition   distance     sharpness")
        for lp in positions:
            picam2.set_controls({"LensPosition": lp})
            time.sleep(1.2)
            bgr = picam2.capture_array()
            g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            s = sharpness(g)
            results.append((lp, s))
            dist = ("inf" if lp <= 0.01 else f"{1.0/lp:.2f} m")
            print(f"  {lp:>10.2f}   {dist:>8}   {s:10.1f}")
            cv2.imwrite(os.path.join(OUT_DIR, f"focus_{lp:.2f}.jpg"), bgr)
    finally:
        picam2.stop(); picam2.close()

    best = max(results, key=lambda r: r[1])
    print(f"\n  sharpest: LensPosition = {best[0]:.2f}  (score {best[1]:.1f})")
    if best[0] in (positions[0], positions[-1]):
        print("  ! the best value is at the EDGE of the sweep -- the true optimum is")
        print("    outside it. Re-run with a --distance closer to reality.")
    print(f"\n  Put this in capture_gpr.py:   \"LensPosition\": {best[0]:.2f}")
    print(f"  Frames are in {OUT_DIR}/focus_*.jpg -- confirm by eye before trusting")
    print("  the number. Laplacian variance also rewards noise and moving leaves.")


# --------------------------------------------------------------------- 4 ---
def cmd_rois(args):
    if not os.path.exists(ROI_FILE):
        print(f"no {ROI_FILE} -- run make_rois.py first.")
        return
    with open(ROI_FILE) as f:
        cfg = json.load(f)
    rois = cfg.get("rois", cfg)
    circular = bool(cfg.get("circular", True))

    picam2 = open_camera(lock=True, distance_m=args.distance)
    try:
        bgr = picam2.capture_array()
    finally:
        picam2.stop(); picam2.close()

    h, w = bgr.shape[:2]
    gpct, mask = green_fraction(bgr)
    out = bgr.copy()
    problems = []

    print(f"\n  frame {w}x{h}   ROI file: {len(rois)} entries, "
          f"circular={circular}\n")
    print("  pot     inside frame     green in ROI")
    for i in range(9):
        pid = f"P-0{i+1}"
        r = rois.get(pid)
        if not r:
            problems.append(f"{pid} missing from {ROI_FILE}")
            continue
        x, y, ww, hh = r["x"], r["y"], r["w"], r["h"]
        inside = (x >= 0 and y >= 0 and x + ww <= w and y + hh <= h)

        area = np.zeros((h, w), np.uint8)
        if circular:
            cx, cy = x + ww // 2, y + hh // 2
            rad = min(ww, hh) // 2
            cv2.circle(area, (cx, cy), rad, 255, -1)
            cv2.circle(out, (cx, cy), rad, (0, 255, 0) if inside else (0, 0, 255), 3)
        else:
            area[max(0, y):y + hh, max(0, x):x + ww] = 255
            cv2.rectangle(out, (x, y), (x + ww, y + hh),
                          (0, 255, 0) if inside else (0, 0, 255), 3)

        tot = int(np.count_nonzero(area))
        grn = int(np.count_nonzero(cv2.bitwise_and(mask, mask, mask=area)))
        pct = 100.0 * grn / tot if tot else 0.0
        cv2.putText(out, pid, (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 255, 0) if inside else (0, 0, 255), 2)

        print(f"  {pid}   {'yes' if inside else 'NO -- CLIPPED':<16} {pct:6.2f} %")
        if not inside:
            problems.append(f"{pid} extends outside the frame")

    ensure_out()
    p = os.path.join(OUT_DIR, "rois.jpg")
    cv2.imwrite(p, out)
    print(f"\n  saved  {p}   <- open it, check every circle sits on a pot rim")

    if problems:
        print("\n  PROBLEMS:")
        for x in problems:
            print(f"    * {x}")
        print("\n  A clipped ROI does not error. It reads a smaller area and that")
        print("  pot's GPR is wrong for all 35 days. Raise the camera or re-run")
        print("  make_rois.py against THIS frame.")
    else:
        print("\n  all nine ROIs are fully inside the frame.")


# --------------------------------------------------------------------- 5 ---
def cmd_check(args):
    print("=" * 62)
    print("CAMERA ACCEPTANCE CHECK")
    print("=" * 62)
    if not cmd_info():
        return
    print("\n" + "-" * 62)
    picam2 = open_camera(lock=True, distance_m=args.distance)
    try:
        print("\nLOCKED CAPTURE (exactly as capture_gpr.py runs it)")
        bgr = picam2.capture_array()
        st1, g1 = report_frame(bgr, "check_1")

        print("\n" + "-" * 62)
        print("REPEATABILITY -- two frames 5 s apart, nothing moving.")
        print("Locked controls mean these should be nearly identical. Drift here")
        print("is drift that will show up as fake growth in your time series.")
        time.sleep(5)
        bgr2 = picam2.capture_array()
        st2, g2 = report_frame(bgr2, "check_2")

        dg = abs(g2 - g1)
        db = abs(st2["mean"] - st1["mean"])
        print(f"\n  green delta      {dg:6.3f} pp   (want < 0.10)")
        print(f"  brightness delta {db:6.2f}     (want < 2.0)")
        if dg > 0.10 or db > 2.0:
            print("\n  ! NOT STABLE. Something is still auto-adjusting, or the light")
            print("    is changing. Confirm AeEnable/AwbEnable are False and AfMode")
            print("    is Manual. An unstable camera makes GPR unusable.")
        else:
            print("\n  stable.")
    finally:
        picam2.stop(); picam2.close()

    print("\n" + "-" * 62)
    cmd_rois(args)

    print("\n" + "=" * 62)
    print("Open every file in " + OUT_DIR + " before you call this passed.")
    print("The numbers tell you where to look. Your eyes decide.")
    print("=" * 62)


def main():
    global OUT_DIR, ROI_FILE
    ap = argparse.ArgumentParser(description="Group B camera acceptance test")
    ap.add_argument("--info",        action="store_true")
    ap.add_argument("--capture",     action="store_true")
    ap.add_argument("--focus-sweep", action="store_true")
    ap.add_argument("--rois",        action="store_true")
    ap.add_argument("--check",       action="store_true")
    ap.add_argument("--as-gpr",      action="store_true",
                    help="capture with capture_gpr.py's hardcoded controls")
    ap.add_argument("--exposure-sweep", action="store_true",
                    help="find the ExposureTime to hardcode. RUN AT NOON.")
    ap.add_argument("--auto",        action="store_true",
                    help="--capture with auto exposure/focus, for comparison")
    ap.add_argument("--distance", type=float, default=DEFAULT_SUBJECT_M,
                    help="metres from lens to CANOPY plane (default %.2f)"
                         % DEFAULT_SUBJECT_M)
    ap.add_argument("--out-dir", default=None, metavar="DIR",
                    help="where to save images (default %s). Created if needed."
                         % OUT_DIR)
    ap.add_argument("--roi-file", default=None, metavar="FILE",
                    help="pot_rois.json to check against (default %s)" % ROI_FILE)
    a = ap.parse_args()

    if a.out_dir:
        OUT_DIR = os.path.abspath(os.path.expanduser(a.out_dir))
    if a.roi_file:
        ROI_FILE = os.path.abspath(os.path.expanduser(a.roi_file))
    print(f"[cam_check] images -> {OUT_DIR}")

    if   a.info:           cmd_info()
    elif a.as_gpr:         cmd_as_gpr(a)
    elif a.exposure_sweep: cmd_exposure_sweep(a)
    elif a.capture:     cmd_capture(a)
    elif a.focus_sweep: cmd_focus_sweep(a)
    elif a.rois:        cmd_rois(a)
    elif a.check:       cmd_check(a)
    else:
        ap.print_help()
        print("\nStart with:  python3 cam_check.py --info")


if __name__ == "__main__":
    main()
