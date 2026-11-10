#!/usr/bin/env python3
"""gpr_view.py -- SEE what the GPR algorithm measures.

The noon frame itself is never stored (storage autonomy), so this takes a fresh
frame with the exact same locked camera settings, runs the exact same mask
(capture_gpr.green_mask, same ROIs), and draws:

  top     the whole bed: counted plant pixels in MAGENTA, speckle removed by the
          3x3 opening in YELLOW, pot circles in cyan with today's GPR
  bottom  every pot close-up, laid out like the bed: photo | what was counted

Writes NO data. Usually run from the Mac with ./gpr_view.sh (photo lands on the
Mac desktop and opens).

    python3 gpr_view.py [--out /tmp/gpr_view.png] [--image some_frame.png]
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime

import cv2
import numpy as np

DUAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DUAL)
import capture_gpr as c  # noqa: E402

TILE = 216          # px per half-tile (photo / mask)
CROP_PAD = 1.35     # crop = pot circle diameter x this


def todays_rows():
    """{pot_id: raw_gpr} from today's noon row, if it exists."""
    out = {}
    try:
        with open(c.OUT_CSV, newline="") as f:
            for r in csv.DictReader(f):
                if r["timestamp"].startswith(datetime.now().strftime("%Y-%m-%d")):
                    out[r["pot_id"]] = r["raw_gpr"]
    except (OSError, KeyError):
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/gpr_view.png")
    ap.add_argument("--image", help="use a saved frame instead of the camera")
    args = ap.parse_args()

    cfg = json.load(open(c.ROI_FILE))
    rois, circular = cfg["rois"], bool(cfg.get("circular", True))
    if args.image:
        frame = cv2.imread(args.image)
    else:
        frame = c.capture_frame(use_light=c.USE_CAPTURE_LIGHT)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    counted = c.green_mask(hsv)                    # what GPR counts
    raw = c.hsv_mask(hsv)                          # before the 3x3 opening
    removed = cv2.bitwise_and(raw, cv2.bitwise_not(counted))
    noon = todays_rows()

    # ---- top: whole bed ----
    top = frame.copy()
    top[removed > 0] = (0, 255, 255)               # yellow: speckle the opening removed
    top[counted > 0] = (255, 0, 255)               # magenta: counted as plant
    stats = {}
    for pid, roi in sorted(rois.items()):
        cx, cy, r = c.roi_geometry(roi)
        area = c.roi_mask(frame.shape[:2], roi, circular)
        g, tot = c.masked_count(counted, area), int(np.count_nonzero(area))
        stats[pid] = (g, tot, g / tot * 100 if tot else 0.0)
        cv2.circle(top, (int(cx), int(cy)), int(r), (255, 255, 0), 2)
        cv2.putText(top, f"{pid} {stats[pid][2]:.2f}%", (int(cx - r), int(cy - r) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    W = top.shape[1]
    hdr = np.zeros((70, W, 3), np.uint8)
    cv2.putText(hdr, f"GPR view  {datetime.now():%Y-%m-%d %H:%M}   D={c.day_index(True)}   "
                f"exposure locked, same ROIs + mask as the noon capture",
                (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    cv2.putText(hdr, "MAGENTA = counted as plant    YELLOW = specks removed by 3x3 opening    "
                "CYAN = pot ROI", (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # ---- bottom: per-pot close-ups in bed layout (rows by y, columns by x) ----
    order = sorted(rois, key=lambda p: rois[p]["y"])
    rows = [sorted(order[i:i + 3], key=lambda p: rois[p]["x"]) for i in range(0, 9, 3)]
    tile_w, tile_h = W // 3, TILE + 34
    grid = np.full((tile_h * 3, W, 3), 25, np.uint8)
    for ri, row in enumerate(rows):
        for ci, pid in enumerate(row):
            cx, cy, r = c.roi_geometry(rois[pid])
            half = int(r * CROP_PAD)
            x0, y0 = max(0, int(cx - half)), max(0, int(cy - half))
            x1, y1 = min(W, int(cx + half)), min(frame.shape[0], int(cy + half))
            photo = cv2.resize(frame[y0:y1, x0:x1], (TILE, TILE), interpolation=cv2.INTER_NEAREST)
            mk = frame[y0:y1, x0:x1].copy() // 3                       # dimmed background
            area = c.roi_mask(frame.shape[:2], rois[pid], circular)[y0:y1, x0:x1]
            mk[(counted[y0:y1, x0:x1] > 0) & (area > 0)] = (255, 0, 255)
            mk[(removed[y0:y1, x0:x1] > 0) & (area > 0)] = (0, 255, 255)
            mk = cv2.resize(mk, (TILE, TILE), interpolation=cv2.INTER_NEAREST)
            sc = TILE / (x1 - x0)
            cv2.circle(mk, (int((cx - x0) * sc), int((cy - y0) * sc)), int(r * sc), (255, 255, 0), 1)
            ox, oy = ci * tile_w + (tile_w - 2 * TILE) // 2, ri * tile_h + 30
            grid[oy:oy + TILE, ox:ox + TILE] = photo
            grid[oy:oy + TILE, ox + TILE:ox + 2 * TILE] = mk
            g, tot, gpr = stats[pid]
            label = f"{pid}  now {gpr:.2f}%  ({g} px)"
            if pid in noon:
                label += f"   noon {noon[pid]}%"
            cv2.putText(grid, label, (ox, oy - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    out = np.vstack([hdr, top, grid])
    cv2.imwrite(args.out, out)
    print(f"[gpr_view] {args.out}")
    for pid in sorted(stats):
        g, tot, gpr = stats[pid]
        print(f"  {pid}: now {gpr:5.2f}%  ({g:4d}/{tot} px)" + (f"   noon {noon[pid]}%" if pid in noon else ""))


if __name__ == "__main__":
    main()
