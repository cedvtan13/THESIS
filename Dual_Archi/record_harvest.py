#!/usr/bin/env python3
"""
record_harvest.py -- capture ground-truth harvest data on D = 30 (harvest day).

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Produces Deliverable 4: the harvest weight table for all nine plants. Writes
harvest_weights.csv, which analyze_yield.py joins to growth_dataset.csv on
pot_id.

WHEN TO RUN
    On D = 30, IMMEDIATELY AFTER the final scheduled image capture and before
    anything is uprooted. The manuscript fixes harvest on the same day as the
    last capture specifically so the terminal GPR corresponds in time to the
    measured weight -- this corrects the decoupling in the previous
    institutional iteration, where observation ended on day 37 but harvest was
    performed on day 44.

WHAT TO WEIGH
    Above-ground fresh-weight biomass in grams. Cut at the soil line. Do not
    include roots and do not shake soil into the pan. Weigh each plant
    separately on the same calibrated scale, and record to the same number of
    decimal places for every plant.

    Weigh promptly. Pechay loses water fast once cut, and a plant weighed
    twenty minutes after cutting is not comparable to one weighed immediately.

USAGE
    python3 record_harvest.py                 interactive, prompts for each pot
    python3 record_harvest.py --show          print what has been recorded
    python3 record_harvest.py --pot P-03 --grams 214.5 --notes "outer leaf torn"
"""

import argparse
import csv
import os
from datetime import datetime

BASE = os.path.expanduser("~/thesis")
OUT_CSV = os.path.join(BASE, "harvest_weights.csv")

POT_IDS = [f"P-0{i}" for i in range(1, 10)]

# Treatment assignment, mirroring Section III.A.3 and the firmware. Recorded
# here so the harvest table is self-contained and can be read without
# cross-referencing the manuscript.
GROUPS = {
    "P-01": "A_Low", "P-02": "A_Low", "P-03": "A_Low",
    "P-04": "B_Optimal", "P-05": "B_Optimal", "P-06": "B_Optimal",
    "P-07": "C_High", "P-08": "C_High", "P-09": "C_High",
}

HEADER = ["pot_id", "group", "harvest_date", "fresh_weight_g", "notes"]


def load():
    if not os.path.exists(OUT_CSV):
        return {}
    with open(OUT_CSV, newline="") as f:
        return {r["pot_id"]: r for r in csv.DictReader(f)}


def save(rows):
    os.makedirs(BASE, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for pid in POT_IDS:
            if pid in rows:
                w.writerow({k: rows[pid].get(k, "") for k in HEADER})


def show(rows):
    if not rows:
        print("nothing recorded yet")
        return
    print(f"{'pot':<6} {'group':<11} {'weight (g)':>11}  notes")
    print("-" * 58)
    for pid in POT_IDS:
        r = rows.get(pid)
        if r:
            print(f"{pid:<6} {r['group']:<11} {r['fresh_weight_g']:>11}  "
                  f"{r.get('notes','')}")
        else:
            print(f"{pid:<6} {GROUPS[pid]:<11} {'--':>11}")
    missing = [p for p in POT_IDS if p not in rows]
    if missing:
        print(f"\nstill missing: {', '.join(missing)}")
    else:
        print("\nall nine plants recorded")


def put(rows, pot, grams, notes):
    if pot not in GROUPS:
        raise SystemExit(f"unknown pot id {pot!r}; expected one of {POT_IDS}")
    if grams <= 0:
        raise SystemExit("weight must be positive")
    # A pechay head far outside a plausible range is much more likely to be a
    # typo or a scale left in ounces than a real measurement. Warn, do not block.
    if grams < 20 or grams > 600:
        print(f"  !! {grams} g is outside the usual range for pechay "
              f"-- check the scale units before accepting this")
    rows[pot] = {"pot_id": pot, "group": GROUPS[pot],
                 "harvest_date": datetime.now().strftime("%Y-%m-%d"),
                 "fresh_weight_g": f"{grams:.1f}", "notes": notes or ""}


def interactive(rows):
    print("Harvest entry. Blank to skip a pot, 'q' to stop.\n")
    for pid in POT_IDS:
        cur = rows.get(pid, {}).get("fresh_weight_g")
        prompt = f"{pid} ({GROUPS[pid]})"
        prompt += f" [current {cur} g]" if cur else ""
        raw = input(f"{prompt} weight in grams: ").strip()
        if raw.lower() == "q":
            break
        if not raw:
            continue
        try:
            g = float(raw)
        except ValueError:
            print("  not a number, skipped")
            continue
        notes = input("  notes (optional): ").strip()
        put(rows, pid, g, notes)
    save(rows)
    print()
    show(rows)


def main():
    ap = argparse.ArgumentParser(description="Record harvest weights")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--pot")
    ap.add_argument("--grams", type=float)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    rows = load()

    if args.show:
        show(rows)
    elif args.pot:
        if args.grams is None:
            raise SystemExit("--pot needs --grams")
        put(rows, args.pot, args.grams, args.notes)
        save(rows)
        show(rows)
    else:
        interactive(rows)


if __name__ == "__main__":
    main()
