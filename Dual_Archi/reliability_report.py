#!/usr/bin/env python3
"""
reliability_report.py -- system reliability summary.  Deliverable 7.

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Table I asks for "the system error log with reliability summary". The raw
error_log.csv is the log; this produces the summary. Reads the four artefacts
the running system leaves behind and reports:

    capture completeness   how many of the noon captures due SO FAR landed
                           (D1 = sowing day, up to today; run 2 = 30 days)
    dataset completeness   how many rows carry a usable SM value
    irrigation activity    events and volume per pot and per treatment group
    band adherence         how often each pot sat inside its assigned band
    faults                 error codes, quarantines, anomaly flags

Run it at the end of the cycle for the write-up, and once a week during the
run so a silent failure surfaces in days rather than in October.

USAGE
    python3 reliability_report.py
    python3 reliability_report.py --days 30 --out reliability_summary.txt
"""

import argparse
import csv
import os
from datetime import date, datetime
from collections import Counter, defaultdict

BASE = os.path.expanduser("~/thesis")
DATA = os.path.expanduser("~/agrisentry_data")

GROWTH_CSV = os.path.join(BASE, "growth_dataset.csv")
SM_CSV = os.path.join(DATA, "sm_log.csv")
EVT_CSV = os.path.join(DATA, "irrigation_log.csv")
ERR_CSV = os.path.join(DATA, "error_log.csv")
SOWING_FILE = os.path.join(BASE, "sowing_date.txt")
FIELD_LOG = os.path.join(BASE, "field_log.csv")
GERM_BAND = (50, 60)          # germination mode: all pots, until bands-on

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


def today_day():
    """Today's D (sowing day = D1), or None if the sowing date is unknown."""
    try:
        sown = date.fromisoformat(open(SOWING_FILE).read().strip())
    except (OSError, ValueError):
        return None
    return (date.today() - sown).days + 1


def bands_on_date():
    """Date of the field-log line written by `agrisentry.sh bands-on`, if any."""
    for r in read(FIELD_LOG) or []:
        if "treatment bands ON" in r.get("note", ""):
            try:
                return date.fromisoformat(r["date"])
            except (KeyError, ValueError):
                pass
    return None


def section(out, title):
    out.append("")
    out.append(title)
    out.append("-" * len(title))


def main():
    ap = argparse.ArgumentParser(description="System reliability summary")
    ap.add_argument("--days", type=int, default=30, help="last day of the cycle (harvest day)")
    ap.add_argument("--first-day", type=int, default=1,
                    help="first day of automated capture (run 2: D1 = sowing day)")
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
        # Only days whose noon window has passed are "due". Today counts once
        # the 12:00-12:50 retries are over, or once today's row exists.
        td = today_day()
        last_due = args.days
        if td is not None:
            done_today = td in days or datetime.now().time() >= datetime.strptime("12:50", "%H:%M").time()
            last_due = min(args.days, td if done_today else td - 1)
        expected = set(range(args.first_day, last_due + 1))
        n_sched = max(len(expected), 1)
        missing = sorted(expected - set(days))
        out.append(f"  cycle                    : D{args.first_day}-D{args.days}"
                   + (f", today is D{td}" if td is not None else ""))
        out.append(f"  captures due so far      : {len(expected)}"
                   + (f" (D{args.first_day}-D{last_due})" if expected else ""))
        out.append(f"  captures recorded        : {len(set(days) & expected)}")
        out.append(f"  completeness so far      : "
                   f"{len(set(days) & expected) / n_sched * 100:.1f}%")
        if last_due < args.days:
            out.append(f"  still to come            : D{last_due + 1}-D{args.days} "
                       f"({args.days - last_due} captures)")
        if missing:
            out.append(f"  MISSED DAYS              : {missing}")
            out.append("    each missed day is an unrecoverable gap in the "
                       "GPR series -- state the cause in the results")
        else:
            out.append("  no missed days")

        rows_expected = len(expected) * 9
        out.append(f"  rows written             : {len(growth)} "
                   f"of {rows_expected} due so far ({args.days * 9} at harvest)")

        # --- SM completeness --------------------------------------------
        nan_sm = sum(1 for r in growth if r.get("sm_pct", "").strip() == "NaN")
        section(out, "Soil moisture column")
        out.append(f"  rows with usable SM      : {len(growth) - nan_sm}")
        out.append(f"  rows with NaN SM         : {nan_sm}")
        if nan_sm:
            pct = nan_sm / len(growth) * 100
            out.append(f"  NaN rate                 : {pct:.1f}%")
            out.append("    NaN rows drop out of the regression, reducing the "
                       f"effective dataset below {rows_expected}")
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
    bon = bands_on_date()
    out.append("  germination mode (all pots 50-60 %) until bands-on; "
               + (f"bands ON from {bon}" if bon else "bands not ON yet"))
    if sm is None:
        out.append(f"  sm_log.csv not found at {SM_CSV}")
    else:
        inb = Counter()
        tot = Counter()
        g_inb = Counter()
        g_tot = Counter()
        for r in sm:
            try:
                d = date.fromisoformat(r.get("wall_time", "")[:10])
            except ValueError:
                continue
            germ = bon is None or d < bon
            for pid in POT_IDS:
                v = r.get(pid, "").strip()
                if not v or v == "NaN":
                    continue
                try:
                    x = float(v)
                except ValueError:
                    continue
                if germ:
                    g_tot[pid] += 1
                    if GERM_BAND[0] <= x <= GERM_BAND[1]:
                        g_inb[pid] += 1
                    continue
                tot[pid] += 1
                lo, hi = BANDS[pid]
                if lo <= x <= hi:
                    inb[pid] += 1
        out.append(f"  snapshots read           : {len(sm)}")
        if sum(g_tot.values()):
            out.append("")
            out.append("  germination phase (target 50-60 % for every pot):")
            out.append(f"  {'pot':<7}{'band':<10}{'in band':>9}{'samples':>9}{'%':>8}")
            for pid in POT_IDS:
                t = g_tot[pid]
                pct = (g_inb[pid] / t * 100) if t else 0.0
                out.append(f"  {pid:<7}{'50-60%':<10}{g_inb[pid]:>9}{t:>9}{pct:>7.1f}%")
        out.append("")
        out.append("  treatment phase:" + ("" if bon else " (not started)"))
        out.append(f"  {'pot':<7}{'band':<10}{'in band':>9}{'samples':>9}{'%':>8}")
        for pid in POT_IDS:
            lo, hi = BANDS[pid]
            t = tot[pid]
            pct = (inb[pid] / t * 100) if t else 0.0
            out.append(f"  {pid:<7}{f'{lo}-{hi}%':<10}{inb[pid]:>9}"
                       f"{t:>9}{pct:>7.1f}%")

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
