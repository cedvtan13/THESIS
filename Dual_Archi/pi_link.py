#!/usr/bin/env python3
"""
pi_link.py -- Raspberry Pi Zero 2W side of the ESP32-S3 serial link.  v4

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Implements the data path Appendix G line 14 assumes ("Fetch localized
Volumetric Water Content (SM) from ESP32 baseline log") and Appendix C step 7.

Three jobs:
  1. Send TIME,<unix_epoch> on connect and hourly. The ESP32 will NOT irrigate
     until it has received this, so this process must be running.
  2. Append every SM / EVT / ERR line the ESP32 emits into CSV files.
  3. Serve moisture snapshots to the noon vision script -> Deliverable 5.

This process makes NO irrigation decisions. Per Fig. 4 and Fig. 6 the ESP32-S3
owns irrigation entirely; if this script dies, watering continues.

WHY THE REQUEST-FILE HANDSHAKE (v4)
-----------------------------------------------------------------------------
Previously capture_gpr.py called get_sm_snapshot(), which opened /dev/ttyAMA0
directly. But the daemon already holds that port open. Linux allows a second
open of the same tty, so both processes read from one byte stream and each
receives a fragment -- silently corrupting the daemon's log AND returning NaN
for the noon SM reading, on the one day per plant that actually matters.

Now there is exactly one owner of the serial port. Anything that needs a
reading drops a request file; the daemon services it and writes the answer to
sm_snapshot.json. The port is also opened with exclusive=True, so a second
opener fails loudly instead of corrupting data quietly.

Pi setup (once):
    sudo raspi-config
        Interface Options -> Serial Port
            login shell over serial?       NO
            serial port hardware enabled?  YES
    echo "dtoverlay=disable-bt" | sudo tee -a /boot/firmware/config.txt
    sudo reboot
    sudo apt install python3-serial

The disable-bt overlay matters: without it /dev/serial0 is the miniUART, whose
baud rate drifts with CPU frequency and corrupts bytes under load.

Wiring (see docs/WIRING.md):
    ESP32-S3 GPIO17 (TX) -> Pi GPIO15 / physical pin 10 (RXD)
    ESP32-S3 GPIO18 (RX) <- Pi GPIO14 / physical pin  8 (TXD)
    GND <-> Pi pin 6                      <-- mandatory, not optional

Run:
    python3 pi_link.py              logger daemon (normally via systemd)
    python3 pi_link.py --snapshot   one-shot SM read, prints, exits
    python3 pi_link.py --ping       link health check
    python3 pi_link.py --status     per-pot configuration dump
    python3 pi_link.py --bands-on   end germination mode
    python3 pi_link.py --clear-faults   un-quarantine all pots after repair
"""

import csv
import json
import os
import sys
import time
from datetime import datetime

import serial

def _default_port():
    """Prefer the real PL011. Fall back to whatever /dev/serial0 points at.

    /dev/ttyAMA0 only exists once `dtoverlay=disable-bt` is in config.txt.
    Without it /dev/serial0 is ttyS0, the miniUART, whose baud rate is tied to
    the core clock and corrupts bytes when the CPU throttles. The fallback lets
    you bench-test before the reboot, but it is NOT fit for the grow-out --
    fix config.txt. Override with AGRISENTRY_PORT=/dev/xxx if you must."""
    env = os.environ.get("AGRISENTRY_PORT")
    if env:
        return env
    if os.path.exists("/dev/ttyAMA0"):
        return "/dev/ttyAMA0"
    if os.path.exists("/dev/serial0"):
        print("[pi_link] WARNING: /dev/ttyAMA0 missing, using /dev/serial0 "
              "(miniUART). Add 'dtoverlay=disable-bt' to /boot/firmware/config.txt "
              "and reboot before collecting real data.", file=sys.stderr)
        return "/dev/serial0"
    return "/dev/ttyAMA0"


PORT = _default_port()
BAUD = 115200
DATA_DIR = os.path.expanduser("~/agrisentry_data")

SM_CSV = os.path.join(DATA_DIR, "sm_log.csv")
EVT_CSV = os.path.join(DATA_DIR, "irrigation_log.csv")
ERR_CSV = os.path.join(DATA_DIR, "error_log.csv")

PID_FILE = os.path.join(DATA_DIR, "pi_link.pid")
REQ_FILE = os.path.join(DATA_DIR, "request_sm")
SNAP_FILE = os.path.join(DATA_DIR, "sm_snapshot.json")
LIGHT_FILE = os.path.join(DATA_DIR, "request_light")

SM_HEADER = ["wall_time", "esp_epoch"] + [f"P-0{i}" for i in range(1, 10)]
EVT_HEADER = ["wall_time", "esp_epoch", "pot_id", "group", "vwc_before",
              "vwc_target", "dose_ml", "pulse_ms", "event_count", "status"]
ERR_HEADER = ["wall_time", "esp_epoch", "code", "detail"]

# A snapshot older than this is not good enough to pair with a GPR row.
SNAPSHOT_MAX_AGE_S = 45 * 60


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------
def ensure_csv(path, header):
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerow(header)


def append_row(path, header, row):
    ensure_csv(path, header)
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow(row)


# ---------------------------------------------------------------------------
# Serial
# ---------------------------------------------------------------------------
def open_link():
    """Exclusive open. If the daemon already holds the port this raises, which
    is the point -- a loud failure beats two readers splitting one byte stream."""
    ser = serial.Serial(PORT, BAUD, timeout=2, exclusive=True)
    time.sleep(0.3)
    ser.reset_input_buffer()
    return ser


def send_time(ser):
    cmd = f"TIME,{int(time.time())}\n"
    ser.write(cmd.encode())
    print(f"[pi_link] sent {cmd.strip()}")


def parse_sm(raw):
    """'SM,<epoch>,v1..v9' -> (epoch, [9 floats/None]) or None if malformed."""
    parts = [p.strip() for p in raw.split(",")]
    if parts[0] != "SM" or len(parts) != 11:
        return None
    try:
        epoch = int(parts[1])
    except ValueError:
        return None
    vals = [None if v == "NaN" else float(v) for v in parts[2:]]
    return epoch, vals


def handle_line(line):
    """Route one ESP32 line to the correct CSV."""
    now = datetime.now().isoformat(timespec="seconds")
    parts = [p.strip() for p in line.split(",")]
    kind = parts[0]

    if kind == "SM" and len(parts) == 11:
        append_row(SM_CSV, SM_HEADER, [now] + parts[1:])
    elif kind == "EVT" and len(parts) == 10:
        append_row(EVT_CSV, EVT_HEADER, [now] + parts[1:])
    elif kind == "ERR" and len(parts) >= 4:
        append_row(ERR_CSV, ERR_HEADER,
                   [now, parts[1], parts[2], ",".join(parts[3:])])
    # BOOT / ACK / PONG / STAT are informational: printed, not stored.


# ---------------------------------------------------------------------------
# Daemon liveness
# ---------------------------------------------------------------------------
def daemon_pid():
    """PID of a live daemon, or None."""
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)          # signal 0 = existence check only
        return pid
    except Exception:
        return None


def write_snapshot(epoch, vals):
    tmp = SNAP_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"esp_epoch": epoch,
                   "wall_time": datetime.now().isoformat(timespec="seconds"),
                   "unix": int(time.time()),
                   "values": vals}, f)
    os.replace(tmp, SNAP_FILE)   # atomic: a reader never sees a half-written file


# ---------------------------------------------------------------------------
# Snapshot API used by capture_gpr.py
# ---------------------------------------------------------------------------
def get_sm_snapshot(timeout=25):
    """Return a list of 9 values (None for a faulted pot), or None on failure.

    Routes through the daemon when one is running, so the serial port only ever
    has a single owner. Falls back to a direct read when it is not."""
    if daemon_pid():
        return _snapshot_via_daemon(timeout)
    return _snapshot_direct(timeout)

def _snapshot_via_daemon(timeout):
    os.makedirs(DATA_DIR, exist_ok=True)
    before = os.path.getmtime(SNAP_FILE) if os.path.exists(SNAP_FILE) else 0
    with open(REQ_FILE, "w") as f:
        f.write(str(int(time.time())))

    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(SNAP_FILE) and os.path.getmtime(SNAP_FILE) > before:
            try:
                with open(SNAP_FILE) as f:
                    snap = json.load(f)
                if int(time.time()) - snap.get("unix", 0) <= SNAPSHOT_MAX_AGE_S:
                    return snap["values"]
            except Exception:
                pass
            break
        time.sleep(0.5)

    print("[pi_link] daemon did not answer the snapshot request", file=sys.stderr)
    return _latest_from_log()


def _latest_from_log():
    """Last resort: newest row of sm_log.csv, if it is recent enough.

    Better than NaN, but only when it is genuinely fresh -- pairing a GPR row
    with hours-old moisture would quietly corrupt the SM column."""
    if not os.path.exists(SM_CSV):
        return None
    try:
        with open(SM_CSV, newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return None
        last = rows[-1]
        age = (datetime.now() -
               datetime.fromisoformat(last["wall_time"])).total_seconds()
        if age > SNAPSHOT_MAX_AGE_S:
            print(f"[pi_link] newest sm_log row is {age/60:.0f} min old -- rejecting",
                  file=sys.stderr)
            return None
        return [None if last[f"P-0{i}"] == "NaN" else float(last[f"P-0{i}"])
                for i in range(1, 10)]
    except Exception as exc:
        print(f"[pi_link] could not read {SM_CSV}: {exc}", file=sys.stderr)
        return None


def _snapshot_direct(timeout):
    try:
        with open_link() as ser:
            send_time(ser)
            ser.write(b"GET_SM\n")
            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = ser.readline().decode(errors="replace").strip()
                parsed = parse_sm(raw)
                if parsed:
                    return parsed[1]
    except Exception as exc:
        print(f"[pi_link] direct snapshot failed: {exc}", file=sys.stderr)
    return None

def set_light_state(on: bool, timeout=5) -> bool:
    """Turn Relay 12 (Flash / Grow Light) ON or OFF.
    
    Routes through the daemon via a request file if running,
    otherwise sends the UART command directly.
    """
    if daemon_pid():
        return _set_light_via_daemon(on, timeout)
    return _set_light_direct(on)


def _set_light_via_daemon(on: bool, timeout=5) -> bool:
    os.makedirs(DATA_DIR, exist_ok=True)
    val = "ON" if on else "OFF"
    with open(LIGHT_FILE, "w") as f:
        f.write(val)

    # Wait for the daemon to process and delete the file
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not os.path.exists(LIGHT_FILE):
            return True
        time.sleep(0.05)
    return False


def _set_light_direct(on: bool) -> bool:
    cmd = b"LIGHT_ON\n" if on else b"LIGHT_OFF\n"
    try:
        with open_link() as ser:
            ser.write(cmd)
            resp = ser.readline().decode(errors="replace").strip()
            return "ACK,LIGHT" in resp
    except Exception as exc:
        print(f"[pi_link] direct light toggle failed: {exc}", file=sys.stderr)
        return False

def simple_command(cmd, expect, timeout=8):
    """One-shot command. Refuses to run while the daemon owns the port."""
    if daemon_pid():
        print("[pi_link] daemon is running and owns the serial port.\n"
              "          stop it first:  sudo systemctl stop pi-link", file=sys.stderr)
        return False
    try:
        with open_link() as ser:
            ser.write((cmd + "\n").encode())
            deadline = time.time() + timeout
            while time.time() < deadline:
                raw = ser.readline().decode(errors="replace").strip()
                if raw:
                    print(f"  < {raw}")
                if raw.startswith(expect):
                    return True
    except Exception as exc:
        print(f"[pi_link] {cmd} failed: {exc}", file=sys.stderr)
    return False


# ---------------------------------------------------------------------------
# Daemon
# ---------------------------------------------------------------------------
def daemon():
    os.makedirs(DATA_DIR, exist_ok=True)
    for path, header in ((SM_CSV, SM_HEADER), (EVT_CSV, EVT_HEADER),
                         (ERR_CSV, ERR_HEADER)):
        ensure_csv(path, header)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        while True:
            try:
                with open_link() as ser:
                    print(f"[pi_link] connected on {PORT}")
                    send_time(ser)
                    last_sync = time.time()
                    pending_req = False

                    while True:
                        # A snapshot request from capture_gpr.py
                        if not pending_req and os.path.exists(REQ_FILE):
                            ser.write(b"GET_SM\n")
                            pending_req = True

                        # A light toggle request from capture_gpr.py
                        if os.path.exists(LIGHT_FILE):
                            try:
                                with open(LIGHT_FILE, "r") as f:
                                    target_state = f.read().strip()
                                cmd = b"LIGHT_ON\n" if target_state == "ON" else b"LIGHT_OFF\n"
                                ser.write(cmd)
                                os.remove(LIGHT_FILE)
                            except Exception:
                                pass

                        raw = ser.readline().decode(errors="replace").strip()
                        if raw:
                            print(f"  < {raw}")
                            handle_line(raw)
                            if pending_req:
                                parsed = parse_sm(raw)
                                if parsed:
                                    write_snapshot(*parsed)
                                    try:
                                        os.remove(REQ_FILE)
                                    except FileNotFoundError:
                                        pass
                                    pending_req = False

                        # Re-sync hourly so ESP32 clock drift cannot accumulate.
                        if time.time() - last_sync > 3600:
                            send_time(ser)
                            last_sync = time.time()

            except Exception as exc:
                print(f"[pi_link] link error: {exc} -- retrying in 10 s",
                      file=sys.stderr)
                time.sleep(10)
    finally:
        try:
            os.remove(PID_FILE)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    if "--snapshot" in sys.argv:
        print(get_sm_snapshot())
    elif "--ping" in sys.argv:
        sys.exit(0 if simple_command("PING", "PONG") else 1)
    elif "--status" in sys.argv:
        simple_command("STATUS", "STAT", timeout=12)
    elif "--bands-on" in sys.argv:
        sys.exit(0 if simple_command("BANDS_ON", "ACK,BANDS_ON") else 1)
    elif "--clear-faults" in sys.argv:
        sys.exit(0 if simple_command("CLEAR_FAULTS", "ACK,CLEAR_FAULTS") else 1)
    elif "--light-on" in sys.argv:
        sys.exit(0 if set_light_state(True) else 1)
    elif "--light-off" in sys.argv:
        sys.exit(0 if set_light_state(False) else 1)
    else:
        daemon()
