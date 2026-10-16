#!/usr/bin/env python3
"""raw_watch.py -- stream raw soil ADC for all 9 pots, once a second.

For probe tests (air / water cup / swap). Stops pi-link to own the serial port;
restart it afterwards with:  sudo -n systemctl restart pi-link

    python3 tools/raw_watch.py            # until Ctrl-C
    python3 tools/raw_watch.py --secs 60
Calibration reference (shared by all pots): dry/air ~2483, wet/water ~1120.
"""
import argparse
import time

from esp_link import EspLink, stop_daemon

ap = argparse.ArgumentParser()
ap.add_argument("--secs", type=float, default=0, help="stop after this many seconds (0 = forever)")
args = ap.parse_args()

stop_daemon()
t_end = time.time() + args.secs if args.secs else None
with EspLink() as esp:
    print("time      " + "".join(f"P-0{i}  " for i in range(1, 10)), flush=True)
    try:
        while t_end is None or time.time() < t_end:
            r = esp.ask("GET_RAW", "RAW", 8)
            if r and r.startswith("RAW"):
                vals = r.split(",")[2:]
                print(time.strftime("%H:%M:%S  ") + "".join(f"{v:>5} " for v in vals), flush=True)
            else:
                print(time.strftime("%H:%M:%S  ") + f"no reply ({r})", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
print("pi-link is STOPPED. Restart: sudo -n systemctl restart pi-link")
