import io
import time
from flask import Flask, Response
from picamera2 import Picamera2
from libcamera import controls  # Exposes AfMode controls

app = Flask(__name__)

STREAM_WIDTH = 1296
STREAM_HEIGHT = 1296

picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (STREAM_WIDTH, STREAM_HEIGHT)})
picam2.configure(config)

# Start camera and enable Continuous Autofocus
picam2.start()
picam2.set_controls({
    "AfMode": controls.AfModeEnum.Continuous,
    "AfRange": controls.AfRangeEnum.Normal,
    "AfSpeed": controls.AfSpeedEnum.Normal
})

# Allow 2 seconds for sensor exposure, white balance, and lens focus to converge
time.sleep(2)

def generate_frames():
    buf = io.BytesIO()
    while True:
        buf.seek(0)
        buf.truncate()
        picam2.capture_file(buf, format='jpeg')
        frame = buf.getvalue()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(1.0)  # 1 frame per second

@app.route('/')
def index():
    return "<html><body style='background-color: black; text-align: center;'><img src='/video_feed' style='max-width: 100%;'></body></html>"

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)