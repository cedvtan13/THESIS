#!/usr/bin/env python3
"""roi_view.py -- fresh camera frame with the pot circles (ROIs), each pot's
counted area and the counted green pixels drawn on it, plus GPR per pot.
Writes /tmp/roi_view.jpg. Writes no data. Used by roi_view.sh on the Mac.
"""
import json
import os
import sys
from datetime import datetime

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import capture_gpr as cg  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/roi_view.jpg"
rois = json.load(open(cg.ROI_FILE if os.path.exists(cg.ROI_FILE) else "pot_rois.json"))["rois"]
f = cg.capture_frame(use_light=False)
g = cg.green_mask(cv2.cvtColor(f, cv2.COLOR_BGR2HSV))
o = f.copy()
o[g > 0] = (255, 0, 255)
cells = cg.cell_masks(f.shape[:2], rois)
for p, m in cells.items():
    cnt, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(o, cnt, -1, (255, 255, 0), 2)
for p, r in rois.items():
    cx, cy, rad = cg.roi_geometry(r)
    cv2.circle(o, (int(cx), int(cy)), int(rad), (0, 255, 255), 3)
    c = int(np.count_nonzero(cv2.bitwise_and(g, g, mask=cells[p])))
    t = int(np.count_nonzero(cells[p]))
    for col, th in (((0, 0, 0), 6), ((255, 255, 255), 2)):
        cv2.putText(o, p, (int(cx) - 45, int(cy) - int(rad) - 14), cv2.FONT_HERSHEY_SIMPLEX, 1.1, col, th)
        cv2.putText(o, f"GPR {100 * c / t:.2f}%", (int(cx) - 70, int(cy) + int(rad) + 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, th)
band = np.full((70, o.shape[1], 3), 30, np.uint8)
cv2.putText(band, f"Pechay GPR  {datetime.now():%Y-%m-%d %H:%M}   yellow = pot circle (ROI)   "
            "cyan = pot area   magenta = counted green", (12, 45),
            cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
cv2.imwrite(out, np.vstack([band, o]), [cv2.IMWRITE_JPEG_QUALITY, 90])
print(f"saved {out}")
