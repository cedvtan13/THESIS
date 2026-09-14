import io
import time
from flask import Flask, Response
from picamera2 import Picamera2

app = Flask(__name__)

picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (1280, 720)})
picam2.configure(config)
picam2.start()
time.sleep(1)

def generate_frames():
    buf = io.BytesIO()
    while True:
        buf.seek(0)
        buf.truncate()
        picam2.capture_file(buf, format='jpeg')
        frame = buf.getvalue()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.5)  # 2 fps keeps RAM and Wi-Fi stable on Pi Zero 2W

@app.route('/')
def index():
    return "<html><body style='background-color: black; text-align: center;'><img src='/video_feed' style='max-width: 100%;'></body></html>"

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)