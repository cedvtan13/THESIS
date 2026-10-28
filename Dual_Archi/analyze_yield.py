#!/usr/bin/env python3
"""
analyze_yield.py -- fit the yield model and validate it.  Deliverables 5 and 6.

Thesis: Computer Vision-Based Growth Monitoring and Yield Prediction for
        Pechay Under Differential Soil Moisture Treatments in a Greenhouse

Does four things:
  1. Fills the smooth_gpr column with a 3-day centred moving average per plant.
     capture_gpr.py deliberately leaves this blank because a centred window
     needs days on both sides, so it can only be computed once the run is over.
  2. Fits the six-term model from Section III.F by ordinary least squares.
  3. Validates it with leave-one-PLANT-out cross-validation.
  4. Fits the original eight-term model the same way, so the manuscript's
     overfitting claim is TESTED rather than asserted.

THE MODEL
    Y = b0 + b1*D + b2*GPR + b3*SM + b4*GPR^2 + b5*(GPR x SM) + e

    Y is one number per plant -- its fresh weight at harvest. D, GPR and SM
    vary daily. So all 35 rows for a plant share the same Y, and the model
    reads as: "from a snapshot on day D showing this canopy and this moisture,
    what will this plant finally weigh?"

WHY LEAVE-ONE-PLANT-OUT AND NOT A RANDOM SPLIT
    The 35 rows within one plant are strongly autocorrelated -- day 20 looks
    much like day 19. A random row-wise split would put day 19 in training and
    day 20 in test, so the model would be scored on rows nearly identical to
    ones it had already seen. That inflates the reported skill without the
    model generalising at all. Holding out a whole plant is the only split
    that measures what the study actually claims: prediction for a plant the
    model has never seen.

TWO ERROR FIGURES, BOTH REPORTED
    The manuscript defines MAE over "the total number of harvested plant
    validation specimens", which reads as one prediction per plant, but the
    dataset has 35 rows per plant. Both are computed here:
      per-plant  -- average the held-out plant's 35 daily predictions into one
                    predicted weight, compare with the measured weight (n = 9)
      per-row    -- every row scored individually (n = 315)
    Report the per-plant figure as the headline and state which is which.

    Only numpy is required. No scikit-learn, so this runs on the Pi as-is.

USAGE
    python3 analyze_yield.py
    python3 analyze_yield.py --growth growth_dataset.csv --harvest harvest_weights.csv
    python3 analyze_yield.py --self-test        synthetic data, no files needed
"""

import argparse
import csv
import json
import os
import sys

import numpy as np

BASE = os.path.expanduser("~/thesis")
GROWTH_CSV = os.path.join(BASE, "growth_dataset.csv")
HARVEST_CSV = os.path.join(BASE, "harvest_weights.csv")
OUT_JSON = os.path.join(BASE, "model_results.json")
OUT_CSV = os.path.join(BASE, "model_predictions.csv")

SMOOTH_WINDOW = 3          # 3-day centred moving average

# Six-term specification, Section III.F.
TERMS_6 = ["1", "D", "GPR", "SM", "GPR^2", "GPR*SM"]
# Original eight-term specification, kept for the overfitting comparison.
TERMS_8 = ["1", "D", "GPR", "SM", "D^2", "GPR^2", "D*GPR", "GPR*SM"]


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load_growth(path, col="cell_gpr"):
    """GPR from `col`; rows without it (run-1 files) fall back to raw_gpr."""
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                gpr = float(r[col] if r.get(col) not in (None, "") else r["raw_gpr"])
                sm = float(r["sm_pct"])       # "NaN" raises, row dropped
                d = int(r["day"])
            except (KeyError, ValueError):
                continue
            rows.append({"pot_id": r["pot_id"], "day": d, "gpr": gpr, "sm": sm,
                         "flag": int(r.get("flag", 0) or 0)})
    return rows


def load_harvest(path):
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                out[r["pot_id"]] = float(r["fresh_weight_g"])
            except (KeyError, ValueError):
                continue
    return out


def smooth_per_plant(rows, window=SMOOTH_WINDOW):
    """3-day centred moving average of GPR, computed within each plant.

    At day 1 and day 35 the window is truncated rather than dropped, so no
    observation is lost at the ends of the series."""
    half = window // 2
    by_pot = {}
    for r in rows:
        by_pot.setdefault(r["pot_id"], []).append(r)
    for pot, rs in by_pot.items():
        rs.sort(key=lambda x: x["day"])
        vals = [x["gpr"] for x in rs]
        for i, r in enumerate(rs):
            lo, hi = max(0, i - half), min(len(vals), i + half + 1)
            r["gpr_s"] = float(np.mean(vals[lo:hi]))
    return rows


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------
def design(rows, terms, use_smoothed=True):
    D = np.array([r["day"] for r in rows], float)
    G = np.array([r["gpr_s"] if use_smoothed else r["gpr"] for r in rows], float)
    S = np.array([r["sm"] for r in rows], float)
    col = {"1": np.ones_like(D), "D": D, "GPR": G, "SM": S,
           "D^2": D ** 2, "GPR^2": G ** 2, "D*GPR": D * G, "GPR*SM": G * S}
    return np.column_stack([col[t] for t in terms])


def fit_ols(X, y):
    """Least squares via lstsq, which handles rank deficiency gracefully
    instead of raising on a singular normal-equations matrix."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def loocv_by_plant(rows, weights, terms, use_smoothed=True):
    """Hold out one whole plant at a time. Returns per-row and per-plant error."""
    pots = sorted({r["pot_id"] for r in rows})
    row_pred, row_true, per_plant = [], [], []

    for held in pots:
        tr = [r for r in rows if r["pot_id"] != held]
        te = [r for r in rows if r["pot_id"] == held]
        if not te:
            continue

        Xtr = design(tr, terms, use_smoothed)
        ytr = np.array([weights[r["pot_id"]] for r in tr], float)
        beta = fit_ols(Xtr, ytr)

        Xte = design(te, terms, use_smoothed)
        pred = Xte @ beta
        true = np.array([weights[r["pot_id"]] for r in te], float)

        row_pred.extend(pred.tolist())
        row_true.extend(true.tolist())
        per_plant.append({"pot_id": held,
                          "actual_g": float(weights[held]),
                          "predicted_g": float(np.mean(pred)),
                          "n_rows": len(te)})

    row_pred = np.array(row_pred)
    row_true = np.array(row_true)
    pa = np.array([p["actual_g"] for p in per_plant])
    pp = np.array([p["predicted_g"] for p in per_plant])

    return {
        "per_row": metrics(row_true, row_pred),
        "per_plant": metrics(pa, pp),
        "plants": per_plant,
    }


def metrics(actual, pred):
    """R-squared and MAE.

    R^2 is computed against the mean of the ACTUAL values, so out-of-sample it
    can legitimately go negative -- that means the model does worse than simply
    predicting the mean weight, which is a real and reportable result, not a
    bug."""
    ss_res = float(np.sum((actual - pred) ** 2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"r2": r2,
            "mae": float(np.mean(np.abs(actual - pred))),
            "rmse": float(np.sqrt(np.mean((actual - pred) ** 2))),
            "n": int(len(actual))}


# ---------------------------------------------------------------------------
def report(name, terms, rows, weights, use_smoothed=True):
    X = design(rows, terms, use_smoothed)
    y = np.array([weights[r["pot_id"]] for r in rows], float)
    beta = fit_ols(X, y)
    insample = metrics(y, X @ beta)
    cv = loocv_by_plant(rows, weights, terms, use_smoothed)

    print(f"\n=== {name} ({len(terms)} terms) ===")
    print("  coefficients (fitted on all data):")
    for t, b in zip(terms, beta):
        label = "b0 (intercept)" if t == "1" else t
        print(f"    {label:<16} {b:+12.4f}")
    print(f"  in-sample     R2 = {insample['r2']:7.4f}   "
          f"MAE = {insample['mae']:7.2f} g   (n={insample['n']})")
    print(f"  LOOCV per-row R2 = {cv['per_row']['r2']:7.4f}   "
          f"MAE = {cv['per_row']['mae']:7.2f} g   (n={cv['per_row']['n']})")
    print(f"  LOOCV per-pl. R2 = {cv['per_plant']['r2']:7.4f}   "
          f"MAE = {cv['per_plant']['mae']:7.2f} g   (n={cv['per_plant']['n']})")

    return {"terms": terms,
            "coefficients": {t: float(b) for t, b in zip(terms, beta)},
            "in_sample": insample, "loocv": cv}


def synthetic(n_plants=9, n_days=35, seed=1):
    """Nine plants on a plausible sigmoid, for testing the machinery without
    waiting 35 days. Not a substitute for real data."""
    rng = np.random.default_rng(seed)
    bands = {0: (35, 260), 1: (55, 330), 2: (75, 300)}   # SM mean, final grams
    rows, weights = [], {}
    for p in range(n_plants):
        pid = f"P-0{p+1}"
        sm_mu, final = bands[p // 3]
        final += rng.normal(0, 18)
        weights[pid] = float(final)
        for d in range(1, n_days + 1):
            gpr = 85 / (1 + np.exp(-0.28 * (d - 18))) + rng.normal(0, 1.2)
            rows.append({"pot_id": pid, "day": d,
                         "gpr": float(max(0.0, gpr)),
                         "sm": float(sm_mu + rng.normal(0, 2.5)),
                         "flag": 0})
    return rows, weights


def main():
    ap = argparse.ArgumentParser(description="Fit and validate the yield model")
    ap.add_argument("--growth", default=GROWTH_CSV)
    ap.add_argument("--harvest", default=HARVEST_CSV)
    ap.add_argument("--raw-gpr", action="store_true",
                    help="use raw instead of smoothed GPR")
    ap.add_argument("--gpr-column", default="cell_gpr",
                    help="growth_dataset.csv column used as GPR (default cell_gpr = "
                         "pot-area GPR; raw_gpr = the pot circle)")
    ap.add_argument("--self-test", action="store_true",
                    help="run on synthetic data, write nothing")
    args = ap.parse_args()

    if args.self_test:
        rows, weights = synthetic()
        print(f"[self-test] {len(rows)} synthetic rows, "
              f"{len(weights)} plants -- NOT real data")
    else:
        for path in (args.growth, args.harvest):
            if not os.path.exists(path):
                sys.exit(f"missing {path}. Run --self-test to check the "
                         f"analysis without real data.")
        rows = load_growth(args.growth, args.gpr_column)
        print(f"[analyze] GPR column: {args.gpr_column}")
        weights = load_harvest(args.harvest)
        missing = {r["pot_id"] for r in rows} - set(weights)
        if missing:
            sys.exit(f"no harvest weight for {sorted(missing)} -- "
                     f"run record_harvest.py first")
        print(f"[analyze] {len(rows)} usable rows, {len(weights)} plants")
        flagged = sum(r["flag"] for r in rows)
        if flagged:
            print(f"[analyze] {flagged} rows carry an anomaly flag; they are "
                  f"INCLUDED. Re-run excluding them to see the difference.")

    rows = smooth_per_plant(rows)
    use_smoothed = not args.raw_gpr
    print(f"[analyze] GPR: {'3-day centred average' if use_smoothed else 'raw'}")

    six = report("Six-term specification (manuscript)", TERMS_6,
                 rows, weights, use_smoothed)
    eight = report("Eight-term specification (original)", TERMS_8,
                   rows, weights, use_smoothed)

    print("\n=== overfitting check ===")
    d_in = eight["in_sample"]["r2"] - six["in_sample"]["r2"]
    d_cv = eight["loocv"]["per_plant"]["r2"] - six["loocv"]["per_plant"]["r2"]
    print(f"  eight-term minus six-term, in-sample R2 : {d_in:+.4f}")
    print(f"  eight-term minus six-term, LOOCV R2     : {d_cv:+.4f}")
    EPS = 0.005      # below this the difference is numerical noise, not signal
    if abs(d_in) < EPS and abs(d_cv) < EPS:
        print("  -> the two specifications are indistinguishable on this data.")
        print("     Parsimony still favours six terms, but do NOT claim the")
        print("     eight-term model overfits: this run does not show it.")
    elif d_in > EPS and d_cv < -EPS:
        print("  -> eight terms fit the training data better but generalise")
        print("     worse. That is textbook overfitting, and it supports the")
        print("     manuscript's reason for dropping D^2 and D*GPR.")
    elif d_cv > 0:
        print("  -> eight terms generalise BETTER here. The manuscript's")
        print("     overfitting claim is not supported by this data and the")
        print("     text needs revising to match what was actually found.")
    else:
        print("  -> difference is not clear-cut; report both and say so.")

    if args.self_test:
        print("\n[self-test] machinery works. Nothing written.")
        return

    with open(OUT_JSON, "w") as f:
        json.dump({"six_term": six, "eight_term": eight}, f, indent=2)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pot_id", "actual_g", "predicted_g", "abs_error_g"])
        for p in six["loocv"]["plants"]:
            w.writerow([p["pot_id"], f"{p['actual_g']:.1f}",
                        f"{p['predicted_g']:.1f}",
                        f"{abs(p['actual_g'] - p['predicted_g']):.1f}"])
    print(f"\nwrote {OUT_JSON}")
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
