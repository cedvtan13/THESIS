#!/usr/bin/env python3
"""flow_test.py -- measure the real flow rate through each valve.

For each pot: put a measuring cup under its emitter, press Enter, and the ESP32
runs the real watering path (valve opens -> 0.25 s -> pump ON for N seconds ->
pump OFF -> 0.25 s -> valve closes). Type how many mL you collected; it works
out mL/s, saves every run, and at the end compares the result with the
firmware's PUMP_FLOW_ML_PER_S (the number used to turn a dose in mL into pump
time).

  python3 flow_test.py                      all 9 pots, 5 s each, 1 run
  python3 flow_test.py --pots 1,4,7 --runs 3 --seconds 5

Results are appended to ~/thesis/flow_calibration.csv.

The ESP32 is NOT given the time here, so no automatic irrigation can start in
the middle of the test.
"""
import argparse
import csv
import os
import re
import statistics
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from actuator_test import watched          # noqa: E402  (reboot detection)
from esp_link import EspLink, info_dict, stop_daemon  # noqa: E402

DUAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_CSV = os.path.join(DUAL, "flow_calibration.csv")
FW = os.path.join(DUAL, "Dual_Archi_Firmware", "src", "main.cpp")


def firmware_flow():
    try:
        m = re.search(r"PUMP_FLOW_ML_PER_S\s*=\s*([\d.]+)", open(FW).read())
        return float(m.group(1)) if m else None
    except OSError:
        return None


def ask_ml(prompt):
    """Returns float mL, None to skip, or 'redo'."""
    while True:
        a = input(prompt).strip().lower()
        if a == "":
            return None
        if a in ("r", "redo"):
            return "redo"
        try:
            v = float(a)
            if v >= 0:
                return v
        except ValueError:
            pass
        print("    type the mL collected (e.g. 96), r to redo, or Enter to skip")


def main():
    ap = argparse.ArgumentParser(description="Per-valve flow rate test")
    ap.add_argument("--pots", default="1,2,3,4,5,6,7,8,9", help="e.g. 1,4,7")
    ap.add_argument("--seconds", type=float, default=5.0, help="pump time per run (max 15)")
    ap.add_argument("--runs", type=int, default=1, help="runs per pot (3 gives a better average)")
    args = ap.parse_args()

    pots = [int(p) for p in args.pots.split(",") if p.strip()]
    if not pots or not all(1 <= p <= 9 for p in pots):
        sys.exit("--pots must be numbers 1-9")
    ms = int(min(max(args.seconds, 0.5), 15.0) * 1000)

    stop_daemon()
    results = {p: [] for p in pots}
    new_file = not os.path.exists(OUT_CSV)
    with EspLink() as esp, open(OUT_CSV, "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["timestamp", "pot_id", "pump_ms", "ml_collected", "ml_per_s"])
        info = info_dict(esp.ask("INFO", "INFO", 3))
        if info.get("actuators") != "ENABLED":
            sys.exit("ESP32 actuators are DISABLED -- set ACTUATORS_ENABLED = true and ./flash_esp.sh")

        print(f"\nFlow test: pots {pots}, pump {ms / 1000:g} s per run, {args.runs} run(s) each.")
        print("After each run type the mL collected, 'r' to redo, or Enter to skip.  Ctrl-C quits.\n")
        try:
            for pot in pots:
                run = 0
                while run < args.runs:
                    input(f"P-0{pot} run {run + 1}/{args.runs}: cup under P-0{pot}, then press Enter ")
                    ok = watched(esp, f"MANUAL_WATER,{pot - 1},{ms}", "ACK,MANUAL_WATER", ms / 1000 + 4)
                    if not ok:
                        print("    run failed -- not recorded")
                        if input("    try again? [Y/n] ").strip().lower() != "n":
                            continue
                        break
                    ml = ask_ml("    mL collected: ")
                    if ml == "redo":
                        continue
                    run += 1
                    if ml is None:
                        print("    skipped")
                        continue
                    rate = ml / (ms / 1000)
                    results[pot].append(rate)
                    w.writerow([datetime.now().isoformat(timespec="seconds"),
                                f"P-0{pot}", ms, ml, f"{rate:.2f}"])
                    f.flush()
                    print(f"    -> {rate:.1f} mL/s")
        except KeyboardInterrupt:
            print("\n  stopped early")

    rates = {p: statistics.mean(v) for p, v in results.items() if v}
    if not rates:
        print("no measurements recorded")
        return
    print("\n== RESULTS (mL/s)")
    for p, r in rates.items():
        spread = (f"  (runs: {', '.join(f'{x:.1f}' for x in results[p])})"
                  if len(results[p]) > 1 else "")
        print(f"  P-0{p}: {r:5.1f}{spread}")
    overall = statistics.mean(rates.values())
    print(f"  average: {overall:.1f} mL/s")
    if len(rates) > 1:
        lo, hi = min(rates.values()), max(rates.values())
        pct = (hi - lo) / overall * 100
        print(f"  spread between valves: {lo:.1f}-{hi:.1f} mL/s ({pct:.0f}%)")
        if pct > 15:
            print("  ! valves differ by more than 15% -- one flow number for all pots will\n"
                  "    over- or under-water some of them. Consider a per-pot flow table.")
    fw = firmware_flow()
    if fw:
        print(f"\n  firmware PUMP_FLOW_ML_PER_S = {fw:g}")
        if abs(overall - fw) / fw > 0.05:
            print(f"  -> update it to {overall:.1f} in Dual_Archi_Firmware/src/main.cpp, then ./flash_esp.sh")
            print(f"     (right now a 100 mL dose actually delivers about {100 * overall / fw:.0f} mL)")
        else:
            print("  -> within 5%, no change needed")
    print(f"\nsaved to {OUT_CSV}")
    print("pi-link is still stopped; start the system with tools/agrisentry.sh start")


if __name__ == "__main__":
    main()
