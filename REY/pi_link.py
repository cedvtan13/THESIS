#!/usr/bin/env python3
"""
pi_link.py -- Raspberry Pi side of the ESP32-S3 serial link.  (rev 2)

Implements the data path that Appendix G line 14 assumes ("Fetch localized
Volumetric Water Content (SM) from ESP32 baseline log") and that Appendix C
step 7 draws, but for which the manuscript specifies no medium. Note that
Appendix A, Fig. 6 currently shows NO link between the two controllers -- that
figure needs updating to match Appendix C.

Runs continuously on the Pi. Three jobs:
  1. Send TIME,<unix_epoch> to the ESP32 on connect, and re-send periodically.
     The ESP32 will NOT irrigate until it has received this.
  2. Append every SM / EVT / ERR line the ESP32 emits into CSV files.
  3. Expose get_sm_snapshot() so the noon cron vision script can pull the
     current soil moisture and write it next to that day's GPR
     (Appendix G, line 14).

Setup on the Pi (once):
    sudo raspi-config
        Interface Options -> Serial Port
            "login shell over serial?"        -> NO
            "serial port hardware enabled?"   -> YES
        reboot
    sudo apt install python3-serial
    Wiring: ESP32 GPIO17 -> Pi pin 10 (RXD)
            ESP32 GPIO18 <- Pi pin  8 (TXD)
            common GND between the two boards  <-- required

Run:
    python3 pi_link.py                 # logger daemon
    python3 pi_link.py --snapshot      # one-shot SM read, prints CSV, exits
    python3 pi_link.py --ping          # link health check
"""

import csv
import os
import sys
import time
from datetime import datetime

import serial

PORT     = "/dev/serial0"
BAUD     = 115200
DATA_DIR = os.path.expanduser("~/agrisentry_data")

SM_CSV  = os.path.join(DATA_DIR, "sm_log.csv")
EVT_CSV = os.path.join(DATA_DIR, "irrigation_log.csv")
ERR_CSV = os.path.join(DATA_DIR, "error_log.csv")

SM_HEADER  = ["wall_time", "esp_epoch"] + [f"P-0{i}" for i in range(1, 10)]
EVT_HEADER = ["wall_time", "esp_epoch", "pot_id", "group", "vwc_before",
              "vwc_target", "dose_ml", "pulse_ms", "event_count", "status"]
ERR_HEADER = ["wall_time", "esp_epoch", "code", "detail"]


def ensure_csv(path, header):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(header)


def append_row(path, header, row):
    ensure_csv(path, header)
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow(row)


def open_link():
    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(0.3)
    ser.reset_input_buffer()
    return ser


def send_time(ser):
    cmd = f"TIME,{int(time.time())}\n"
    ser.write(cmd.encode())
    print(f"[pi_link] sent {cmd.strip()}")


def handle_line(line):
    """Parse one ESP32 line and route it to the right CSV."""
    now = datetime.now().isoformat(timespec="seconds")
    parts = [p.strip() for p in line.split(",")]
    kind = parts[0]

    if kind == "SM" and len(parts) == 11:
        append_row(SM_CSV, SM_HEADER, [now] + parts[1:])
    elif kind == "EVT" and len(parts) == 10:
        append_row(EVT_CSV, EVT_HEADER, [now] + parts[1:])
    elif kind == "ERR" and len(parts) >= 4:
        append_row(ERR_CSV, ERR_HEADER, [now, parts[1], parts[2],
                                         ",".join(parts[3:])])
    # BOOT / ACK / PONG / STAT are informational only -- printed, not stored.


def get_sm_snapshot(timeout=15):
    """Ask the ESP32 for a fresh reading. Returns a list of 9 floats (or None
    for a faulted sensor), or None if the link failed. Import this from your
    noon vision script."""
    try:
        with open_link() as ser:
            send_time(ser)
            ser.write(b"GET_SM\n")
            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = ser.readline().decode(errors="replace").strip()
                if raw.startswith("SM,"):
                    vals = raw.split(",")[2:]
                    return [None if v == "NaN" else float(v) for v in vals]
    except Exception as exc:
        print(f"[pi_link] snapshot failed: {exc}", file=sys.stderr)
    return None


def ping(timeout=5):
    try:
        with open_link() as ser:
            ser.write(b"PING\n")
            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = ser.readline().decode(errors="replace").strip()
                if raw.startswith("PONG"):
                    print(f"[pi_link] link OK -> {raw}")
                    return True
    except Exception as exc:
        print(f"[pi_link] ping failed: {exc}", file=sys.stderr)
    print("[pi_link] no response from ESP32")
    return False


def daemon():
    for path, header in ((SM_CSV, SM_HEADER), (EVT_CSV, EVT_HEADER),
                         (ERR_CSV, ERR_HEADER)):
        ensure_csv(path, header)

    last_sync = 0.0
    while True:
        try:
            with open_link() as ser:
                print(f"[pi_link] connected on {PORT}")
                send_time(ser)
                last_sync = time.time()

                while True:
                    raw = ser.readline().decode(errors="replace").strip()
                    if raw:
                        print(f"  < {raw}")
                        handle_line(raw)

                    # Re-sync hourly so ESP32 drift never accumulates.
                    if time.time() - last_sync > 3600:
                        send_time(ser)
                        last_sync = time.time()

        except Exception as exc:
            print(f"[pi_link] link error: {exc} -- retrying in 10 s",
                  file=sys.stderr)
            time.sleep(10)


if __name__ == "__main__":
    if "--snapshot" in sys.argv:
        print(get_sm_snapshot())
    elif "--ping" in sys.argv:
        sys.exit(0 if ping() else 1)
    else:
        daemon()
