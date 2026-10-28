#!/usr/bin/env python3
"""
recompute_cell_gpr.py -- GPR inside each pot's own CELL, recomputed from the
saved noon frames.

Why: from about D16 the seedlings lean toward the light and grow out past the
pot rim, so the pot-circle GPR (raw_gpr) drops to 0 although the plants are
alive. The old territory circle (terr_gpr, r = 221 px) is big enough, but
neighbouring territory circles overlap (real spacing is 25-31 cm, the circle
assumes 33 cm), so a leaf could count for two pots.

The CELL of a pot = every pixel closer to that pot's centre than to any other
pot's centre (a Voronoi cell), capped at CELL_R_PX from the centre. Cells never
overlap, and leaning leaves stay inside their own pot's cell.

The green mask is exactly the live pipeline's (capture_gpr.green_mask: same HSV
band, same full-frame 3x3 opening). Pot centres come from the ROI file that was
live on that day (they moved on D16 and D22 when the camera was re-aligned).
The live capture is NOT changed by this script.

USAGE (Pi or Mac; needs opencv + numpy)
    python3 tools/recompute_cell_gpr.py                      # all frames, D12+
    python3 tools/recompute_cell_gpr.py --frames-dir DIR --out cell_gpr.csv
    python3 tools/recompute_cell_gpr.py --overlay-day 21     # also save a picture
"""

import argparse
import csv
import glob
import json
import os
import re
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DUAL = os.path.dirname(HERE)
sys.path.insert(0, DUAL)
import capture_gpr as cg  # noqa: E402  (same mask code as the live pipeline)

CELL_R_PX = cg.CELL_R_PX  # same cell as the live capture (run 2 writes cell_gpr itself)

# Which ROI file was live from which day on, per run (keyed by sowing date).
# Run 1 (sown 2026-10-06, archived): frames exist from D12.
ROI_SCHEDULES = {
    "2026-10-06": [
        (11, "pot_rois_before_20261021.json"),   # D11-D15: rims re-fitted Oct 16
        (16, "pot_rois_before_20261027.json"),   # D16-D21: shifted after the camera knock
        (22, "pot_rois_before_run2.json"),        # D22-D23: shifted for drift Oct 27
    ],
}
DEFAULT_SCHEDULE = [(1, "pot_rois.json")]       # any later run: add rows here if ROIs move
ROI_SCHEDULE = ROI_SCHEDULES.get(cg.sowing_date(), DEFAULT_SCHEDULE)


def rois_for_day(day):
    name = None
    for start, fname in ROI_SCHEDULE:
        if day >= start:
            name = fname
    if name is None:
        return None
    with open(os.path.join(DUAL, name)) as f:
        return json.load(f)["rois"]


def cells(shape_hw, rois):
    """{pot_id: bool mask} -- the live pipeline's cells (capture_gpr.cell_masks)."""
    return {p: m > 0 for p, m in cg.cell_masks(shape_hw, rois, CELL_R_PX).items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--frames-dir", default=cg.FRAME_DIR)
    ap.add_argument("--out", default=os.path.join(cg.BASE, "cell_gpr.csv"))
    ap.add_argument("--overlay-day", type=int, help="save an overlay picture for this day")
    args = ap.parse_args()

    frames = {}
    for path in glob.glob(os.path.join(args.frames_dir, "D*_*.png")):
        name = os.path.basename(path)
        m = re.match(r"D(\d+)_\d{4}-\d{2}-\d{2}_(\d{4})\.png$", name)   # noon frames only
        if m:
            frames[int(m.group(1))] = path
    if not frames:
        sys.exit(f"no noon frames found in {args.frames_dir}")

    rows = []
    for day in sorted(frames):
        rois = rois_for_day(day)
        img = cv2.imread(frames[day])
        if rois is None or img is None:
            continue
        green = cg.green_mask(cv2.cvtColor(img, cv2.COLOR_BGR2HSV)) > 0
        cm = cells(img.shape[:2], rois)
        for pid in sorted(cm):
            total = int(cm[pid].sum())
            g = int((green & cm[pid]).sum())
            rows.append({"day": day, "frame": os.path.basename(frames[day]), "pot_id": pid,
                         "cell_gpr": f"{100.0 * g / total:.2f}", "cell_green_px": g,
                         "cell_total_px": total, "cell_r_px": CELL_R_PX})
        if args.overlay_day == day:
            o = img.copy()
            for pid, mask in cm.items():
                cnt, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(o, cnt, -1, (0, 255, 255), 2)
            o[green] = (255, 0, 255)
            out_png = os.path.splitext(args.out)[0] + f"_D{day}.png"
            cv2.imwrite(out_png, o)
            print(f"overlay -> {out_png}")

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows (D{min(frames)}-D{max(frames)}) -> {args.out}")


if __name__ == "__main__":
    main()
