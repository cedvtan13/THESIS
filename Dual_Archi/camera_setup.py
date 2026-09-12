#!/usr/bin/env python3
"""
camera_setup.py -- measure the three camera controls that capture_gpr.py
needs, and verify the rig framing.

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

capture_gpr.py locks LensPosition, ExposureTime and ColourGains so that
acquisition conditions stay identical across all 35 days. The values in the
script are placeholders. This tool measures the real ones on the rig.

WHY THEY MUST BE LOCKED
    The methodology treats lighting as a strict control variable. Autofocus,
    auto-exposure and auto-white-balance all fight that. If the camera
    refocuses slightly overnight, leaf edges sharpen or soften and the green
    pixel count moves without the plant changing. If auto-exposure compensates
    for a duller morning, the HSV values shift and GPR moves for the same
    reason. Every such change becomes noise in the growth curve that looks
    exactly like biology.

COMMANDS
    python3 camera_setup.py height --array 690
        Compute the required mounting height for your measured array size.

    python3 camera_setup.py frame --height 1030
        Capture one frame and report whether the whole array is visible,
        with a grid overlay so you can judge centring and squareness.

    python3 camera_setup.py focus --height 1030
        Sweep LensPosition, score each by image sharpness, report the best.

    python3 camera_setup.py exposure
        Sweep ExposureTime, report which avoids clipping.

    python3 camera_setup.py whitebalance
        Measure ColourGains once the exposure is fixed.

    python3 camera_setup.py verify --lens 0.97 --exposure 8000 --gains 1.8,1.6
        Capture with the final locked settings for a last visual check.
"""

import argparse
import math
import os
import sys
import time

import cv2
import numpy as np

try:
    from picamera2 import Picamera2
    from libcamera import controls
except ImportError:
    print("picamera2 not found. Run on the Raspberry Pi, inside a venv created")
    print("with:  python3 -m venv --system-site-packages ~/thesis-env")
    sys.exit(1)

# Camera Module 3 standard lens, full-field
VFOV_DEG = 41.0
HFOV_DEG = 66.0
RES = (2304, 1296)


# ---------------------------------------------------------------------------
def open_cam(lens=None, exposure=None, gains=None):
    cam = Picamera2()
    cam.configure(cam.create_still_configuration(main={"size": RES}))
    cam.start()
    ctl = {}
    if lens is not None:
        ctl["AfMode"] = controls.AfModeEnum.Manual
        ctl["LensPosition"] = float(lens)
    if exposure is not None:
        ctl["AeEnable"] = False
        ctl["ExposureTime"] = int(exposure)
        ctl["AnalogueGain"] = 1.0
    if gains is not None:
        ctl["AwbEnable"] = False
        ctl["ColourGains"] = tuple(gains)
    if ctl:
        cam.set_controls(ctl)
    time.sleep(2.0)          # let the locked settings settle
    return cam


def grab(cam):
    return cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)


def sharpness(img):
    """Variance of the Laplacian. Higher means more high-frequency detail,
    which for a fixed scene means better focus."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


# ---------------------------------------------------------------------------
def cmd_height(args):
    a = args.array
    vmin = (a / 2) / math.tan(math.radians(VFOV_DEG) / 2)
    print(f"\nArray to be framed : {a} x {a} mm")
    print(f"Camera v3 FOV      : {VFOV_DEG} deg vertical, {HFOV_DEG} deg horizontal")
    print("\nThe VERTICAL field of view is the narrower of the two, so it is")
    print("what limits you. A height that satisfies it will always satisfy the")
    print("horizontal direction as well.\n")
    print(f"Absolute minimum height : {vmin:.0f} mm  (array exactly fills the frame)")
    for pct, label in ((1.08, "tight"), (1.12, "recommended"), (1.20, "generous")):
        h = vmin * pct
        cov_v = 2 * h * math.tan(math.radians(VFOV_DEG) / 2)
        cov_h = 2 * h * math.tan(math.radians(HFOV_DEG) / 2)
        margin = (cov_v - a) / 2
        ppmm = RES[1] / cov_v
        print(f"  {label:<12} {h:6.0f} mm -> covers {cov_h:.0f} x {cov_v:.0f} mm, "
              f"{margin:.0f} mm margin each edge, {ppmm:.2f} px/mm")
    rec = vmin * 1.12
    print(f"\nMeasure from the POT RIM, not the floor or the bench.")
    print(f"Suggested starting LensPosition = 1 / {rec/1000:.3f} m = "
          f"{1000/rec:.2f} dioptres")


# ---------------------------------------------------------------------------
def cmd_frame(args):
    cam = open_cam(lens=(1000.0 / args.height) if args.height else None)
    img = grab(cam)
    cam.stop(); cam.close()

    out = img.copy()
    h, w = out.shape[:2]
    # thirds grid, to judge centring and squareness by eye
    for i in (1, 2):
        cv2.line(out, (w * i // 3, 0), (w * i // 3, h), (0, 255, 255), 2)
        cv2.line(out, (0, h * i // 3), (w, h * i // 3), (0, 255, 255), 2)
    cv2.line(out, (w // 2, 0), (w // 2, h), (0, 0, 255), 1)
    cv2.line(out, (0, h // 2), (w, h // 2), (0, 0, 255), 1)

    cv2.imwrite("frame_check.jpg", img)
    cv2.imwrite("frame_grid.jpg", out)
    print("\nwrote frame_check.jpg  (clean capture)")
    print("wrote frame_grid.jpg   (with thirds grid and centre cross)")
    print("\nCopy both to your laptop and check:")
    print("  1. all nine pots fully visible, none clipped at any edge")
    print("  2. a visible gap between the outermost pots and the frame edge")
    print("  3. the centre pot sits on the red cross")
    print("  4. each row of pots runs parallel to a yellow line -- if rows")
    print("     appear to converge, the camera is tilted and not truly nadir")


# ---------------------------------------------------------------------------
def cmd_focus(args):
    start = 1000.0 / args.height if args.height else 1.0
    lo = max(0.0, start - args.span)
    hi = start + args.span
    steps = np.linspace(lo, hi, args.steps)

    print(f"\nSweeping LensPosition {lo:.2f} to {hi:.2f} in {args.steps} steps.")
    print("LensPosition is in DIOPTRES = 1 / (distance in metres).")
    print(f"At {args.height} mm that is nominally {start:.2f}.\n")
    print("Put a pot with real foliage under the camera before running this.")
    print("Focusing on bare soil gives a misleading peak.\n")

    cam = open_cam(exposure=args.exposure)
    results = []
    for lp in steps:
        cam.set_controls({"AfMode": controls.AfModeEnum.Manual,
                          "LensPosition": float(lp)})
        time.sleep(1.2)
        img = grab(cam)
        s = sharpness(img)
        results.append((float(lp), s))
        bar = "#" * int(s / max(1, max(r[1] for r in results)) * 40)
        print(f"  LensPosition {lp:5.2f} -> sharpness {s:9.1f}  {bar}")
        cv2.imwrite(f"focus_{lp:.2f}.jpg", img)
    cam.stop(); cam.close()

    best = max(results, key=lambda r: r[1])
    print(f"\nSHARPEST: LensPosition = {best[0]:.2f}  (score {best[1]:.1f})")
    print(f"  implied focus distance {1.0/best[0]*1000:.0f} mm")
    print("\nLook at the saved focus_*.jpg files and confirm the peak looks")
    print("sharp to your eye too. The metric can be fooled by a frame where")
    print("something moved.")
    print(f"\nThen set in capture_gpr.py:   \"LensPosition\": {best[0]:.2f},")


# ---------------------------------------------------------------------------
def cmd_exposure(args):
    times = [1000, 2000, 4000, 8000, 16000, 32000, 64000]
    print("\nSweeping ExposureTime under your CURRENT lighting.")
    print("Run this with the LED array on and at the same time of day you")
    print("intend to capture.\n")
    cam = open_cam(lens=args.lens)
    best = None
    for et in times:
        cam.set_controls({"AeEnable": False, "ExposureTime": et,
                          "AnalogueGain": 1.0})
        time.sleep(1.5)
        img = grab(cam)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean = g.mean()
        clipped = (g >= 254).mean() * 100
        dark = (g <= 1).mean() * 100
        flag = ""
        if clipped > 0.5:
            flag = "  <- CLIPPING, detail lost in highlights"
        elif mean < 60:
            flag = "  <- too dark"
        elif 90 <= mean <= 170 and clipped <= 0.5:
            flag = "  <- good"
            if best is None:
                best = et
        print(f"  {et:6} us -> mean {mean:6.1f}, clipped {clipped:5.2f}%, "
              f"black {dark:5.2f}%{flag}")
        cv2.imwrite(f"exposure_{et}.jpg", img)
    cam.stop(); cam.close()
    if best:
        print(f"\nSuggested: ExposureTime = {best}")
    else:
        print("\nNo setting landed in the good band. Adjust the lighting level")
        print("rather than pushing exposure to an extreme.")
    print("\nThen set in capture_gpr.py:   \"ExposureTime\": <value>,")


# ---------------------------------------------------------------------------
def cmd_whitebalance(args):
    print("\nMeasuring ColourGains with auto white balance ON, so the values")
    print("it settles on can then be locked in.\n")
    print("Place a sheet of white paper covering most of the array first.\n")
    cam = Picamera2()
    cam.configure(cam.create_still_configuration(main={"size": RES}))
    cam.start()
    cam.set_controls({"AeEnable": False, "ExposureTime": args.exposure,
                      "AnalogueGain": 1.0, "AwbEnable": True})
    time.sleep(4.0)
    md = cam.capture_metadata()
    img = grab(cam)
    cam.stop(); cam.close()
    cv2.imwrite("whitebalance_check.jpg", img)
    g = md.get("ColourGains")
    if g:
        print(f"Auto white balance settled on ColourGains = "
              f"({g[0]:.2f}, {g[1]:.2f})")
        print(f"\nThen set in capture_gpr.py:   "
              f"\"ColourGains\": ({g[0]:.2f}, {g[1]:.2f}),")
    else:
        print("Camera did not report ColourGains. Keep the defaults and note it.")
    print("\nRemove the paper before any further captures.")


# ---------------------------------------------------------------------------
def cmd_verify(args):
    gains = tuple(float(x) for x in args.gains.split(","))
    cam = open_cam(lens=args.lens, exposure=args.exposure, gains=gains)
    shots = []
    for i in range(3):
        img = grab(cam)
        cv2.imwrite(f"verify_{i}.jpg", img)
        shots.append(img)
        print(f"  capture {i+1}: sharpness {sharpness(img):.1f}, "
              f"mean brightness {cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean():.1f}")
        time.sleep(2)
    cam.stop(); cam.close()

    d = np.abs(shots[0].astype(int) - shots[2].astype(int)).mean()
    print(f"\nmean pixel difference between first and third capture: {d:.2f}")
    if d < 2.0:
        print("  settings are stable -- repeat captures are consistent")
    else:
        print("  !! captures differ noticeably. Something is still automatic,")
        print("     or the light is changing. Re-check that AeEnable, AwbEnable")
        print("     are False and AfMode is Manual.")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Camera rig setup and calibration")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("height"); p.add_argument("--array", type=float, required=True)
    p.set_defaults(func=cmd_height)

    p = sp.add_parser("frame"); p.add_argument("--height", type=float)
    p.set_defaults(func=cmd_frame)

    p = sp.add_parser("focus")
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--span", type=float, default=0.6)
    p.add_argument("--steps", type=int, default=13)
    p.add_argument("--exposure", type=int, default=8000)
    p.set_defaults(func=cmd_focus)

    p = sp.add_parser("exposure"); p.add_argument("--lens", type=float, required=True)
    p.set_defaults(func=cmd_exposure)

    p = sp.add_parser("whitebalance")
    p.add_argument("--exposure", type=int, required=True)
    p.set_defaults(func=cmd_whitebalance)

    p = sp.add_parser("verify")
    p.add_argument("--lens", type=float, required=True)
    p.add_argument("--exposure", type=int, required=True)
    p.add_argument("--gains", required=True)
    p.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
