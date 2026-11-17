#!/usr/bin/env python3
"""fix_duplicate_day.py -- a day with two sets of rows: keep one set, set the other aside.

Runs ON THE PI. D20 has 18 rows: a 09:36 capture (made by catch_up.sh after a
reboot, outside the noon window) and a 12:42 manual retake. A duplicated plant-day
breaks the leave-one-plant-out analysis. This keeps the set whose timestamp you
choose and moves the other set to a separate file (nothing is deleted).

    python3 ~/fixkit/fix_duplicate_day.py --day 20                     # show both sets
    python3 ~/fixkit/fix_duplicate_day.py --day 20 --keep 12:42 --write
"""
import argparse
import csv
import os
import shutil
from datetime import datetime

BASE = os.path.expanduser("~/thesis")
CSV = os.path.join(BASE, "growth_dataset.csv")

ap = argparse.ArgumentParser()
ap.add_argument("--day", type=int, required=True)
ap.add_argument("--keep", help="time of the set to keep, e.g. 12:42")
ap.add_argument("--write", action="store_true")
a = ap.parse_args()

with open(CSV, newline="") as f:
    rd = csv.reader(f)
    header = next(rd)
    rows = list(rd)
col = {h: i for i, h in enumerate(header)}
day = [r for r in rows if r[col["day"]] == str(a.day)]
sets = {}
for r in day:
    sets.setdefault(r[col["timestamp"]][-5:], []).append(r)
for t, rs in sets.items():
    print(f"D{a.day} set at {t}: {len(rs)} rows")
    for r in rs:
        print(f"   {r[col['pot_id']]}  sm {r[col['sm_pct']]:>5}  cell_gpr {r[col['cell_gpr']]:>5}")
if len(sets) < 2:
    raise SystemExit("only one set for this day; nothing to fix")
if not a.keep or a.keep not in sets:
    raise SystemExit(f"\nchoose one with --keep {' or --keep '.join(sets)}  (add --write to apply)")
drop = [r for t, rs in sets.items() if t != a.keep for r in rs]
if not a.write:
    raise SystemExit(f"\npreview: would keep {a.keep}, set aside {len(drop)} rows (add --write)")
stamp = f"{datetime.now():%Y%m%d_%H%M}"
shutil.copy2(CSV, f"{CSV}.before_dedup_D{a.day}_{stamp}")
aside = os.path.join(BASE, f"growth_dataset_setaside_D{a.day}_{stamp}.csv")
with open(aside, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(drop)
keep = [r for r in rows if r not in drop]
with open(CSV, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(keep)
print(f"\nkept the {a.keep} set; {len(drop)} rows moved to {aside}")
line = (f'{datetime.now():%Y-%m-%d},{a.day},ALL,"D{a.day} DUPLICATE ROWS RESOLVED on {datetime.now():%b %d %H:%M}: '
        f'kept the {a.keep} capture; the other set ({len(drop)} rows) moved to {os.path.basename(aside)}. '
        f'See the D{a.day} notes for why there were two captures."')
with open(os.path.join(BASE, "field_log.csv"), "a", newline="") as f:
    f.write(line + "\r\n")
print("field log updated:\n" + line)
