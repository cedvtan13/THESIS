#!/usr/bin/env python3
"""
stream_preview.py -- live camera preview in a browser, for AIMING THE RIG.

Group B thesis rig. Run on the Raspberry Pi, open the page on your laptop.

    python3 stream_preview.py
    -> http://<pi-ip>:8000/

WHAT IT'S FOR
  This is not just a video feed. It draws the things you actually need while
  mounting the camera:

    normal   plain view + centre crosshair + thirds grid (level the frame)
    roi      overlays the circles from pot_rois.json (are all 9 pots inside?)
    mask     shows ONLY what your HSV band selects (calibrate on real leaves)
    gpr      ROI overlay + live per-pot GPR percentage

  Switch modes with the buttons on the page, or ?mode=roi in the URL.

  The 'mask' mode is the HSV tuning task from your critical list. Point it at
  real Pechay leaves and check they light up. If the leaves stay black, your
  HUE_LO/HUE_HI are wrong -- and remember those are OpenCV hue units (0-179),
  NOT degrees. Do not halve them.

NOTES
  - Preview is 16:9 to match the 2304x1296 still capture. If you change the
    size, keep 16:9 or the ROI overlay will not line up.
  - It tries to keep the same sensor field of view as the still capture. The
    printed sensor output size on startup should read 2304x1296. If it does
    not, the preview FOV differs from what capture_gpr.py will see and the
    aiming is not valid -- say so and we will fix the config.
  - Picamera2's format names are inverted: "RGB888" hands you a BGR array,
    which is what OpenCV wants. No conversion needed here.

    Ctrl-C to stop.
"""

import argparse
import io
import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import cv2
import numpy as np

# --- must match capture_gpr.py exactly -------------------------------------
HUE_LO, HUE_HI = 35, 85          # OpenCV hue units (0-179), NOT degrees
SAT_MIN, VAL_MIN = 40, 40
MORPH_KERNEL = np.ones((5, 5), np.uint8)

FULL_W, FULL_H = 2304, 1296      # the still-capture resolution ROIs refer to

state = {"mode": "normal"}
latest = {"jpeg": None}
lock = threading.Lock()


def load_rois(path):
    if not os.path.exists(path):
        print(f"[preview] no {path} -- ROI overlay disabled", file=sys.stderr)
        return None, True
    with open(path) as f:
        cfg = json.load(f)
    return cfg.get("rois", cfg), bool(cfg.get("circular", True))


def green_mask(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv,
                    np.array([HUE_LO, SAT_MIN, VAL_MIN], np.uint8),
                    np.array([HUE_HI, 255, 255], np.uint8))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, MORPH_KERNEL)


def draw_guides(img):
    """Centre crosshair and thirds grid -- use these to level the frame."""
    h, w = img.shape[:2]
    for i in (1, 2):
        cv2.line(img, (w * i // 3, 0), (w * i // 3, h), (70, 70, 70), 1)
        cv2.line(img, (0, h * i // 3), (w, h * i // 3), (70, 70, 70), 1)
    cx, cy = w // 2, h // 2
    cv2.line(img, (cx - 20, cy), (cx + 20, cy), (0, 255, 255), 1)
    cv2.line(img, (cx, cy - 20), (cx, cy + 20), (0, 255, 255), 1)
    return img


def render(bgr, rois, circular, scale, mode):
    h, w = bgr.shape[:2]

    if mode == "mask":
        m = green_mask(bgr)
        out = cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)
        out[m > 0] = (0, 255, 0)
        pct = 100.0 * np.count_nonzero(m) / m.size
        cv2.putText(out, f"whole frame green: {pct:5.2f}%", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(out, f"H {HUE_LO}-{HUE_HI}  S>{SAT_MIN}  V>{VAL_MIN}",
                    (10, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        return out

    out = bgr.copy()
    draw_guides(out)

    if mode in ("roi", "gpr") and rois:
        gm = green_mask(bgr) if mode == "gpr" else None
        for i in range(9):
            pid = f"P-0{i + 1}"
            r = rois.get(pid)
            if not r:
                continue
            x = int(r["x"] * scale); y = int(r["y"] * scale)
            ww = int(r["w"] * scale); hh = int(r["h"] * scale)
            inside = (x >= 0 and y >= 0 and x + ww <= w and y + hh <= h)
            col = (0, 255, 0) if inside else (0, 0, 255)   # red = falls off frame

            label = pid
            if circular:
                cx, cy = x + ww // 2, y + hh // 2
                rad = min(ww, hh) // 2
                cv2.circle(out, (cx, cy), rad, col, 2)
                if gm is not None:
                    area = np.zeros(gm.shape, np.uint8)
                    cv2.circle(area, (cx, cy), rad, 255, -1)
                    tot = int(np.count_nonzero(area))
                    grn = int(np.count_nonzero(cv2.bitwise_and(gm, gm, mask=area)))
                    label = f"{pid} {100.0 * grn / tot if tot else 0:.1f}%"
            else:
                cv2.rectangle(out, (x, y), (x + ww, y + hh), col, 2)

            cv2.putText(out, label, (x, max(14, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)

    cv2.putText(out, f"mode: {mode}", (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    return out


PAGE = """<!doctype html><html><head><title>Group B rig preview</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 body{{background:#111;color:#ddd;font-family:system-ui,sans-serif;margin:0;padding:12px}}
 img{{width:100%;max-width:1200px;display:block;border:1px solid #333}}
 a{{display:inline-block;padding:8px 14px;margin:6px 6px 6px 0;background:#222;
    color:#ddd;text-decoration:none;border:1px solid #444;border-radius:4px}}
 a.on{{background:#2a5;color:#000;border-color:#2a5}}
 p{{color:#888;font-size:14px;max-width:900px}}
</style></head><body>
<div>{buttons}</div>
<img src="/stream.mjpg?t={ts}">
<p><b>normal</b> level the frame with the grid &middot;
   <b>roi</b> every circle must be green (red = that pot falls off the frame) &middot;
   <b>mask</b> point at real leaves &mdash; they must light up green &middot;
   <b>gpr</b> live per-pot percentage</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass                                    # keep the console quiet

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path == "/":
            if "mode" in q:
                state["mode"] = q["mode"][0]
            modes = ["normal", "roi", "mask", "gpr"]
            btns = "".join(
                f'<a class="{"on" if m == state["mode"] else ""}" href="/?mode={m}">{m}</a>'
                for m in modes)
            body = PAGE.format(buttons=btns, ts=int(time.time())).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif u.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header("Age", "0")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=FRAME")
            self.end_headers()
            try:
                while True:
                    with lock:
                        buf = latest["jpeg"]
                    if buf is None:
                        time.sleep(0.05)
                        continue
                    self.wfile.write(b"--FRAME\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(buf)))
                    self.end_headers()
                    self.wfile.write(buf)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_error(404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--width", type=int, default=1024, help="16:9 please")
    ap.add_argument("--roi-file",
                    default=os.path.expanduser("~/thesis/pot_rois.json"))
    ap.add_argument("--lock-exposure", action="store_true",
                    help="use the same locked settings as capture_gpr.py")
    args = ap.parse_args()

    w = args.width
    h = int(round(w * 9 / 16))
    scale = w / FULL_W

    rois, circular = load_rois(args.roi_file)

    from picamera2 import Picamera2
    picam2 = Picamera2()

    # Keep the same sensor field of view as the 2304x1296 still capture,
    # otherwise aiming with this preview tells you nothing useful.
    try:
        cfg = picam2.create_video_configuration(
            main={"size": (w, h), "format": "RGB888"},
            sensor={"output_size": (FULL_W, FULL_H)})
    except (TypeError, KeyError):
        print("[preview] this picamera2 has no 'sensor' option -- "
              "VERIFY the preview FOV matches the still before trusting it",
              file=sys.stderr)
        cfg = picam2.create_video_configuration(
            main={"size": (w, h), "format": "RGB888"})

    picam2.configure(cfg)
    picam2.start()
    time.sleep(1.0)

    if args.lock_exposure:
        from libcamera import controls
        picam2.set_controls({
            "AfMode": controls.AfModeEnum.Manual, "LensPosition": 2.5,
            "AeEnable": False, "ExposureTime": 8000, "AnalogueGain": 1.0,
            "AwbEnable": False, "ColourGains": (1.8, 1.6)})
        time.sleep(1.0)

    try:
        sensor = picam2.camera_configuration().get("sensor", {})
        print(f"[preview] sensor output: {sensor.get('output_size')}  "
              f"(want {FULL_W}x{FULL_H})")
    except Exception:
        pass

    ip = "0.0.0.0"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
    except Exception:
        pass
    print(f"[preview] {w}x{h}  ->  http://{ip}:{args.port}/")
    print("[preview] Ctrl-C to stop")

    def grabber():
        while True:
            frame = picam2.capture_array()          # RGB888 config -> BGR array
            out = render(frame, rois, circular, scale, state["mode"])
            ok, enc = cv2.imencode(".jpg", out,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if ok:
                with lock:
                    latest["jpeg"] = enc.tobytes()
            time.sleep(0.02)

    threading.Thread(target=grabber, daemon=True).start()

    srv = ThreadingHTTPServer(("", args.port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        picam2.stop()
        picam2.close()


if __name__ == "__main__":
    main()
