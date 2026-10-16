#!/usr/bin/env python3
"""map_probes.py -- find which channel each physical probe is wired to.

Takes a 5 s baseline, then reports every time a channel moves more than
--thresh counts away from its baseline (probe pulled into air or gripped)
and again when it settles back. Pull one probe at a time, in a known order.
Stops pi-link; restart it afterwards: sudo -n systemctl restart pi-link
"""
import argparse
import statistics
import time

from esp_link import EspLink, stop_daemon

ap = argparse.ArgumentParser()
ap.add_argument("--secs", type=float, default=240)
ap.add_argument("--thresh", type=int, default=150)
args = ap.parse_args()


def read(esp):
    r = esp.ask("GET_RAW", "RAW", 8)
    if r and r.startswith("RAW"):
        return [int(v) for v in r.split(",")[2:]]
    return None


stop_daemon()
with EspLink() as esp:
    samples = []
    t0 = time.time()
    while time.time() - t0 < 5:
        v = read(esp)
        if v:
            samples.append(v)
        time.sleep(0.5)
    base = [int(statistics.median(s[i] for s in samples)) for i in range(9)]
    print("baseline " + " ".join(f"P-0{i+1}={b}" for i, b in enumerate(base)), flush=True)
    print("READY -- pull probes now", flush=True)
    moved = [False] * 9
    t_end = time.time() + args.secs
    while time.time() < t_end:
        v = read(esp)
        if not v:
            continue
        for i in range(9):
            d = v[i] - base[i]
            if not moved[i] and abs(d) > args.thresh:
                moved[i] = True
                print(time.strftime("%H:%M:%S") + f"  MOVED   P-0{i+1}  {base[i]} -> {v[i]} ({d:+d})", flush=True)
            elif moved[i] and abs(d) < args.thresh / 2:
                moved[i] = False
                print(time.strftime("%H:%M:%S") + f"  back    P-0{i+1}  {v[i]}", flush=True)
        time.sleep(0.4)
print("done. pi-link is STOPPED. Restart: sudo -n systemctl restart pi-link")
