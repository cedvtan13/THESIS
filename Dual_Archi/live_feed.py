import io
import json
import os
import time
import cv2
import numpy as np
from flask import Flask, Response
from picamera2 import Picamera2
from libcamera import controls

app = Flask(__name__)

STREAM_WIDTH = 1296
STREAM_HEIGHT = 1296
ROI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pot_rois.json")

# Fallback default coordinates if pot_rois.json is missing
DEFAULT_ROIS = {
    "P-01": {"x": 284, "y": 306, "w": 149, "h": 149},
    "P-02": {"x": 562, "y": 296, "w": 149, "h": 149},
    "P-03": {"x": 828, "y": 283, "w": 149, "h": 149},
    "P-04": {"x": 289, "y": 601, "w": 149, "h": 149},
    "P-05": {"x": 570, "y": 589, "w": 149, "h": 149},
    "P-06": {"x": 851, "y": 576, "w": 149, "h": 149},
    "P-07": {"x": 301, "y": 906, "w": 149, "h": 149},
    "P-08": {"x": 580, "y": 896, "w": 149, "h": 149},
    "P-09": {"x": 848, "y": 888, "w": 149, "h": 149}
}

def load_rois():
    if os.path.exists(ROI_FILE):
        try:
            with open(ROI_FILE, "r") as f:
                data = json.load(f)
                return data.get("rois", DEFAULT_ROIS)
        except Exception:
            return DEFAULT_ROIS
    return DEFAULT_ROIS

rois = load_rois()

picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (STREAM_WIDTH, STREAM_HEIGHT), "format": "BGR888"})
picam2.configure(config)
picam2.start()

# Enable Continuous Autofocus for live alignment
picam2.set_controls({
    "AfMode": controls.AfModeEnum.Continuous,
    "AfRange": controls.AfRangeEnum.Normal,
    "AfSpeed": controls.AfSpeedEnum.Normal
})
time.sleep(2)

def generate_frames():
    while True:
        # Capture raw BGR array directly from sensor
        frame = picam2.capture_array()

        # Draw ROI guide circles and labels over the frame
        for pot_id, r in rois.items():
            cx = r["x"] + r["w"] // 2
            cy = r["y"] + r["h"] // 2
            rad = min(r["w"], r["h"]) // 2

            # Green circle for the pot soil target
            cv2.circle(frame, (cx, cy), rad, (0, 255, 0), 2)
            # Center target pip
            cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1)
            # Pot label
            cv2.putText(frame, pot_id, (r["x"], max(25, r["y"] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Encode modified frame with overlays to JPEG
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue

        frame_bytes = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.5)  # 2 fps: smooth enough to align pots without exhausting Pi Zero 2W RAM

@app.route('/')
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

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True)