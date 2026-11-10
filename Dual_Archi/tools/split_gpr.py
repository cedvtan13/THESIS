#!/usr/bin/env python3
"""
split_gpr.py -- write the nine per-pot GPR time-series files of Table I, Deliverable 3
("Date, Timestamp, Pot ID, GPR, Smoothed GPR, Anomaly Flag") from growth_dataset.csv.

Read-only on the source files: growth_dataset.csv, glare_log.csv and field_log.csv are
never changed. Safe to re-run any time; the files are rewritten from scratch.

    gpr_pct           cell_gpr (pot-area cell), the study's main GPR measure
    smoothed_gpr_pct  copied from growth_dataset.csv's smooth_gpr. Blank until
                      analyze_yield.py fills it after harvest (the 3-day centred
                      average needs the whole run, Section III.D.5)
    anomaly_flag      ok, or any of (joined with ";"):
                        MISSED  no capture that day; GPR left blank, never back-filled
                        JUMP    capture_gpr.py's jump flag (flag = 1)
                        GLARE / MILD / DARK  from glare_log.csv
                        NOTE    field_log.csv has a note naming this pot that day
                                (e.g. P-03 D7 false green); read field_log_note
    field_log_note    field_log.csv lines for that day that name this pot or ALL

Usage:
    python3 tools/split_gpr.py                         # on the Pi (~/thesis)
    python3 tools/split_gpr.py --base DATA/thesis      # on the Mac, from the repo root
Output: <base>/gpr_per_pot/P-01_gpr.csv ... P-09_gpr.csv
"""
import argparse
import csv
import datetime as dt
import os

HEADER = ["date", "timestamp", "day", "pot_id", "gpr_pct", "smoothed_gpr_pct",
          "anomaly_flag", "field_log_note"]
POTS = [f"P-0{i}" for i in range(1, 10)]


def read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--base", default=os.path.expanduser("~/thesis"))
    ap.add_argument("--out", help="output folder (default <base>/gpr_per_pot)")
    args = ap.parse_args()
    out = args.out or os.path.join(args.base, "gpr_per_pot")
    os.makedirs(out, exist_ok=True)

    rows = read(os.path.join(args.base, "growth_dataset.csv"))
    if not rows:
        raise SystemExit("[split_gpr] growth_dataset.csv missing or empty")
    sown = dt.date.fromisoformat(open(os.path.join(args.base, "sowing_date.txt")).read().strip())
    glare = {(int(g["day"]), g["pot_id"]): g["level"]
             for g in read(os.path.join(args.base, "glare_log.csv")) if g["level"] != "ok"}
    notes = {}
    for n in read(os.path.join(args.base, "field_log.csv")):
        try:
            d = int(n["day"])
        except (TypeError, ValueError):
            continue
        for pid in (n["pot_id"] or "").split(";"):
            notes.setdefault((d, pid.strip()), []).append(n["note"].strip())

    data = {(int(r["day"]), r["pot_id"]): r for r in rows}
    last_day = max(d for d, _ in data)

    for pid in POTS:
        path = os.path.join(out, f"{pid}_gpr.csv")
        n_ok = n_missed = 0
        with open(path, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(HEADER)
            for d in range(1, last_day + 1):
                r = data.get((d, pid))
                flags = []
                if r is None:
                    flags.append("MISSED")
                    date, ts, gpr, sm = (sown + dt.timedelta(days=d - 1)).isoformat(), "", "", ""
                    n_missed += 1
                else:
                    ts = r["timestamp"]
                    date, gpr, sm = ts[:10], r["cell_gpr"], r.get("smooth_gpr", "")
                    if r.get("flag") == "1":
                        flags.append("JUMP")
                    n_ok += 1
                if (d, pid) in glare:
                    flags.append(glare[(d, pid)])
                if any(not s.startswith("[glare_check]") for s in notes.get((d, pid), [])):
                    flags.append("NOTE")
                note = " | ".join(notes.get((d, pid), []) + notes.get((d, "ALL"), []))
                w.writerow([date, ts, d, pid, gpr, sm, ";".join(flags) or "ok", note])
        print(f"[split_gpr] {os.path.relpath(path)}: D1-D{last_day}, "
              f"{n_ok} captured, {n_missed} missed")


if __name__ == "__main__":
    main()
