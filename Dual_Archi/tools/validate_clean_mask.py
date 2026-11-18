#!/usr/bin/env python3
"""validate_clean_mask.py -- score the clean mask (and each of its steps) against
the hand labels, exactly the way `gpr_validate.py score` scores the original mask.

Ground truth: GPR_VALIDATION/labels_Cedric.json + labels_Kent_v2.json
(run 1, D12 = 2026-10-17 and D13 = 2026-10-18, 9 pots each, two independent
annotators = 36 pot-images). Pot circles: pot_rois_before_20261021.json (the
circles in use on those days, r = 85 px); labels are clipped to them.

Read-only: writes only the --out CSV. Needs opencv + numpy.

    cd Dual_Archi
    python3 tools/validate_clean_mask.py --frames-dir ../framesss \
        --out ../GPR_VALIDATION/results_clean_mask_D12_D13_leafonly.csv
    python3 tools/validate_clean_mask.py --frames-dir ../framesss --plants \
        --out ../GPR_VALIDATION/results_clean_mask_D12_D13_plants.csv

The first line of output ("original") must equal the committed validation
(IoU 0.630, bias +0.044 pp, MAE 0.281 pp, leaf-only); if it does not, the
setup is wrong and the other numbers mean nothing.
"""
import argparse
import csv
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DUAL = os.path.dirname(HERE)
REPO = os.path.dirname(DUAL)
sys.path.insert(0, HERE)
sys.path.insert(0, DUAL)
import capture_gpr as cg  # noqa: E402
import gpr_validate as gv  # noqa: E402

LABELS = [os.path.join(REPO, "GPR_VALIDATION", "labels_Cedric.json"),
          os.path.join(REPO, "GPR_VALIDATION", "labels_Kent_v2.json")]
ROIS = os.path.join(DUAL, "pot_rois_before_20261021.json")


def thr(hsv, h_lo, s_min, v_min, h_hi):
    return cv2.inRange(hsv, np.array([h_lo, s_min, v_min], np.uint8),
                       np.array([h_hi, 255, 255], np.uint8))


def wb_core(frame):
    """Clean mask step 1: sunny-reference white balance, clean HSV band, 3x3 opening."""
    hsv = cv2.cvtColor(cg.sunny_wb_bgr(frame), cv2.COLOR_BGR2HSV)
    core = cv2.morphologyEx(thr(hsv, cg.CLEAN_HUE_LO, cg.CLEAN_SAT_MIN, cg.CLEAN_VAL_MIN,
                                cg.CLEAN_HUE_HI), cv2.MORPH_OPEN, cg.MORPH_KERNEL)
    return hsv, core


def inner_disc(shape, rois, r_inner):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    inner = np.zeros((h, w), bool)
    for r in rois.values():
        cx, cy, _ = cg.roi_geometry(r)
        inner |= ((xx - cx) ** 2 + (yy - cy) ** 2) <= r_inner ** 2
    return inner


def blob_filter(core, inner):
    """Clean mask step 2: keep blobs >= MIN_BLOB_AREA that touch the inner disc, clip to it."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(core, connectivity=8)
    keep = np.zeros(n, bool)
    keep[np.unique(lab[inner & (core > 0)])] = True
    keep[0] = False
    keep &= st[:, cv2.CC_STAT_AREA] >= cg.MIN_BLOB_AREA
    return keep[lab] & inner


def edge_recovery(hsv, core):
    """Clean mask step 3: add weak-threshold pixels within 1 px of the core."""
    weak = thr(hsv, cg.WEAK_HUE_LO, cg.WEAK_SAT_MIN, cg.WEAK_VAL_MIN, cg.WEAK_HUE_HI) > 0
    dil = cv2.dilate(core.astype(np.uint8), cg.MORPH_KERNEL) > 0
    return (core > 0) | (dil & weak)


def full_clean(frame, rois, r_inner):
    old = cg.POT_INNER_R_PX
    cg.POT_INNER_R_PX = r_inner
    try:
        return cg.clean_green_mask(frame, rois)[0] > 0    # the deployed function itself
    finally:
        cg.POT_INNER_R_PX = old


def variants(rois):
    return [
        ("original (validated, main track)",
         lambda f: cg.green_mask(cv2.cvtColor(f, cv2.COLOR_BGR2HSV)) > 0),
        ("step 1: sunny WB only", lambda f: wb_core(f)[1] > 0),
        ("step 1+2: WB + blob filter (r=68)",
         lambda f: blob_filter(wb_core(f)[1], inner_disc(f.shape[:2], rois, 68.0))),
        ("step 1+3: WB + edge recovery", lambda f: edge_recovery(*wb_core(f))),
        ("full clean, as deployed (r=68)", lambda f: full_clean(f, rois, 68.0)),
        ("full clean, no inner limit (r=85)", lambda f: full_clean(f, rois, 85.0)),
    ]


def summarise(rs):
    ga = np.array([r["gpr_auto"] for r in rs])
    gm = np.array([r["gpr_manual"] for r in rs])
    d = ga - gm
    tp = sum(r["tp"] for r in rs); fp = sum(r["fp"] for r in rs); fn = sum(r["fn"] for r in rs)
    sd = float(np.std(d, ddof=1))
    return {"n": len(rs), "precision": tp / (tp + fp), "recall": tp / (tp + fn),
            "iou": float(np.nanmean([r["iou"] for r in rs])),
            "mae": float(np.mean(np.abs(d))), "bias": float(np.mean(d)),
            "r": float(np.corrcoef(ga, gm)[0, 1]),
            "ba_lo": float(np.mean(d) - 1.96 * sd), "ba_hi": float(np.mean(d) + 1.96 * sd)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plants", action="store_true",
                    help="score whole-plant labels (default: leaf blades, stems removed, "
                         "as in the committed validation)")
    a = ap.parse_args()

    rois, _ = gv.load_rois(ROIS)
    raw = gv.load_labels(LABELS)
    labels = {}
    for who, lab in raw.items():           # same label prep as gpr_validate.py score
        labels[who] = {}
        for key, man in lab.items():
            man = man & gv.roi_circle_local(gv.roi_for(rois, key))
            if not a.plants:
                man = cv2.morphologyEx(man.astype(np.uint8), cv2.MORPH_OPEN,
                                       np.ones((3, 3), np.uint8)) > 0
            labels[who][key] = man
    names = sorted({k[0] for lab in labels.values() for k in lab})
    frames = {}
    for n in names:
        img = cv2.imread(os.path.join(a.frames_dir, n))
        if img is None:
            sys.exit(f"frame {n} not found in {a.frames_dir}")
        frames[n] = img
        med = np.median(img.reshape(-1, 3), axis=0)
        print(f"{n}: blue/red {med[0] / max(med[2], 1):.2f}")
    print("labels: " + ("whole plants" if a.plants else "leaf blades (thin stems removed)")
          + f", {len(labels)} annotators\n")

    rows = []
    hdr = f"{'mask':36s} {'frame':5s} {'IoU':>6s} {'prec':>5s} {'rec':>5s} {'bias pp':>8s} {'MAE pp':>7s} {'r':>6s}  BA 95% (pp)"
    print(hdr)
    print("-" * len(hdr))
    for name, fn in variants(rois):
        masks = {n: fn(img) for n, img in frames.items()}
        rs = []
        for who, lab in sorted(labels.items()):
            for (f, pot), man in sorted(lab.items()):
                roi = gv.roi_for(rois, (f, pot))
                circ = gv.roi_circle_local(roi)
                auto = gv.crop(masks[f], roi) & circ
                area = int(circ.sum())
                tp, fp, fn_, prec, rec, iou, dice = gv.seg_metrics(auto, man)
                rs.append({"mask": name, "annotator": who, "frame": f, "pot": pot,
                           "roi_px": area, "auto_px": int(auto.sum()), "manual_px": int(man.sum()),
                           "gpr_auto": 100 * auto.sum() / area, "gpr_manual": 100 * man.sum() / area,
                           "tp": tp, "fp": fp, "fn": fn_, "precision": prec, "recall": rec,
                           "iou": iou, "dice": dice})
        rows += rs
        for label, sub in [(n[:3], [r for r in rs if r["frame"] == n]) for n in names] + [("ALL", rs)]:
            s = summarise(sub)
            print(f"{name:36s} {label:5s} {s['iou']:6.3f} {s['precision']:5.2f} {s['recall']:5.2f} "
                  f"{s['bias']:+8.3f} {s['mae']:7.3f} {s['r']:6.3f}  {s['ba_lo']:+.2f} to {s['ba_hi']:+.2f}")
        print()

    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    print(f"per-pot table -> {a.out}")


if __name__ == "__main__":
    main()
