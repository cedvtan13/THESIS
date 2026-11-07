#!/usr/bin/env python3
"""Capture-time test: is a 13:00 or 14:00 photo less glary than the 12:00 one?

Takes one photo with exactly the noon capture's camera settings (locked gain and
white balance, exposure matched to mean V 73), measures every pot the same way as
capture_gpr.py (cell_gpr, raw_gpr) and the same way as glare_check.py (clipped
pixels, brightness relative to the median pot, level). Writes only to its own log:

    ~/thesis/time_test_log.csv
    ~/agrisentry_data/frames/time_test/DXX_YYYY-MM-DD_HHMM.png      (raw, lossless)
    ~/agrisentry_data/frames/time_test/overlay/DXX_HHMM_overlay.jpg (check picture)

It never touches growth_dataset.csv, exposure_log.csv or glare_log.csv.

Also scores today's official noon frame (slot 12:00) the first time it runs each
day, so all three times are measured by the same code.

Cron (13:00 and 14:00, never :30, which belongs to light_log.py):
    0 13,14 * * *  python3 ~/THESIS/Dual_Archi/tools/time_test.py --until 2026-11-09

Summary of the test so far:
    python3 ~/THESIS/Dual_Archi/tools/time_test.py --summary
"""
import argparse
import csv
import glob
import json
import os
import sys
from datetime import date, datetime

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import capture_gpr as cg  # noqa: E402
from glare_check import check, level  # noqa: E402

LOG = os.path.join(cg.BASE, "time_test_log.csv")
OUT_DIR = os.path.join(cg.FRAME_DIR, "time_test")
HEADER = ["date", "slot", "day", "source", "pot_id", "cell_gpr", "raw_gpr", "clip_pct",
          "rel_brightness", "pot_mean_v", "frame_mean_v", "level", "exposure_us",
          "light_index", "frame"]


def load_rois():
    with open(cg.ROI_FILE) as f:
        cfg = json.load(f)
    return cfg.get("rois", cfg)


def day_or_blank():
    try:
        return cg.day_index(True)
    except Exception:
        return ""


def score(frame, path, rois):
    """Per-pot rows: GPR exactly as capture_gpr.py, light exactly as glare_check.py.

    The circles follow the camera first (capture_gpr.aligned_rois), as in the noon capture."""
    rois = cg.aligned_rois(frame, rois, log=False)[0]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    green = cg.green_mask(hsv)
    cells = cg.cell_masks(frame.shape[:2], rois)
    radius = int(round(min(r["w"] for r in rois.values()) / 2.0))
    fmean, light = check(path, rois, radius)
    light = {pid: (clip, mean, rel) for pid, clip, mean, rel in light}
    out = []
    for i in range(1, 10):
        pid = f"P-0{i}"
        area = cg.roi_mask(frame.shape[:2], rois[pid], True)
        tot = int(np.count_nonzero(area))
        raw = cg.masked_count(green, area) / tot * 100.0 if tot else 0.0
        ctot = int(np.count_nonzero(cells[pid]))
        cell = cg.masked_count(green, cells[pid]) / ctot * 100.0 if ctot else 0.0
        clip, mean, rel = light[pid]
        out.append([pid, f"{cell:.2f}", f"{raw:.2f}", f"{clip:.1f}", f"{rel:.2f}",
                    f"{mean:.1f}", f"{fmean:.1f}", level(clip, rel)])
    return out, green, cells


def save_overlay(frame, green, cells, rois, name):
    ov = frame.copy()
    ov[green > 0] = (255, 0, 255)
    for pid, m in cells.items():
        cnt, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(ov, cnt, -1, (0, 255, 255), 2)
        cx, cy, _ = cg.roi_geometry(rois[pid])
        cv2.putText(ov, pid, (int(cx) - 30, int(cy) - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (0, 255, 255), 2)
    od = os.path.join(OUT_DIR, "overlay")
    os.makedirs(od, exist_ok=True)
    p = os.path.join(od, name)
    cv2.imwrite(p, ov, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return p


def append(rows):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HEADER)
        w.writerows(rows)


def logged(date_s, slot):
    if not os.path.exists(LOG):
        return False
    with open(LOG, newline="") as f:
        return any(r["date"] == date_s and r["slot"] == slot for r in csv.DictReader(f))


def noon_exposure(d):
    """Exposure of today's official noon photo, from exposure_log.csv."""
    try:
        with open(cg.EXPOSURE_LOG, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["day"] == str(d)]
        if rows:
            r = rows[-1]
            exp, v = float(r["exposure_us"]), float(r["mean_v"])
            return int(exp), f"{(v / cg.TARGET_MEAN_V) * (1000.0 / (exp / 1000.0)):.1f}"
    except (OSError, KeyError, ValueError):
        pass
    return "", ""


def score_noon(rois, today, d):
    """Score today's official noon frame once, as slot 12:00."""
    if d == "" or logged(today, "12:00"):
        return
    frames = sorted(glob.glob(os.path.join(cg.FRAME_DIR, f"D{d:02d}_{today}_12*.png")))
    if not frames:
        print(f"[time_test] no noon frame for D{d} yet")
        return
    path = frames[-1]
    frame = cv2.imread(path)
    if frame is None:
        return
    rows, _, _ = score(frame, path, rois)
    exp, idx = noon_exposure(d)
    append([[today, "12:00", d, "noon_capture", *r, exp, idx, os.path.basename(path)] for r in rows])
    print(f"[time_test] scored the noon frame {os.path.basename(path)}")


def capture_now(rois, today, d):
    slot = datetime.now().strftime("%H:%M")
    frame = cg.capture_frame(use_light=False)
    exp, v = cg.LAST_EXPOSURE["exposure_us"], cg.LAST_EXPOSURE["mean_v"]
    idx = f"{(v / cg.TARGET_MEAN_V) * (1000.0 / (exp / 1000.0)):.1f}"
    os.makedirs(OUT_DIR, exist_ok=True)
    tag = f"D{d:02d}" if d != "" else "Dxx"
    path = os.path.join(OUT_DIR, f"{tag}_{today}_{slot.replace(':', '')}.png")
    if not cv2.imwrite(path, frame):
        raise SystemExit(f"[time_test] could not save {path}")
    rows, green, cells = score(frame, path, rois)
    append([[today, slot, d, "test_shot", *r, exp, idx, os.path.basename(path)] for r in rows])
    ov = save_overlay(frame, green, cells, cg.aligned_rois(frame, rois, log=False)[0],
                      f"{tag}_{slot.replace(':', '')}_overlay.jpg")
    flagged = [r[0] + " " + r[7] for r in rows if r[7] != "ok"]
    print(f"[time_test] {today} {slot}: exposure {exp} us, light index {idx}, "
          f"flags: {', '.join(flagged) or 'none'}  overlay -> {ov}")


def summary():
    if not os.path.exists(LOG):
        sys.exit("no time_test_log.csv yet")
    with open(LOG, newline="") as f:
        rows = list(csv.DictReader(f))
    shots = {}
    for r in rows:
        shots.setdefault((r["date"], r["slot"]), []).append(r)
    print(f"{'date':10} {'slot':5} {'light':>6} {'flags':>5} {'max rel':>7} {'min rel':>7}  "
          f"{'flagged pots':28} cell_gpr P-01..P-09")
    for (d, s), rs in sorted(shots.items()):
        rel = [float(r["rel_brightness"]) for r in rs]
        flags = [f"{r['pot_id'][-1]}{r['level'][0]}" for r in rs if r["level"] != "ok"]
        gpr = " ".join(f"{float(r['cell_gpr']):.2f}" for r in sorted(rs, key=lambda r: r["pot_id"]))
        print(f"{d:10} {s:5} {r['light_index'] or '-':>6} {len(flags):5d} {max(rel):7.2f} "
              f"{min(rel):7.2f}  {' '.join(flags):28} {gpr}")
    print("\nlight = light index (higher = brighter); flags: pot number + G(LARE) M(ILD) D(ARK);"
          "\nrel = pot brightness / median pot. The evenest light has max rel near 1 and min rel near 1.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--until", help="last date to run (YYYY-MM-DD); later runs exit quietly")
    ap.add_argument("--summary", action="store_true", help="print the comparison so far")
    ap.add_argument("--noon-only", action="store_true", help="only score today's noon frame")
    args = ap.parse_args()
    if args.summary:
        return summary()
    today = date.today().isoformat()
    if args.until and today > args.until:
        return
    rois = load_rois()
    d = day_or_blank()
    score_noon(rois, today, d)
    if not args.noon_only:
        capture_now(rois, today, d)


if __name__ == "__main__":
    main()
