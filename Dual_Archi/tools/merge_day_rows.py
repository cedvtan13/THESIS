#!/usr/bin/env python3
"""Build one day's rows from two captures: GPR from the photo, soil from a later reading.

Used when the noon photo is good but its soil readings failed (NaN) and a later
retake has valid soil readings but worse light. Every image column (GPR, pixel
counts, canopy size, flag) comes from the photo rows in --photo-csv; only sm_pct
comes from the current rows in growth_dataset.csv. The timestamp stays the photo's.

    python3 merge_day_rows.py --base ~/thesis --day 12 \
        --photo-csv ~/thesis/growth_dataset.csv.before_D12_retake          # dry run
    python3 merge_day_rows.py ... --write                                  # apply

--write backs up growth_dataset.csv first (growth_dataset.csv.before_D<day>_merge).
"""
import argparse
import csv
import os
import shutil


def rows_for(path, day):
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        return rd.fieldnames, list(rd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.path.expanduser("~/thesis"))
    ap.add_argument("--day", type=int, required=True)
    ap.add_argument("--photo-csv", required=True, help="CSV holding the photo's rows for that day")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    ds = os.path.join(a.base, "growth_dataset.csv")
    head, rows = rows_for(ds, a.day)
    _, prow = rows_for(a.photo_csv, a.day)
    d = str(a.day)
    photo = {r["pot_id"]: r for r in prow if r["day"] == d}
    cur = {r["pot_id"]: r for r in rows if r["day"] == d}
    if len(photo) != 9 or len(cur) != 9:
        raise SystemExit(f"need 9 rows for day {d} in both files (photo {len(photo)}, current {len(cur)})")

    merged = {}
    for pid, p in photo.items():
        m = dict(p)
        m["sm_pct"] = cur[pid]["sm_pct"]
        merged[pid] = m
        print(f"{pid}: {p['timestamp']} cell_gpr {cur[pid]['cell_gpr']} -> {p['cell_gpr']}, "
              f"sm_pct {p['sm_pct']} -> {m['sm_pct']} (from {cur[pid]['timestamp']})")

    if not a.write:
        print("dry run: nothing written (add --write)")
        return
    bak = f"{ds}.before_D{a.day:02d}_merge"
    shutil.copy2(ds, bak)
    out = [merged[r["pot_id"]] if r["day"] == d else r for r in rows]
    with open(ds, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(out)
    print(f"written {ds} (backup {bak})")


if __name__ == "__main__":
    main()
