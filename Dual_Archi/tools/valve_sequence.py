#!/usr/bin/env python3
"""valve_sequence.py -- run each pot's valve + pump in order, P-01 .. P-09.

For checking which hose each valve feeds: take the hoses OUT of the pots (into
a bucket) first. Every step pumps real water (MANUAL_WATER, not counted as an
irrigation event). Stops pi-link; restart it afterwards:
    sudo -n systemctl restart pi-link

    python3 tools/valve_sequence.py --ms 2000 --gap 10
"""
import argparse
import time

from esp_link import EspLink, stop_daemon

ap = argparse.ArgumentParser()
ap.add_argument("--ms", type=int, default=2000, help="pump time per valve (max 15000)")
ap.add_argument("--gap", type=float, default=10, help="seconds between valves")
ap.add_argument("--pots", default="1,2,3,4,5,6,7,8,9")
args = ap.parse_args()

stop_daemon()
with EspLink() as esp:
    print("starting in 5 s", flush=True)
    time.sleep(5)
    for pot in [int(p) for p in args.pots.split(",")]:
        print(time.strftime("%H:%M:%S") + f"  VALVE P-0{pot} + pump, {args.ms} ms", flush=True)
        r = esp.ask(f"MANUAL_WATER,{pot - 1},{min(args.ms, 15000)}", ("ACK,MANUAL_WATER", "ERR"),
                    args.ms / 1000 + 4)
        print(time.strftime("%H:%M:%S") + f"  -> {r}", flush=True)
        time.sleep(args.gap)
print("done. pi-link is STOPPED. Restart: sudo -n systemctl restart pi-link")
