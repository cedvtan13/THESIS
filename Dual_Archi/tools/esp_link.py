#!/usr/bin/env python3
"""esp_link.py -- small shared helper for the bench / actuator / system tools.

Talks to the ESP32-S3 over /dev/ttyAMA0 directly. The pi-link daemon must NOT
be running (it holds the port exclusively); stop_daemon() takes care of that.
"""
import subprocess
import sys
import time

import serial

PORT = "/dev/ttyAMA0"
BAUD = 115200


def daemon_active():
    r = subprocess.run(["systemctl", "is-active", "pi-link"],
                       capture_output=True, text=True)
    return r.stdout.strip() == "active"


def stop_daemon():
    """Stop pi-link so we can own the serial port. Returns True if it was running."""
    if not daemon_active():
        return False
    print("[esp] stopping pi-link service (frees the serial port)")
    subprocess.run(["sudo", "-n", "systemctl", "stop", "pi-link"], check=True)
    time.sleep(1)
    return True


class EspLink:
    def __init__(self):
        self.ser = serial.Serial(PORT, BAUD, timeout=0.2, exclusive=True)
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def close(self):
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def ask(self, cmd, expect, timeout=5.0, echo=False):
        """Send cmd, return the first line starting with any prefix in expect
        (str or tuple), or None on timeout. ERR lines are returned too, so the
        caller can see why something was refused."""
        if isinstance(expect, str):
            expect = (expect,)
        self.ser.reset_input_buffer()
        self.ser.write((cmd + "\n").encode())
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.ser.readline().decode(errors="replace").strip()
            if not line:
                continue
            if echo:
                print(f"  < {line}")
            if line.startswith(expect) or line.startswith("ERR,"):
                return line
        return None

    def sync_time(self):
        return self.ask(f"TIME,{int(time.time())}", "ACK,TIME")


def info_dict(line):
    """'INFO,a=1,b=2' -> {'a': '1', 'b': '2'}"""
    out = {}
    for part in (line or "").split(",")[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


if __name__ == "__main__":
    # Ad-hoc use:  python3 esp_link.py PING PONG
    if len(sys.argv) < 2:
        sys.exit("usage: esp_link.py <COMMAND> [EXPECT_PREFIX]")
    stop_daemon()
    with EspLink() as esp:
        print(esp.ask(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "", echo=True))
