#!/usr/bin/env python3
import json, cv2, numpy as np

img = cv2.imread('/home/crk/roi_alignment_debug.png')
if img is None:
    raise SystemExit("Missing /home/crk/roi_alignment_debug.png")

with open('/home/crk/THESIS/Dual_Archi/pot_rois.json') as f:
    cfg = json.load(f)
rois = cfg.get("rois", cfg)

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

print("--- HSV CALIBRATION ANALYSIS ---")
for pid in ["P-07", "P-04", "P-05"]:
    r = rois[pid]
    cx, cy = int(r["x"] + r["w"]/2), int(r["y"] + r["h"]/2)
    rad = int(min(r["w"], r["h"])/2)
    
    mask = np.zeros(hsv.shape[:2], np.uint8)
    cv2.circle(mask, (cx, cy), rad, 255, -1)
    
    pts = hsv[mask == 255]
    h, s, v = pts[:,0], pts[:,1], pts[:,2]
    
    print(f"\n[{pid}] Soil & Canopy Pixels ({len(pts)} total):")
    print(f"  Hue:        min={h.min():3d}, p25={int(np.percentile(h,25)):3d}, median={int(np.median(h)):3d}, max={h.max():3d}")
    print(f"  Saturation: min={s.min():3d}, p25={int(np.percentile(s,25)):3d}, median={int(np.median(s)):3d}, max={s.max():3d}")
    print(f"  Value:      min={v.min():3d}, p25={int(np.percentile(v,25)):3d}, median={int(np.median(v)):3d}, max={v.max():3d}")

# Test candidate thresholds across all 9 pots
for s_min, v_min in [(70, 50), (80, 55), (90, 60), (100, 65)]:
    m = cv2.inRange(hsv, np.array([35, s_min, v_min]), np.array([85, 255, 255]))
    kernel = np.ones((3, 3), np.uint8)
    m_open = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel)
    
    pot_pcts = []
    for pid, r in rois.items():
        cx, cy = int(r["x"] + r["w"]/2), int(r["y"] + r["h"]/2)
        rad = int(min(r["w"], r["h"])/2)
        pmask = np.zeros(hsv.shape[:2], np.uint8)
        cv2.circle(pmask, (cx, cy), rad, 255, -1)
        tot = np.count_nonzero(pmask)
        grn = np.count_nonzero(cv2.bitwise_and(m_open, m_open, mask=pmask))
        pot_pcts.append(round(grn / tot * 100, 2))
    print(f"\nTested H(35-85) S>{s_min} V>{v_min} -> GPR across pots: {pot_pcts}")
