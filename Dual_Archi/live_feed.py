#!/usr/bin/env python3
"""live_feed.py -- live ROI alignment stream for arranging the pots.

Open http://groupb.local:5000 (or http://<pi-ip>:5000) in a browser and move
each pot until its rim sits inside its green circle.

The camera is opened with capture_gpr.open_locked_camera(), i.e. the SAME
still configuration, fixed focus (LensPosition 0.42), locked exposure and white
balance as the daily GPR capture, and the circles come from the same
pot_rois.json through the same roi_geometry(). What you line up here is what
gets measured.

    python3 live_feed.py              3 fps
    python3 live_feed.py --fps 2
    python3 live_feed.py --light      capture light ON while streaming
                                      (re-sent every 15 s; goes off by itself
                                       within 20 s after you quit)

Stop with Ctrl+C. The camera can only be used by one program at a time, so
stop this before the 12:00 capture (or a bench test) needs it.
"""
import argparse
import json
import os
import threading
import time

import cv2
from flask import Flask, Response

from capture_gpr import ROI_FILE, open_locked_camera, roi_geometry

app = Flask(__name__)
lock = threading.Lock()
latest = {"jpeg": None}


def load_rois():
    with open(ROI_FILE) as f:
        cfg = json.load(f)
    return cfg.get("rois", cfg)


def draw(frame, rois):
    for pot_id, roi in rois.items():
        cx, cy, r = roi_geometry(roi)
        c = (int(cx), int(cy))
        cv2.circle(frame, c, int(r), (0, 255, 0), 2)          # measured area
        cv2.circle(frame, c, 3, (0, 255, 0), -1)               # centre pip
        cv2.putText(frame, pot_id, (int(cx - r), max(25, int(cy - r) - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    return frame


def camera_loop(fps, use_light):
    """One camera owner; every browser tab gets the latest frame."""
    import pi_link
    rois = load_rois()
    cam = open_locked_camera()
    time.sleep(1)
    period = 1.0 / fps
    next_light = 0.0
    try:
        while True:
            t0 = time.time()
            if use_light and t0 >= next_light:
                pi_link.light_pulse(20000)            # self-expiring, refresh before it lapses
                next_light = t0 + 15
            # same colour conversion as capture_gpr.capture_frame()
            frame = cv2.cvtColor(cam.capture_array(), cv2.COLOR_RGB2BGR)
            ok, jpeg = cv2.imencode(".jpg", draw(frame, rois), [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ok:
                with lock:
                    latest["jpeg"] = jpeg.tobytes()
            time.sleep(max(0.0, period - (time.time() - t0)))
    finally:
        cam.stop()
        cam.close()
        if use_light:
            pi_link.set_light_state(False)


def stream(fps):
    period = 1.0 / fps
    while True:
        with lock:
            jpeg = latest["jpeg"]
        if jpeg:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
        time.sleep(period)


@app.route("/")
def index():
    return """
    <html>
      <body style='background-color: #121212; color: #fff; text-align: center; font-family: sans-serif; margin-top: 20px;'>
        <h2>Live ROI Alignment Guide</h2>
        <p style='color: #aaa;'>Move each physical pot until its inner rim sits squarely inside the green circle.</p>
        <img src='/video_feed' style='border: 2px solid #333; max-width: 90vw; max-height: 80vh;'>
      </body>
    </html>
    """


@app.route("/video_feed")
def video_feed():
    return Response(stream(app.config["FPS"]), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Live ROI alignment stream")
    ap.add_argument("--fps", type=float, default=3.0, help="frames per second (default 3)")
    ap.add_argument("--light", action="store_true", help="keep the capture light on while streaming")
    ap.add_argument("--port", type=int, default=5000)
    args = ap.parse_args()
    app.config["FPS"] = max(0.5, min(args.fps, 10.0))
    threading.Thread(target=camera_loop, args=(app.config["FPS"], args.light), daemon=True).start()
    print(f"[live_feed] http://groupb.local:{args.port}  ({app.config['FPS']:g} fps, Ctrl+C to stop)")
    app.run(host="0.0.0.0", port=args.port, threaded=True)
