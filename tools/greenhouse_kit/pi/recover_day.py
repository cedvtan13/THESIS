#!/usr/bin/env python3
"""recover_day.py -- add the missing rows of a day whose noon frame was saved.

Runs ON THE PI. For a day that has a saved noon frame in ~/agrisentry_data/frames/
but no rows in growth_dataset.csv (D18 in this run). It measures the frame with
exactly the same code as the noon capture (capture_gpr: HSV mask, 3x3 opening,
pot areas moved with the camera) and takes each pot's soil moisture from the
sm_log.csv reading closest to the frame's time (within 45 minutes).

Nothing is replaced: it refuses if the day already has rows. The CSV is backed
up first. Without --write it only prints what it would add.

    python3 ~/fixkit/recover_day.py --day 18            # preview
    python3 ~/fixkit/recover_day.py --day 18 --write    # add the 9 rows

Record the recovery in the field log afterwards (the script prints the line).
"""
import argparse
import csv
import glob
import json
import os
import shutil
import sys
from datetime import datetime

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.join(HOME, "THESIS", "Dual_Archi"))
import capture_gpr as cg  # noqa: E402
import cv2  # noqa: E402
import numpy as np  # noqa: E402

SM_LOG = os.path.join(HOME, "agrisentry_data", "sm_log.csv")
MAX_SM_GAP_MIN = 45


def nearest_sm(when):
    if not os.path.exists(SM_LOG):
        return None, None
    best, best_gap = None, None
    with open(SM_LOG, newline="") as f:
        for r in csv.DictReader(f):
            try:
                t = datetime.fromisoformat(r["wall_time"])
            except (KeyError, ValueError):
                continue
            gap = abs((t - when).total_seconds()) / 60
            if best_gap is None or gap < best_gap:
                best, best_gap = r, gap
    if best is None or best_gap > MAX_SM_GAP_MIN:
        return None, best_gap
    return best, best_gap


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--day", type=int, required=True)
    ap.add_argument("--frame", help="default: the saved noon frame of that day")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    found = sorted(glob.glob(os.path.join(cg.FRAME_DIR, f"D{args.day:02d}_*.png")))
    path = args.frame or (found[-1] if found else None)
    if not path:
        sys.exit(f"no saved frame for D{args.day} in {cg.FRAME_DIR}")
    name = os.path.basename(path)              # D18_2026-11-15_1200.png
    try:
        stamp_dt = datetime.strptime(name[4:19], "%Y-%m-%d_%H%M")
    except ValueError:
        stamp_dt = datetime.fromtimestamp(os.path.getmtime(path))
    stamp = f"{stamp_dt:%Y-%m-%d %H:%M}"

    with open(cg.OUT_CSV, newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        rows = list(rd)
    col = {h: i for i, h in enumerate(header)}
    if any(r[col["day"]] == str(args.day) for r in rows):
        sys.exit(f"D{args.day} already has rows in {cg.OUT_CSV}; use "
                 "Dual_Archi/tools/remeasure_day.py to re-measure an existing day")

    frame = cv2.imread(path)
    if frame is None:
        sys.exit(f"could not read {path}")
    with open(cg.ROI_FILE) as f:
        cfg = json.load(f)
    rois, dx, dy, conf, applied = cg.aligned_rois(
        frame, cfg.get("rois", cfg), day=args.day, stamp=stamp,
        source=f"recover {name}", log=args.write)
    print(f"frame {name}  ({stamp})  alignment ({dx:+.1f}, {dy:+.1f}) px, "
          f"confidence {conf:.2f}, applied={applied}")
    if not applied:
        sys.exit("alignment not applied (weak match) -- not recovering automatically; "
                 "check the frame by eye first")

    sm_row, gap = nearest_sm(stamp_dt)
    if sm_row is None:
        print(f"WARNING: no sm_log reading within {MAX_SM_GAP_MIN} min of {stamp} "
              f"(closest {gap if gap is None else round(gap)} min) -> sm_pct = NaN")
    else:
        print(f"soil moisture from sm_log at {sm_row['wall_time']} ({gap:.0f} min from the frame)")

    prev = {}
    for r in rows:
        try:
            if int(r[col["day"]]) < args.day:
                prev[r[col["pot_id"]]] = (int(r[col["day"]]), float(r[col["raw_gpr"]]))
        except ValueError:
            pass

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green = cg.green_mask(hsv)
    green_raw = cg.hsv_mask(hsv)
    cells = cg.cell_masks(frame.shape[:2], rois)
    terr_r = (cg.POT_PITCH_MM * cg.PX_PER_MM) / 2.0
    new_rows = []
    for pid in sorted(rois):
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
        sm = sm_row.get(pid) if sm_row else None
        try:
            sm_str = f"{float(sm):.1f}"
        except (TypeError, ValueError):
            sm_str = "NaN"
        vals = {"day": args.day, "timestamp": stamp, "pot_id": pid, "sm_pct": sm_str,
                "raw_gpr": f"{gpr:.2f}", "smooth_gpr": "", "green_px": g, "total_px": tot,
                "flag": flag, "raw_gpr_noopen": f"{(gr / tot * 100.0 if tot else 0.0):.2f}",
                "terr_gpr": f"{(tg / tt * 100.0 if tt else 0.0):.2f}", "terr_green_px": tg,
                "terr_total_px": tt, "canopy_w_px": cw, "canopy_h_px": ch,
                "morph_k": cg.MORPH_K,
                "cell_gpr": f"{(cgreen / ct * 100.0 if ct else 0.0):.2f}",
                "cell_green_px": cgreen, "cell_total_px": ct}
        row = [str(vals.get(h, "")) for h in header]
        new_rows.append(row)
        print(f"  {pid}  sm {sm_str:>5}  raw_gpr {vals['raw_gpr']:>5}  cell_gpr {vals['cell_gpr']:>5}")

    if not args.write:
        print("\n(preview only: nothing written; add --write to add these 9 rows)")
        return
    bak = f"{cg.OUT_CSV}.before_recover_D{args.day}_{datetime.now():%Y%m%d_%H%M}"
    shutil.copy2(cg.OUT_CSV, bak)
    rows.extend(new_rows)
    rows.sort(key=lambda r: (int(r[col["day"]]), r[col["pot_id"]]))
    with open(cg.OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"\nD{args.day}: 9 rows added to {cg.OUT_CSV}\nbackup: {bak}")
    note = (f'{datetime.now():%Y-%m-%d},{args.day},ALL,"D{args.day} ROWS RECOVERED on '
            f'{datetime.now():%b %d}: the noon frame {name} was saved but its rows were never '
            f'written. Measured from the saved frame with the noon-capture code '
            f'(recover_day.py); soil moisture from the sm_log reading at '
            f'{sm_row["wall_time"][11:16] if sm_row else "n/a"}."')
    flog = os.path.join(cg.BASE, "field_log.csv")
    if os.path.exists(flog):
        shutil.copy2(flog, f"{flog}.before_recover_D{args.day}")
        with open(flog, "a") as f:
            f.write(note + "\n")
        print(f"\nfield log updated ({flog}):\n{note}")
    else:
        print(f"\nfield log not found at {flog}; add this line by hand:\n{note}")


if __name__ == "__main__":
    main()
