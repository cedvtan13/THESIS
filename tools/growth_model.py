#!/usr/bin/env python3
"""growth_model.py -- pre-harvest canopy growth model (protocol: DATA/2026-11-17-growth-model-protocol.md).

Fits logistic (M1), Gompertz (M2) and linear (M3) growth curves to each plant's
daily cell_gpr and tests them on days they were not fitted on, against two
baselines: persistence (B1) and the mean of the last 3 training values (B2).

  Design A: train D1, D4-D15 -> test D16-D20
  Design B: rolling origin T = D10..D19, forecast 1-3 days ahead (>= 6 training days)
  Run 1: all rows as measured.  Run 2: flagged rows removed.

    python3 tools/growth_model.py            # from the THESIS folder
Writes only to DATA/model_preview/.
"""
import csv
import os
import sys
import warnings

import numpy as np
from scipy.optimize import curve_fit

warnings.filterwarnings("ignore")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "Dual_Archi", "growth_dataset.csv")
OUT = os.path.join(ROOT, "DATA", "model_preview")

PLANTS = ["P-01", "P-02", "P-04", "P-05", "P-06", "P-07", "P-08", "P-09"]   # P-03 excluded (dead)
GROUP = {"P-01": "Low", "P-02": "Low", "P-04": "Medium", "P-05": "Medium", "P-06": "Medium",
         "P-07": "High", "P-08": "High", "P-09": "High"}
D20_KEEP = "12:42"
FLAGGED = {("P-08", 13), ("P-09", 13), ("P-09", 15)} | {(p, d) for p in PLANTS for d in (19, 20)}
TRAIN_END_A, TEST_A = 15, list(range(16, 21))


def logistic(t, K, r, t0):
    return K / (1.0 + np.exp(-r * (t - t0)))


def gompertz(t, K, b, r):
    return K * np.exp(-b * np.exp(-r * t))


def load():
    rows = list(csv.DictReader(open(SRC, newline="")))
    data = {p: {} for p in PLANTS}
    for r in rows:
        p, d = r["pot_id"], int(r["day"])
        if p not in data:
            continue
        if d == 20 and not r["timestamp"].endswith(D20_KEEP):
            continue
        data[p][d] = float(r["cell_gpr"])
    return data


def fit_predict(days, vals, future):
    """Return {model: predictions or None} for the future days."""
    t, y = np.array(days, float), np.array(vals, float)
    out = {}
    k0 = max(1.5 * y.max(), 0.05)
    try:
        p, _ = curve_fit(logistic, t, y, p0=[k0, 0.3, 10], bounds=([0, 0, 0], [5, 3, 40]), maxfev=20000)
        out["M1_logistic"] = (logistic(np.array(future, float), *p), p)
    except Exception:
        out["M1_logistic"] = (None, None)
    try:
        p, _ = curve_fit(gompertz, t, y, p0=[k0, 5, 0.3], bounds=([0, 0, 0], [5, 50, 3]), maxfev=20000)
        out["M2_gompertz"] = (gompertz(np.array(future, float), *p), p)
    except Exception:
        out["M2_gompertz"] = (None, None)
    m = t >= 8
    if m.sum() >= 2:
        c = np.polyfit(t[m], y[m], 1)
        out["M3_linear"] = (np.polyval(c, np.array(future, float)), c)
    else:
        out["M3_linear"] = (None, None)
    out["B1_persistence"] = (np.full(len(future), y[-1]), None)
    out["B2_recent_mean"] = (np.full(len(future), y[-3:].mean()), None)
    return out


MODELS = ["M1_logistic", "M2_gompertz", "M3_linear", "B1_persistence", "B2_recent_mean"]


def series(data, p, run):
    s = data[p]
    return {d: v for d, v in sorted(s.items()) if not (run == 2 and (p, d) in FLAGGED)}


def design_a(data, run):
    preds, fits = [], []
    for p in PLANTS:
        s = series(data, p, run)
        tr = [(d, v) for d, v in s.items() if d <= TRAIN_END_A]
        te = [(d, v) for d, v in s.items() if d in TEST_A]
        if len(tr) < 4 or not te:
            continue
        res = fit_predict([d for d, _ in tr], [v for _, v in tr], [d for d, _ in te])
        for m, (pr, par) in res.items():
            fits.append({"run": run, "plant": p, "model": m, "converged": pr is not None,
                         "params": "" if par is None else " ".join(f"{x:.4g}" for x in np.atleast_1d(par))})
            if pr is None:
                continue
            for (d, v), yhat in zip(te, pr):
                preds.append({"run": run, "plant": p, "group": GROUP[p], "model": m, "day": d,
                              "actual": round(v, 4), "pred": round(float(yhat), 4),
                              "abs_err": round(abs(float(yhat) - v), 4)})
    return preds, fits


def design_b(data, run):
    rows = []
    for p in PLANTS:
        s = series(data, p, run)
        days = list(s)
        for T in range(10, 20):
            tr = [d for d in days if d <= T]
            if len(tr) < 6:
                continue
            fut = [d for d in days if T < d <= min(T + 3, 20)]
            if not fut:
                continue
            res = fit_predict(tr, [s[d] for d in tr], fut)
            for m, (pr, _) in res.items():
                if pr is None:
                    continue
                for d, yhat in zip(fut, pr):
                    rows.append({"run": run, "plant": p, "model": m, "origin": T, "horizon": d - T,
                                 "abs_err": abs(float(yhat) - s[d])})
    return rows


def summarize_a(preds):
    out = []
    for run in (1, 2):
        for scope in ["ALL", "Low", "Medium", "High"] + PLANTS:
            base = None
            vals = {}
            for m in MODELS:
                e = [r["abs_err"] for r in preds if r["run"] == run and r["model"] == m and
                     (scope == "ALL" or r["group"] == scope or r["plant"] == scope)]
                if e:
                    a = np.array(e)
                    vals[m] = (a.mean(), np.sqrt((a ** 2).mean()), len(a))
            if "B1_persistence" in vals:
                base = vals["B1_persistence"][0]
            for m, (mae, rmse, n) in vals.items():
                skill = "" if not base else round(1 - mae / base, 3)
                out.append({"run": run, "scope": scope, "model": m, "n": n, "MAE_pp": round(mae, 4),
                            "RMSE_pp": round(rmse, 4), "skill_vs_B1": skill})
    return out


def median_skill(metrics, run, model):
    s = [r["skill_vs_B1"] for r in metrics if r["run"] == run and r["model"] == model
         and r["scope"] in PLANTS and r["skill_vs_B1"] != ""]
    return (float(np.median(s)), len(s)) if s else (None, 0)


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def plots(data, preds):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 4, figsize=(16, 7), sharex=True)
    tt = np.linspace(1, 20, 200)
    for ax, p in zip(axs.flat, PLANTS):
        s = series(data, p, 1)
        tr = [(d, v) for d, v in s.items() if d <= TRAIN_END_A]
        te = [(d, v) for d, v in s.items() if d in TEST_A]
        ax.plot(*zip(*tr), "o", color="#2b6cb0", label="training")
        ax.plot(*zip(*te), "s", color="#c53030", label="test (D16-20)")
        fl = [(d, v) for d, v in s.items() if (p, d) in FLAGGED]
        if fl:
            ax.plot(*zip(*fl), "x", color="k", ms=9, label="flagged")
        res = fit_predict([d for d, _ in tr], [v for _, v in tr], list(tt))
        for m, c in (("M1_logistic", "#2f855a"), ("M2_gompertz", "#805ad5"), ("M3_linear", "#dd6b20")):
            if res[m][0] is not None:
                ax.plot(tt, res[m][0], color=c, lw=1.4, label=m.split("_")[1])
        ax.axhline(tr[-1][1], color="grey", ls="--", lw=1, label="persistence")
        ax.axvline(15.5, color="grey", lw=0.8)
        ax.set_title(f"{p} ({GROUP[p]})")
        ax.set_ylabel("cell GPR (%)")
    axs.flat[0].legend(fontsize=7)
    for ax in axs[1]:
        ax.set_xlabel("Day")
    fig.suptitle("Canopy growth model: fit D1-D15, test D16-D20 (Run 1, all rows)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "plot_pots_A.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for g, c in (("Low", "#c53030"), ("Medium", "#2b6cb0"), ("High", "#2f855a")):
        ps = [p for p in PLANTS if GROUP[p] == g]
        days = sorted(set.intersection(*[set(series(data, p, 1)) for p in ps]))
        m = [np.mean([data[p][d] for p in ps]) for d in days]
        ax.plot(days, m, "o-", color=c, label=f"{g} ({', '.join(ps)})")
    ax.axvline(15.5, color="grey", lw=0.8)
    ax.text(15.7, ax.get_ylim()[1] * 0.95, "test", color="grey")
    ax.set_xlabel("Day")
    ax.set_ylabel("mean cell GPR (%)")
    ax.set_title("Group mean canopy cover, D1-D20 (P-03 excluded)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "plot_groups.png"), dpi=150)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = load()
    preds, fits = [], []
    for run in (1, 2):
        p, f = design_a(data, run)
        preds += p
        fits += f
    metrics = summarize_a(preds)
    brows = []
    for run in (1, 2):
        brows += design_b(data, run)
    bsum = []
    for run in (1, 2):
        for h in (1, 2, 3):
            base = [r["abs_err"] for r in brows if r["run"] == run and r["horizon"] == h and r["model"] == "B1_persistence"]
            for m in MODELS:
                e = [r["abs_err"] for r in brows if r["run"] == run and r["horizon"] == h and r["model"] == m]
                if e:
                    bsum.append({"run": run, "horizon_days": h, "model": m, "n": len(e),
                                 "MAE_pp": round(float(np.mean(e)), 4),
                                 "skill_vs_B1": round(1 - np.mean(e) / np.mean(base), 3) if base else ""})
    write_csv(os.path.join(OUT, "fits.csv"), fits)
    write_csv(os.path.join(OUT, "test_A.csv"), preds)
    write_csv(os.path.join(OUT, "metrics_A.csv"), metrics)
    write_csv(os.path.join(OUT, "metrics_B.csv"), bsum)
    plots(data, preds)
    # console summary
    for run in (1, 2):
        print(f"\nDesign A, Run {run}: pooled over all plants")
        for r in metrics:
            if r["run"] == run and r["scope"] == "ALL":
                print(f"  {r['model']:15s} MAE {r['MAE_pp']:.4f}  RMSE {r['RMSE_pp']:.4f}  skill {r['skill_vs_B1']}")
        for m in ("M1_logistic", "M2_gompertz"):
            ms, n = median_skill(metrics, run, m)
            print(f"  median skill across plants, {m}: {ms if ms is None else round(ms, 3)} (n={n})")
    fails = sum(1 for f in fits if not f["converged"])
    print(f"\nfailed fits (Design A): {fails}")
    print(f"written to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
