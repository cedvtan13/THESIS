#!/usr/bin/env python3
"""
reliability_report.py -- system reliability summary.  Deliverable 7.

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Table I asks for "the system error log with reliability summary". The raw
error_log.csv is the log; this produces the summary. Reads the four artefacts
the running system leaves behind and reports:

    capture completeness   how many of the 35 scheduled noon captures landed
    dataset completeness   how many of the 315 rows carry a usable SM value
    irrigation activity    events and volume per pot and per treatment group
    band adherence         how often each pot sat inside its assigned band
    faults                 error codes, quarantines, anomaly flags

Run it at the end of the cycle for the write-up, and once a week during the
run so a silent failure surfaces in days rather than in October.

USAGE
    python3 reliability_report.py
    python3 reliability_report.py --days 35 --out reliability_summary.txt
"""

import argparse
import csv
import os
from collections import Counter, defaultdict

BASE = os.path.expanduser("~/thesis")
DATA = os.path.expanduser("~/agrisentry_data")

GROWTH_CSV = os.path.join(BASE, "growth_dataset.csv")
SM_CSV = os.path.join(DATA, "sm_log.csv")
EVT_CSV = os.path.join(DATA, "irrigation_log.csv")
ERR_CSV = os.path.join(DATA, "error_log.csv")

POT_IDS = [f"P-0{i}" for i in range(1, 10)]
BANDS = {
    "P-01": (30, 40), "P-02": (30, 40), "P-03": (30, 40),
    "P-04": (50, 60), "P-05": (50, 60), "P-06": (50, 60),
    "P-07": (70, 80), "P-08": (70, 80), "P-09": (70, 80),
}
GROUPS = {"P-01": "A_Low", "P-02": "A_Low", "P-03": "A_Low",
          "P-04": "B_Optimal", "P-05": "B_Optimal", "P-06": "B_Optimal",
          "P-07": "C_High", "P-08": "C_High", "P-09": "C_High"}


def read(path):
    if not os.path.exists(path):
        return None
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def section(out, title):
    out.append("")
    out.append(title)
    out.append("-" * len(title))


def main():
    ap = argparse.ArgumentParser(description="System reliability summary")
    ap.add_argument("--days", type=int, default=35)
    ap.add_argument("--out")
    args = ap.parse_args()

    out = ["SYSTEM RELIABILITY SUMMARY  (Deliverable 7)",
           "=" * 44]

    # --- capture completeness -------------------------------------------
    growth = read(GROWTH_CSV)
    section(out, "Image capture")
    if growth is None:
        out.append(f"  growth_dataset.csv not found at {GROWTH_CSV}")
    else:
        days = sorted({int(r["day"]) for r in growth})
        expected = set(range(1, args.days + 1))
        missing = sorted(expected - set(days))
        out.append(f"  scheduled captures       : {args.days}")
        out.append(f"  captures recorded        : {len(days)}")
        out.append(f"  completeness             : "
                   f"{len(days) / args.days * 100:.1f}%")
        if missing:
            out.append(f"  MISSED DAYS              : {missing}")
            out.append("    each missed day is an unrecoverable gap in the "
                       "GPR series -- state the cause in the results")
        else:
            out.append("  no missed days")

        rows_expected = args.days * 9
        out.append(f"  rows written             : {len(growth)} "
                   f"of {rows_expected} expected")

        # --- SM completeness --------------------------------------------
        nan_sm = sum(1 for r in growth if r.get("sm_pct", "").strip() == "NaN")
        section(out, "Soil moisture column")
        out.append(f"  rows with usable SM      : {len(growth) - nan_sm}")
        out.append(f"  rows with NaN SM         : {nan_sm}")
        if nan_sm:
            pct = nan_sm / len(growth) * 100
            out.append(f"  NaN rate                 : {pct:.1f}%")
            out.append("    NaN rows drop out of the regression, reducing the "
                       "effective dataset below 315")
            per_pot = Counter(r["pot_id"] for r in growth
                              if r.get("sm_pct", "").strip() == "NaN")
            for pid, n in sorted(per_pot.items()):
                out.append(f"      {pid}: {n} NaN rows")

        # --- anomaly flags ----------------------------------------------
        flagged = [r for r in growth if str(r.get("flag", "0")).strip() == "1"]
        section(out, "GPR anomaly flags")
        out.append(f"  flagged rows             : {len(flagged)}")
        if flagged:
            out.append("    a flag means GPR moved more in one day than plant "
                       "growth plausibly allows")
            out.append("    usual causes: the rig shifted, lighting changed, "
                       "or condensation on the lens")
            for r in flagged[:15]:
                out.append(f"      day {r['day']:>2}  {r['pot_id']}  "
                           f"GPR={r['raw_gpr']}")
            if len(flagged) > 15:
                out.append(f"      ... and {len(flagged) - 15} more")

    # --- irrigation ------------------------------------------------------
    evt = read(EVT_CSV)
    section(out, "Irrigation activity")
    if evt is None:
        out.append(f"  irrigation_log.csv not found at {EVT_CSV}")
    else:
        n_pot = Counter()
        ml_pot = defaultdict(float)
        clamped = 0
        for r in evt:
            pid = r.get("pot_id", "?")
            n_pot[pid] += 1
            try:
                ml_pot[pid] += float(r.get("dose_ml", 0))
            except ValueError:
                pass
        out.append(f"  total irrigation events  : {len(evt)}")
        out.append("")
        out.append(f"  {'pot':<7}{'group':<11}{'events':>8}{'total mL':>11}")
        for pid in POT_IDS:
            out.append(f"  {pid:<7}{GROUPS[pid]:<11}{n_pot[pid]:>8}"
                       f"{ml_pot[pid]:>11.0f}")

        out.append("")
        out.append("  by treatment group:")
        for g in ("A_Low", "B_Optimal", "C_High"):
            pots = [p for p in POT_IDS if GROUPS[p] == g]
            ev = sum(n_pot[p] for p in pots)
            ml = sum(ml_pot[p] for p in pots)
            out.append(f"    {g:<11} {ev:>4} events  {ml:>8.0f} mL")
        out.append("")
        out.append("    Group A should show the fewest events and the least")
        out.append("    volume, Group C the most. If that ordering does not")
        out.append("    hold, the treatments did not separate and the SM term")
        out.append("    in the model is not measuring what it claims.")

    # --- band adherence --------------------------------------------------
    sm = read(SM_CSV)
    section(out, "Treatment band adherence")
    if sm is None:
        out.append(f"  sm_log.csv not found at {SM_CSV}")
    else:
        inb = Counter()
        tot = Counter()
        for r in sm:
            for pid in POT_IDS:
                v = r.get(pid, "").strip()
                if not v or v == "NaN":
                    continue
                try:
                    x = float(v)
                except ValueError:
                    continue
                tot[pid] += 1
                lo, hi = BANDS[pid]
                if lo <= x <= hi:
                    inb[pid] += 1
        out.append(f"  snapshots read           : {len(sm)}")
        out.append("")
        out.append(f"  {'pot':<7}{'band':<10}{'in band':>9}{'samples':>9}{'%':>8}")
        for pid in POT_IDS:
            lo, hi = BANDS[pid]
            t = tot[pid]
            pct = (inb[pid] / t * 100) if t else 0.0
            out.append(f"  {pid:<7}{f'{lo}-{hi}%':<10}{inb[pid]:>9}"
                       f"{t:>9}{pct:>7.1f}%")
        out.append("")
        out.append("    Adherence will not be 100%: a pot sits below its band")
        out.append("    between the moment it dries out and the next scheduled")
        out.append("    sweep. Report the figure rather than explaining it away.")

    # --- faults ----------------------------------------------------------
    err = read(ERR_CSV)
    section(out, "Fault log")
    if err is None:
        out.append(f"  error_log.csv not found at {ERR_CSV}")
    else:
        codes = Counter(r.get("code", "?") for r in err)
        out.append(f"  total entries            : {len(err)}")
        if codes:
            out.append("")
            for code, n in codes.most_common():
                out.append(f"    {code:<20} {n:>5}")
        quarantined = [r for r in err if r.get("code") == "POD_QUARANTINE"]
        if quarantined:
            out.append("")
            out.append("  QUARANTINE EVENTS -- these pots stopped being watered:")
            for r in quarantined:
                out.append(f"    {r.get('wall_time','?')}  {r.get('detail','')}")
            out.append("    A quarantined pot receives no water for the rest of")
            out.append("    the run. Its data cannot be treated as part of its")
            out.append("    treatment group and must be disclosed.")
        if not len(err):
            out.append("  no faults recorded")

    text = "\n".join(out)
    print(text)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text + "\n")
        print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
