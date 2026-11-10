#!/usr/bin/env python3
"""
glare_check.py -- flag sun glare on each pot in the saved noon frame.

Sun patches through the greenhouse frame can over-expose some pots at noon. In an
over-exposed pot the leaves clip and turn yellowish, so the green threshold misses
them (D6, P-07: hue 30-33 under H 38). This tool records which pots were affected
each day, so GPR rows from glare days can be treated with care in the analysis.
It only reads the saved frame: it never opens the camera.

Per pot (inside its pot circle):
    clip_pct        share of pixels with V >= 250 (clipped)
    rel_brightness  pot mean V / median pot mean V for that frame
    level           GLARE  clip_pct >= 5 and rel_brightness >= 1.4
                    MILD   rel_brightness >= 1.4 (not GLARE)
                    DARK   rel_brightness <= 0.6 (deep shade; dark leaves can miss V >= 55)
                    ok     otherwise
White tubes and sensor boards inside the pots always clip a little (0-4 % on
D1-D5), so clip_pct alone is not glare.

Usage:
    python3 tools/glare_check.py                 # every noon frame not yet in the log
    python3 tools/glare_check.py --days 4 5 6 --roi-file pot_rois_before_D6_recentre.json
                                                 # back-fill with the circles used on those days

Cron (installed by agrisentry.sh), after the noon capture window:
    55 12 * * *  python3 ~/THESIS/Dual_Archi/tools/glare_check.py

Output: ~/thesis/glare_log.csv
    day, frame, pot_id, clip_pct, rel_brightness, pot_mean_v, frame_mean_v, level, roi_file
Days with any GLARE, MILD or DARK pot also get one line in field_log.csv.
"""
import argparse
import csv
import glob
import json
import os
import re

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DUAL = os.path.dirname(HERE)
FRAME_DIR = os.path.expanduser("~/agrisentry_data/frames")
LOG = os.path.join(DUAL, "glare_log.csv")
FIELD_LOG = os.path.join(DUAL, "field_log.csv")
HEADER = ["day", "frame", "pot_id", "clip_pct", "rel_brightness", "pot_mean_v",
          "frame_mean_v", "level", "roi_file"]

CLIP_V = 250
GLARE_CLIP_PCT = 5.0
BRIGHT_REL = 1.4
DARK_REL = 0.6
FRAME_RE = re.compile(r"^D(\d+)_(\d{4}-\d{2}-\d{2})_(\d{4})\.png$")


def logged_days():
    if not os.path.exists(LOG):
        return set()
    with open(LOG, newline="") as f:
        return {int(r["day"]) for r in csv.DictReader(f)}


def noon_frames():
    """{day: (path, date)} for DXX_YYYY-MM-DD_HHMM.png; the latest frame wins per day."""
    out = {}
    for path in sorted(glob.glob(os.path.join(FRAME_DIR, "D*_*.png"))):
        m = FRAME_RE.match(os.path.basename(path))
        if m:
            out[int(m.group(1))] = (path, m.group(2))
    return out


def level(clip, rel):
    if clip >= GLARE_CLIP_PCT and rel >= BRIGHT_REL:
        return "GLARE"
    if rel >= BRIGHT_REL:
        return "MILD"
    if rel <= DARK_REL:
        return "DARK"
    return "ok"


def check(path, rois, radius):
    frame = cv2.imread(path)
    if frame is None:
        raise SystemExit(f"[glare_check] cannot read {path}")
    v = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 2]
    rows = []
    for pid in sorted(rois):
        r = rois[pid]
        cx, cy = r["x"] + r["w"] / 2.0, r["y"] + r["h"] / 2.0
        mask = np.zeros(v.shape, np.uint8)
        cv2.circle(mask, (int(round(cx)), int(round(cy))), radius, 255, -1)
        px = v[mask > 0]
        rows.append([pid, float((px >= CLIP_V).mean() * 100.0), float(px.mean())])
    med = float(np.median([m for _, _, m in rows]))
    return float(v.mean()), [(pid, clip, mean, mean / med) for pid, clip, mean in rows]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--days", nargs="+", type=int, help="only these days (re-checks them even if logged)")
    ap.add_argument("--roi-file", default=os.path.join(DUAL, "pot_rois.json"))
    ap.add_argument("--no-field-log", action="store_true")
    args = ap.parse_args()

    roi_path = args.roi_file if os.path.isabs(args.roi_file) else os.path.join(DUAL, args.roi_file)
    with open(roi_path) as f:
        rois = json.load(f)["rois"]
    radius = int(round(min(r["w"] for r in rois.values()) / 2.0))

    frames = noon_frames()
    done = logged_days()
    todo = sorted(args.days) if args.days else sorted(d for d in frames if d not in done)
    if not todo:
        print("[glare_check] nothing new to check")
        return

    new_file = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(HEADER)
        for d in todo:
            if d not in frames:
                print(f"[glare_check] D{d}: no noon frame (missed day?) -- skipped")
                continue
            if d in done:
                print(f"[glare_check] D{d}: already in {os.path.basename(LOG)} -- skipped")
                continue
            path, date = frames[d]
            day_rois, roi_tag = rois, os.path.basename(roi_path)
            try:    # follow the camera, exactly as capture_gpr.py does (from D10)
                import sys
                sys.path.insert(0, DUAL)
                import capture_gpr as cg
                img = cv2.imread(path)
                if img is not None:
                    day_rois, dx, dy, _, applied = cg.aligned_rois(img, rois, log=False)
                    if applied:
                        roi_tag += f"+align({dx:+.0f},{dy:+.0f})"
            except Exception as e:      # never lose the glare check over alignment
                print(f"[glare_check] alignment skipped ({e})")
            fmean, res = check(path, day_rois, radius)
            flagged = []
            for pid, clip, mean, rel in res:
                lv = level(clip, rel)
                w.writerow([d, os.path.basename(path), pid, f"{clip:.1f}", f"{rel:.2f}",
                            f"{mean:.1f}", f"{fmean:.1f}", lv, roi_tag])
                if lv != "ok":
                    flagged.append(f"{pid} {lv} (clip {clip:.1f} %, {rel:.1f}x)")
            print(f"[glare_check] D{d} {os.path.basename(path)}: "
                  + ("; ".join(flagged) if flagged else "no glare"))
            if flagged and not args.no_field_log:
                pots = ";".join(s.split()[0] for s in flagged)
                note = "[glare_check] noon light: " + "; ".join(flagged)
                with open(FIELD_LOG, "a", newline="") as fl:
                    csv.writer(fl).writerow([date, d, pots, note])


if __name__ == "__main__":
    main()
