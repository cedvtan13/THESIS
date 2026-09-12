import io
import time
from http import server
from threading import Condition
from picamera2 import Picamera2

STREAM_WIDTH = 1280
STREAM_HEIGHT = 720
PORT = 8000

PAGE = f"""\
<!DOCTYPE html>
<html>
<head>
    <title>Pi Cam V3 Live View</title>
    <style>
        body {{ background: #121212; color: #eee; font-family: sans-serif; text-align: center; margin: 0; padding: 20px; }}
        h2 {{ margin: 5px; color: #4CAF50; }}
        p {{ margin: 5px 0 15px; font-size: 14px; color: #aaa; }}
        img {{ max-width: 90vw; max-height: 80vh; border: 2px solid #333; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
    </style>
</head>
<body>
    <h2>Raspberry Pi Camera V3 Test Feed</h2>
    <p>Resolution: {STREAM_WIDTH}x{STREAM_HEIGHT} | Nadir Height & FOV Calibration</p>
    <img src="stream.mjpg" />
</body>
</html>
"""

# Initialize Picamera2
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (STREAM_WIDTH, STREAM_HEIGHT), "format": "XBGR8888"}
)
picam2.configure(config)
picam2.start()

# Give auto-exposure and auto-focus 1 second to stabilize
time.sleep(1)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                buf = io.BytesIO()
                while True:
                    buf.seek(0)
                    buf.truncate()
                    picam2.capture_file(buf, format='jpeg')
                    frame = buf.getvalue()

                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
                    # Small delay to keep CPU usage low on Pi Zero 2W
                    time.sleep(0.04)
            except Exception:
                pass
        else:
            self.send_error(404)
            self.end_headers()

print(f"[Camera] Stream live at: http://groupb.local:{PORT}/ (or your Pi IP)")

try:
    server_address = ('', PORT)
    httpd = server.HTTPServer(server_address, StreamingHandler)
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nStopping camera stream...")
finally:
    picam2.stop()
    picam2.close()