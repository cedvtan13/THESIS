#!/usr/bin/env python3
"""roi_drift.py -- how far has each pot moved from its circle in pot_rois.json?

Finds each pot's rim near its current circle (Hough circle fit on a saved frame
or a fresh photo) and prints the offset in pixels. With --apply it re-centres the
circles on the fitted rims, after backing up the old file. Sizes never change.

    python3 tools/roi_drift.py --frame ~/agrisentry_data/frames/D10_2026-11-07_1200.png
    python3 tools/roi_drift.py --capture --out /tmp/roi_drift.jpg
    python3 tools/roi_drift.py --frame F.png --apply --backup-tag D10_recentre

A pot whose rim is not found (hidden by leaves, a person, a cloth) keeps the
median shift of the pots that were found. Check the picture before --apply.
"""
import argparse
import json
import os
import shutil
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import capture_gpr as cg  # noqa: E402

SEARCH_PX = 90          # how far from the current centre a rim may be found


def fit(gray, cx, cy, r_roi):
    """Best rim circle near (cx, cy); rim radius is about r_roi / 0.9."""
    rim = r_roi / 0.9
    x0, y0 = int(max(0, cx - rim - SEARCH_PX)), int(max(0, cy - rim - SEARCH_PX))
    x1 = int(min(gray.shape[1], cx + rim + SEARCH_PX))
    y1 = int(min(gray.shape[0], cy + rim + SEARCH_PX))
    sub = cv2.medianBlur(gray[y0:y1, x0:x1], 5)
    c = cv2.HoughCircles(sub, cv2.HOUGH_GRADIENT, dp=1.2, minDist=40, param1=90, param2=28,
                         minRadius=int(rim * 0.85), maxRadius=int(rim * 1.2))
    if c is None:
        return None
    best = None
    for x, y, r in c[0]:
        x, y = x + x0, y + y0
        dist = float(np.hypot(x - cx, y - cy))
        if dist <= SEARCH_PX and (best is None or dist < best[3]):
            best = (float(x), float(y), float(r), dist)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--frame", help="a saved frame (PNG)")
    src.add_argument("--capture", action="store_true", help="take a fresh photo")
    ap.add_argument("--roi-file", default=cg.ROI_FILE)
    ap.add_argument("--out", default="/tmp/roi_drift.jpg", help="check picture")
    ap.add_argument("--apply", action="store_true",
                    help="re-centre the circles: all shifted by the median (camera moved)")
    ap.add_argument("--per-pot", action="store_true",
                    help="with --apply: move each circle to its own rim fit (pots moved)")
    ap.add_argument("--backup-tag", default="recentre", help="pot_rois_before_<tag>.json")
    args = ap.parse_args()

    frame = cg.capture_frame(use_light=False) if args.capture else cv2.imread(args.frame)
    if frame is None:
        sys.exit(f"cannot read {args.frame}")
    with open(args.roi_file) as f:
        cfg = json.load(f)
    rois = cfg["rois"]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    fits, shifts = {}, []
    print(f"{'pot':5} {'centre now':>12} {'rim found':>12} {'shift x,y':>11} {'dist':>5}")
    for pid in sorted(rois):
        cx, cy, r = cg.roi_geometry(rois[pid])
        b = fit(gray, cx, cy, r)
        fits[pid] = b
        if b:
            dx, dy = b[0] - cx, b[1] - cy
            shifts.append((dx, dy))
            print(f"{pid:5} {cx:6.0f},{cy:<5.0f} {b[0]:6.0f},{b[1]:<5.0f} {dx:+5.0f},{dy:+5.0f} {b[3]:5.0f}")
        else:
            print(f"{pid:5} {cx:6.0f},{cy:<5.0f}   not found")
    if not shifts:
        sys.exit("no rims found -- check the picture by eye")
    mdx = float(np.median([s[0] for s in shifts]))
    mdy = float(np.median([s[1] for s in shifts]))
    print(f"\nmedian shift: {mdx:+.0f} px x, {mdy:+.0f} px y  ({len(shifts)}/9 rims found)")

    o = frame.copy()
    for pid, r in rois.items():
        cx, cy, rad = cg.roi_geometry(r)
        cv2.circle(o, (int(cx), int(cy)), int(rad), (0, 255, 255), 2)        # yellow: now
        b = fits[pid]
        if b:
            cv2.circle(o, (int(b[0]), int(b[1])), int(b[2]), (255, 0, 255), 2)  # magenta: rim
        cv2.putText(o, pid, (int(cx) - 30, int(cy) - int(rad) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.9, (0, 255, 255), 2)
    cv2.imwrite(args.out, o, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"picture -> {args.out}  (yellow = circle now, magenta = rim found)")

    if args.apply:
        bak = os.path.join(os.path.dirname(args.roi_file), f"pot_rois_before_{args.backup_tag}.json")
        shutil.copy2(args.roi_file, bak)
        for pid, r in rois.items():
            cx, cy, rad = cg.roi_geometry(r)
            b = fits[pid]
            nx, ny = (b[0], b[1]) if (b and args.per_pot) else (cx + mdx, cy + mdy)
            r["x"] = int(round(nx - r["w"] / 2.0))
            r["y"] = int(round(ny - r["h"] / 2.0))
        how = "each pot to its rim fit" if args.per_pot else f"all pots by {mdx:+.0f},{mdy:+.0f} px"
        cfg["_comment"] = (f"re-centred by roi_drift.py ({how}) on "
                           f"{os.path.basename(args.frame) if args.frame else 'a fresh photo'}. "
                           f"Before: {os.path.basename(bak)}")
        with open(args.roi_file, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"re-centred {args.roi_file}: {how}  (backup: {bak})")


if __name__ == "__main__":
    main()
