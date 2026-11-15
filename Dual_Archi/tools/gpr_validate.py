#!/usr/bin/env python3
"""
gpr_validate.py -- prove the GPR mask is correct against human ground truth.

The adviser's question: "how do we know the GPR we get is correct?"  Answer:
people hand-paint the leaf pixels in each pot of saved noon frames WITHOUT
seeing the automatic mask, then this script compares the HSV mask against
those hand labels pixel by pixel.

    export   frames -> one self-contained annotate.html (open in any browser,
             paint leaves, press "Download labels")
    score    labels JSON(s) -> per-pot precision / recall / IoU / Dice,
             GPR(auto) vs GPR(manual), MAE, bias, Pearson r, Bland-Altman
             limits, and inter-annotator agreement when 2+ people labelled.

The automatic mask is recomputed exactly as capture_gpr.py does it (same HSV
band, same full-frame 3x3 opening, same circular ROI), so the numbers apply
to the dataset as logged.

USAGE (Mac or Pi; needs opencv + numpy)
    python3 tools/gpr_validate.py export FRAME.png [FRAME.png ...] --out val/
    python3 tools/gpr_validate.py score val/labels_*.json --frames-dir FRAMES/
    python3 tools/gpr_validate.py score ... --leaf-only   # leaf blades only

Frames live on the Pi in ~/agrisentry_data/frames/ (copied to the Mac by
./sync_pi.sh pull into _pi_data/agrisentry_data/frames/).
"""

import argparse
import base64
import csv
import json
import math
import os
import sys
from itertools import combinations

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DUAL = os.path.dirname(HERE)
sys.path.insert(0, DUAL)
import capture_gpr as cg  # noqa: E402  (same mask code as the live pipeline)

ROI_FILE = os.path.join(DUAL, "pot_rois.json")
TEMPLATE = os.path.join(HERE, "gpr_annotate_template.html")


def load_rois(path):
    with open(path) as f:
        cfg = json.load(f)
    return cfg["rois"], cfg.get("circular", True)


def roi_circle_local(roi):
    """ROI circle inside its own w x h crop, as a 0/1 array."""
    cx, cy, r = cg.roi_geometry(roi)
    m = cg.circle_mask((roi["h"], roi["w"]), cx - roi["x"], cy - roi["y"], r)
    return m > 0


def crop(a, roi):
    return a[roi["y"]:roi["y"] + roi["h"], roi["x"]:roi["x"] + roi["w"]]


# ---------------------------------------------------------------- export
def cmd_export(args):
    rois, _ = load_rois(args.roi_file)
    items = []
    for path in args.frames:
        img = cv2.imread(path)
        if img is None:
            sys.exit(f"cannot read {path}")
        # Move the circles with the camera, exactly as capture_gpr.py did for this
        # frame, so each crop is the pot area the dataset measured. The crop's
        # position is saved with the labels, and score uses that same position.
        frois = rois if args.no_align else cg.aligned_rois(img, rois, log=False)[0]
        for pid in sorted(frois):
            roi = frois[pid]
            ok, png = cv2.imencode(".png", crop(img, roi))
            cx, cy, r = cg.roi_geometry(roi)
            items.append({
                "frame": os.path.basename(path), "pot": pid,
                "x": roi["x"], "y": roi["y"], "w": roi["w"], "h": roi["h"],
                "cx": cx - roi["x"], "cy": cy - roi["y"], "r": r,
                "img": "data:image/png;base64," + base64.b64encode(png).decode(),
            })
    with open(TEMPLATE) as f:
        html = f.read().replace("/*__ITEMS__*/[]", json.dumps(items))
    os.makedirs(args.out, exist_ok=True)
    out = os.path.join(args.out, "annotate.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"{len(items)} pot crops from {len(args.frames)} frame(s) -> {out}")
    print("Each annotator: open it, paint every leaf pixel, Download labels.")


# ---------------------------------------------------------------- score
def rle_decode(rle, n):
    out = np.zeros(n, np.uint8)
    pos, val = 0, 0
    for run in rle:
        if val:
            out[pos:pos + run] = 1
        pos += run
        val ^= 1
    return out


POS = {}   # (frame, pot) -> (x, y) of the crop the labeller painted


def roi_for(rois, key):
    """The ROI as exported for that crop; the fixed ROI file for older labels (run 1)."""
    r = dict(rois[key[1]])
    if key in POS:
        r["x"], r["y"] = POS[key]
    return r


def load_labels(paths):
    """{annotator: {(frame, pot): bool array}}"""
    by = {}
    for p in paths:
        with open(p) as f:
            d = json.load(f)
        who = d.get("annotator") or os.path.basename(p)
        lab = by.setdefault(who, {})
        for it in d["items"]:
            if not it.get("done"):
                continue
            m = rle_decode(it["rle"], it["w"] * it["h"]).reshape(it["h"], it["w"])
            lab[(it["frame"], it["pot"])] = m.astype(bool)
            if "x" in it:   # crop position saved at export (aligned circles)
                POS[(it["frame"], it["pot"])] = (it["x"], it["y"])
    return by


def seg_metrics(auto, man):
    tp = int(np.sum(auto & man))
    fp = int(np.sum(auto & ~man))
    fn = int(np.sum(~auto & man))
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    iou = tp / (tp + fp + fn) if tp + fp + fn else float("nan")
    dice = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
    return tp, fp, fn, prec, rec, iou, dice


def pearson(x, y):
    if len(x) < 3:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def cmd_score(args):
    rois, _ = load_rois(args.roi_file)
    raw_labels = load_labels(args.labels)
    if not raw_labels:
        sys.exit("no finished labels in those files")
    # Clip to the ROI circle, and in --leaf-only mode drop 1-2 px wide stems
    # (GPR measures leaf cover). Done once here so the program-vs-human AND the
    # human-vs-human comparisons use the same definition of "leaf".
    labels = {}
    for who, lab in raw_labels.items():
        labels[who] = {}
        for key, man in lab.items():
            man = man & roi_circle_local(roi_for(rois, key))
            if args.leaf_only:
                man = cv2.morphologyEx(man.astype(np.uint8), cv2.MORPH_OPEN,
                                       np.ones((3, 3), np.uint8)) > 0
            labels[who][key] = man
    auto_cache = {}

    def auto_mask(frame):
        if frame not in auto_cache:
            img = cv2.imread(os.path.join(args.frames_dir, frame))
            if img is None:
                sys.exit(f"frame {frame} not found in {args.frames_dir}")
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            auto_cache[frame] = cg.green_mask(hsv) > 0   # full-frame opening
        return auto_cache[frame]

    rows = []
    for who, lab in sorted(labels.items()):
        for (frame, pot), man in sorted(lab.items()):
            roi = roi_for(rois, (frame, pot))
            circ = roi_circle_local(roi)
            auto = crop(auto_mask(frame), roi) & circ
            area = int(circ.sum())
            tp, fp, fn, prec, rec, iou, dice = seg_metrics(auto, man)
            rows.append({
                "annotator": who, "frame": frame, "pot": pot,
                "roi_px": area, "auto_px": int(auto.sum()), "manual_px": int(man.sum()),
                "gpr_auto": 100 * auto.sum() / area, "gpr_manual": 100 * man.sum() / area,
                "tp": tp, "fp": fp, "fn": fn,
                "precision": prec, "recall": rec, "iou": iou, "dice": dice,
            })

    out_csv = args.out
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

    def summary(rs, title):
        ga = np.array([r["gpr_auto"] for r in rs])
        gm = np.array([r["gpr_manual"] for r in rs])
        d = ga - gm
        tp = sum(r["tp"] for r in rs); fp = sum(r["fp"] for r in rs); fn = sum(r["fn"] for r in rs)
        sd = float(np.std(d, ddof=1)) if len(d) > 1 else float("nan")
        print(f"\n{title}  (n = {len(rs)} pot-images)")
        print(f"  pixel precision {tp/(tp+fp):.3f}   recall {tp/(tp+fn):.3f}   "
              f"IoU {tp/(tp+fp+fn):.3f}   Dice {2*tp/(2*tp+fp+fn):.3f}   (pooled)")
        print(f"  mean per-pot IoU {np.nanmean([r['iou'] for r in rs]):.3f}")
        print(f"  GPR auto vs manual: MAE {np.mean(np.abs(d)):.3f} pp   bias {np.mean(d):+.3f} pp   "
              f"Pearson r {pearson(ga, gm):.3f}")
        print(f"  Bland-Altman 95% limits: {np.mean(d) - 1.96*sd:+.3f} to {np.mean(d) + 1.96*sd:+.3f} pp")
        rel = np.abs(d) / np.where(gm > 0, gm, np.nan)
        print(f"  mean relative GPR error {100*np.nanmean(rel):.1f} %")

    print("GPR VALIDATION -- automatic HSV mask vs hand-labelled "
          + ("leaf blades (thin stems removed from the labels)" if args.leaf_only else "plants"))
    summary(rows, "ALL ANNOTATORS")
    if len(labels) > 1:
        for who in sorted(labels):
            summary([r for r in rows if r["annotator"] == who], f"annotator: {who}")
        print("\nINTER-ANNOTATOR AGREEMENT (how consistent the human ground truth is)")
        for a, b in combinations(sorted(labels), 2):
            common = sorted(set(labels[a]) & set(labels[b]))
            ious, dg = [], []
            for key in common:
                circ = roi_circle_local(roi_for(rois, key))
                ma, mb = labels[a][key], labels[b][key]
                ious.append(seg_metrics(ma, mb)[5])
                dg.append(100 * abs(int(ma.sum()) - int(mb.sum())) / circ.sum())
            if common:
                print(f"  {a} vs {b}: n={len(common)}  mean IoU {np.nanmean(ious):.3f}  "
                      f"mean |dGPR| {np.mean(dg):.3f} pp")
                # Independence check: one person editing another's saved labels
                # leaves a near-perfect subset and pixel-identical images.
                R = raw_labels   # as drawn, before any stem removal
                same = sum(bool((R[a][k] == R[b][k]).all()) for k in common)
                for x, y in ((a, b), (b, a)):
                    px = sum(int(R[x][k].sum()) for k in common)
                    out = sum(int((R[x][k] & ~R[y][k]).sum()) for k in common)
                    if px and out / px < 0.02:
                        print(f"  WARNING: {100 * (1 - out / px):.1f}% of {x}'s pixels lie inside "
                              f"{y}'s labels ({same} image(s) identical) -- {x} probably "
                              f"edited {y}'s labels; this pair is NOT independent")
    print(f"\nper-pot table -> {out_csv}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--roi-file", default=ROI_FILE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("frames", nargs="+")
    e.add_argument("--out", default="gpr_validation")
    e.add_argument("--no-align", action="store_true",
                   help="use pot_rois.json as is (frames from before the camera alignment, run 1)")
    s = sub.add_parser("score")
    s.add_argument("labels", nargs="+")
    s.add_argument("--frames-dir", required=True)
    s.add_argument("--out", default="gpr_validation.csv")
    s.add_argument("--leaf-only", action="store_true",
                   help="remove 1-2 px wide stems from the hand labels (3x3 opening, "
                        "the same kernel the pipeline uses) before scoring")
    args = ap.parse_args()
    {"export": cmd_export, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
