#!/usr/bin/env python3
"""mask_compare.py -- why are the recent masks smaller? Read-only comparison.

Runs ON THE PI (or on any computer with the frames, pot_rois.json and OpenCV).
For every saved noon frame from D10 on, it measures each pot's cell GPR three ways:

  current  the validated mask used in the thesis (H 38-85, S>=100, V>=55, 3x3 opening)
  twolevel the current mask grown by 1 px into neighbouring pixels with S>=80, V>=55
           (catches leaf edges that dim light pushes just below S=100)
  bright   the current mask after scaling the frame's brightness (V) to the 73 target

and writes, without touching any thesis file:
  ~/fixkit/mask_compare/mask_compare.csv      one row per day and pot
  ~/fixkit/mask_compare/Dxx_pots.jpg          9 pot close-ups per day:
                                              green  = current mask
                                              magenta = extra pixels of 'twolevel'
Bring the whole ~/fixkit/mask_compare folder back for analysis.

    python3 ~/fixkit/mask_compare.py              # D10 to the latest frame
    python3 ~/fixkit/mask_compare.py --from 14
"""
import argparse
import csv
import glob
import json
import os
import sys

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.join(HOME, "THESIS", "Dual_Archi"))
import capture_gpr as cg  # noqa: E402
import cv2  # noqa: E402
import numpy as np  # noqa: E402

OUT = os.path.join(HOME, "fixkit", "mask_compare")
K = np.ones((3, 3), np.uint8)


def thr(hsv, s, v):
    return cv2.inRange(hsv, np.array([cg.HUE_LO, s, v], np.uint8),
                       np.array([cg.HUE_HI, 255, 255], np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, default=10)
    ap.add_argument("--frames", default=cg.FRAME_DIR)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    with open(cg.ROI_FILE) as f:
        cfg = json.load(f)
    base_rois = cfg.get("rois", cfg)

    rows = []
    for path in sorted(glob.glob(os.path.join(args.frames, "D*_*.png"))):
        name = os.path.basename(path)
        try:
            day = int(name[1:3])
        except ValueError:
            continue
        if day < args.start:
            continue
        frame = cv2.imread(path)
        if frame is None:
            continue
        rois, dx, dy, conf, applied = cg.aligned_rois(frame, base_rois, day=day,
                                                      source="mask_compare", log=False)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mean_v = float(hsv[..., 2].mean())
        cur = cv2.morphologyEx(thr(hsv, cg.SAT_MIN, cg.VAL_MIN), cv2.MORPH_OPEN, K)
        weak = thr(hsv, 80, cg.VAL_MIN)
        two = cv2.dilate(cur, K) & weak | cur
        hb = hsv.copy()
        hb[..., 2] = np.clip(hsv[..., 2].astype(np.float32) * (73.0 / max(mean_v, 1)), 0, 255).astype(np.uint8)
        bri = cv2.morphologyEx(thr(hb, cg.SAT_MIN, cg.VAL_MIN), cv2.MORPH_OPEN, K)
        cells = cg.cell_masks(frame.shape[:2], rois)
        tiles = []
        for pid in sorted(rois):
            c = cells[pid] > 0
            tot = int(c.sum())
            gc, gt, gb = (int((m > 0)[c].sum()) for m in (cur, two, bri))
            pot = c
            leaf_s = hsv[..., 1][(cur > 0) & pot]
            leaf_v = hsv[..., 2][(cur > 0) & pot]
            rows.append({"day": day, "frame": name, "pot_id": pid, "frame_mean_v": f"{mean_v:.1f}",
                         "align_conf": f"{conf:.2f}", "cell_px": tot,
                         "gpr_current": f"{gc / tot * 100:.3f}", "gpr_twolevel": f"{gt / tot * 100:.3f}",
                         "gpr_bright": f"{gb / tot * 100:.3f}",
                         "leaf_median_S": int(np.median(leaf_s)) if leaf_s.size else "",
                         "leaf_median_V": int(np.median(leaf_v)) if leaf_v.size else ""})
            cx, cy, _ = cg.roi_geometry(rois[pid])
            r = int(cg.CELL_R_PX)
            x0, y0 = max(0, int(cx) - r), max(0, int(cy) - r)
            x1, y1 = min(frame.shape[1], int(cx) + r), min(frame.shape[0], int(cy) + r)
            crop = frame[y0:y1, x0:x1].copy()
            sub_c = cur[y0:y1, x0:x1] > 0
            sub_x = (two[y0:y1, x0:x1] > 0) & ~sub_c
            crop[sub_x] = (255, 0, 255)
            crop[sub_c] = (0, 220, 0)
            crop = cv2.resize(crop, (300, 300), interpolation=cv2.INTER_NEAREST)
            cv2.putText(crop, f"D{day} {pid} {gc / tot * 100:.2f}%", (6, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            tiles.append(crop)
        while len(tiles) < 9:
            tiles.append(np.zeros((300, 300, 3), np.uint8))
        grid = np.vstack([np.hstack(tiles[i:i + 3]) for i in (0, 3, 6)])
        cv2.imwrite(os.path.join(OUT, f"D{day:02d}_pots.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"D{day}: mean V {mean_v:.1f}, align conf {conf:.2f}, "
              f"current {np.mean([float(x['gpr_current']) for x in rows if x['day'] == day]):.3f} %, "
              f"twolevel {np.mean([float(x['gpr_twolevel']) for x in rows if x['day'] == day]):.3f} %")
    if rows:
        with open(os.path.join(OUT, "mask_compare.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\nwritten to {OUT}/  (mask_compare.csv and Dxx_pots.jpg)")
    else:
        print("no frames found")


if __name__ == "__main__":
    main()
