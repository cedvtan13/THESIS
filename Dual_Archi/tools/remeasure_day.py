#!/usr/bin/env python3
"""remeasure_day.py -- re-measure one day's GPR from its saved noon frame.

For a day whose pot circles were off because the camera moved. Recomputes every
GPR column from the saved lossless frame with the circles moved to follow the
camera (capture_gpr.aligned_rois). Keeps the day, the original timestamp, the pot
and the soil moisture read at capture time. Only that day's rows change, in place.
The whole CSV is backed up first, and the change is printed pot by pot.

    python3 tools/remeasure_day.py --day 10                 # show old vs new, change nothing
    python3 tools/remeasure_day.py --day 10 --write         # replace that day's rows
"""
import argparse
import csv
import glob
import json
import os
import shutil
import sys
from datetime import datetime

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import capture_gpr as cg  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--day", type=int, required=True)
    ap.add_argument("--frame", help="default: the saved noon frame of that day")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    path = args.frame or (sorted(glob.glob(os.path.join(cg.FRAME_DIR, f"D{args.day:02d}_*.png"))) or [None])[-1]
    if not path:
        sys.exit(f"no saved frame for D{args.day}")
    frame = cv2.imread(path)
    with open(cg.ROI_FILE) as f:
        cfg = json.load(f)
    rois, dx, dy, conf, applied = cg.aligned_rois(frame, cfg["rois"], day=args.day,
                                                  source=f"remeasure {os.path.basename(path)}",
                                                  log=args.write)
    if not applied:
        sys.exit("alignment not applied (weak match) -- not re-measuring")

    with open(cg.OUT_CSV, newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        rows = list(rd)
    col = {h: i for i, h in enumerate(header)}
    day_rows = [r for r in rows if r[col["day"]] == str(args.day)]
    if len(day_rows) != 9:
        sys.exit(f"expected 9 rows for D{args.day}, found {len(day_rows)}")

    # previous raw_gpr per pot (days before this one) for the anomaly flag
    prev = {}
    for r in rows:
        if int(r[col["day"]]) < args.day:
            prev[r[col["pot_id"]]] = (int(r[col["day"]]), float(r[col["raw_gpr"]]))

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green = cg.green_mask(hsv)
    green_raw = cg.hsv_mask(hsv)
    cells = cg.cell_masks(frame.shape[:2], rois)
    terr_r = (cg.POT_PITCH_MM * cg.PX_PER_MM) / 2.0
    new = {}
    for r in day_rows:
        pid = r[col["pot_id"]]
        roi = rois[pid]
        cx, cy, _ = cg.roi_geometry(roi)
        area = cg.roi_mask(frame.shape[:2], roi, True)
        tot = int(np.count_nonzero(area))
        g = cg.masked_count(green, area)
        gr = cg.masked_count(green_raw, area)
        cw, ch = cg.canopy_bbox(green, area)
        ta = cg.circle_mask(frame.shape[:2], cx, cy, terr_r)
        tt, tg = int(np.count_nonzero(ta)), cg.masked_count(green, ta)
        ct, cgreen = int(np.count_nonzero(cells[pid])), cg.masked_count(green, cells[pid])
        gpr = g / tot * 100.0 if tot else 0.0
        flag = 0
        if pid in prev:
            pday, pg = prev[pid]
            if abs(gpr - pg) > cg.ANOMALY_DELTA_PER_DAY * max(1, args.day - pday):
                flag = 1
        vals = {"raw_gpr": f"{gpr:.2f}", "green_px": g, "total_px": tot, "flag": flag,
                "raw_gpr_noopen": f"{(gr / tot * 100.0 if tot else 0.0):.2f}",
                "terr_gpr": f"{(tg / tt * 100.0 if tt else 0.0):.2f}", "terr_green_px": tg,
                "terr_total_px": tt, "canopy_w_px": cw, "canopy_h_px": ch,
                "cell_gpr": f"{(cgreen / ct * 100.0 if ct else 0.0):.2f}",
                "cell_green_px": cgreen, "cell_total_px": ct}
        new[pid] = vals
        print(f"{pid}  raw_gpr {r[col['raw_gpr']]:>5} -> {vals['raw_gpr']:>5}   "
              f"cell_gpr {r[col['cell_gpr']]:>5} -> {vals['cell_gpr']:>5}")

    if not args.write:
        print("\n(dry run: nothing written; add --write to replace the rows)")
        return
    bak = f"{cg.OUT_CSV}.before_remeasure_D{args.day}_{datetime.now():%Y%m%d_%H%M}"
    shutil.copy2(cg.OUT_CSV, bak)
    for r in rows:
        if r[col["day"]] == str(args.day):
            for k, v in new[r[col["pot_id"]]].items():
                r[col[k]] = str(v)
    with open(cg.OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"\nD{args.day} rows replaced in {cg.OUT_CSV}\nbackup: {bak}")


if __name__ == "__main__":
    main()
