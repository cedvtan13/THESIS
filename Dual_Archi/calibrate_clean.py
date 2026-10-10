#!/usr/bin/env python3
import json, cv2, numpy as np, time
from picamera2 import Picamera2
from libcamera import controls

# 1. Grab a clean, unannotated frame with capture_gpr controls
cam = Picamera2()
cfg = cam.create_still_configuration(main={"size": (1296, 1296)})
cam.configure(cfg)
cam.start()
cam.set_controls({
    "AfMode": controls.AfModeEnum.Manual,
    "LensPosition": 0.42,
    "AeEnable": False,
    "ExposureTime": 24000,
    "AnalogueGain": 1.0,
    "AwbEnable": False,
    "ColourGains": (1.8, 1.6),
})
time.sleep(2)
raw_bgr = cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)
cam.stop()
cam.close()
cv2.imwrite('/home/crk/clean_test_frame.jpg', raw_bgr)
print("Saved clean frame to /home/crk/clean_test_frame.jpg")

with open('/home/crk/THESIS/Dual_Archi/pot_rois.json') as f:
    cfg = json.load(f)
rois = cfg.get("rois", cfg)

hsv = cv2.cvtColor(raw_bgr, cv2.COLOR_BGR2HSV)

print("\n--- SWEEPING HSV ON REAL PIXELS ---")
print("Target: Cotyledon pots ~0.8% - 2.5%, Empty/bare soil pots <= 0.3%")
print(f"{'HUE':<12} {'SAT':<6} {'VAL':<6} | " + " ".join([f"{k:>5}" for k in sorted(rois.keys())]))
print("-" * 75)

for h_lo, h_hi in [(35, 85), (38, 85), (40, 85)]:
    for s_min in [60, 70, 80, 90, 100]:
        for v_min in [45, 55, 65]:
            m = cv2.inRange(hsv, np.array([h_lo, s_min, v_min]), np.array([h_hi, 255, 255]))
            kernel = np.ones((3, 3), np.uint8)
            m_open = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel)
            
            vals = []
            for pid in sorted(rois.keys()):
                r = rois[pid]
                cx, cy = int(r["x"] + r["w"]/2), int(r["y"] + r["h"]/2)
                rad = int(min(r["w"], r["h"])/2)
                pmask = np.zeros(hsv.shape[:2], np.uint8)
                cv2.circle(pmask, (cx, cy), rad, 255, -1)
                tot = np.count_nonzero(pmask)
                grn = np.count_nonzero(cv2.bitwise_and(m_open, m_open, mask=pmask))
                vals.append(grn / tot * 100)
            
            # Print row
            scores = " ".join([f"{v:5.2f}%" for v in vals])
            print(f"H({h_lo}-{h_hi})   S>{s_min:<3} V>{v_min:<3} | {scores}")
