#!/usr/bin/env python3
"""Draw the per-pot GPR time series (Deliverable 3) as a PNG, one panel per moisture group.

Reads the files made by split_gpr.py (<base>/gpr_per_pot/P-0X_gpr.csv) and plots
gpr_pct (cell_gpr) by day. Missed days are left as gaps, never filled in.

    python3 Dual_Archi/tools/plot_gpr.py --base DATA/thesis \
        --out DELIVERABLES/D3_gpr_timeseries/gpr_by_group.png
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GROUPS = [
    ("Low (30–40 %)", ["P-01", "P-02", "P-03"]),
    ("Optimal (50–60 %)", ["P-04", "P-05", "P-06"]),
    ("High (70–80 %)", ["P-07", "P-08", "P-09"]),
]
# Colour, line style and marker all differ, so a pot is never told apart by colour alone.
COLOURS = ["#2a78d6", "#eb6834", "#1baf7a"]
DASHES = ["-", "--", ":"]
MARKERS = ["o", "s", "^"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#6b6a66", "#e1e0d9", "#fcfcfb"
LIGHT_FLAGS = ("GLARE", "MILD", "DARK")


def read_pot(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            day = int(r["day"])
            gpr = float(r["gpr_pct"]) if r["gpr_pct"] else None
            flag = r["anomaly_flag"]
            # Hollow marker: light problem logged that day, or a green object that is not a plant.
            not_plant = "NOT a plant" in r["field_log_note"]
            if not_plant:
                NOT_PLANT.append((r["pot_id"], day))
            odd = any(k in flag for k in LIGHT_FLAGS) or not_plant
            rows.append((day, gpr, flag, odd))
    return rows


NOT_PLANT = []  # (pot, day) rows the field log marks as a green object, not a plant


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="DATA/thesis")
    ap.add_argument("--out", default="DELIVERABLES/D3_gpr_timeseries/gpr_by_group.png")
    ap.add_argument("--bands-day", type=int, default=8, help="day the treatment bands were switched on")
    ap.add_argument("--label", default="",
                    help="text added to the title, e.g. 'CLEAN MASK (exploratory)'")
    a = ap.parse_args()

    data = {p: read_pot(Path(a.base) / "gpr_per_pot" / f"{p}_gpr.csv") for _, ps in GROUPS for p in ps}
    last = max(d for rows in data.values() for d, *_ in rows)
    missed = sorted({d for rows in data.values() for d, g, f, _ in rows if "MISSED" in f})
    top = max([g for rows in data.values() for _, g, *_ in rows if g is not None] + [0.1])
    ymax = max(0.8, round(top * 1.25 + 0.05, 1))

    plt.rcParams.update({"font.family": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 11})
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), sharey=True, facecolor=SURFACE)
    fig.subplots_adjust(left=0.06, right=0.97, top=0.74, bottom=0.2, wspace=0.08)

    for ax, (name, pots) in zip(axes, GROUPS):
        ax.set_facecolor(SURFACE)
        for d in missed:
            ax.axvspan(d - 0.5, d + 0.5, color="#000000", alpha=0.05, lw=0)
        if missed:
            ax.text((missed[0] + missed[-1]) / 2, ymax * 0.5, "missed\n(Pi off)", ha="center", va="center",
                    fontsize=9.5, color=MUTED)
        if a.bands_day <= last:
            ax.axvline(a.bands_day - 0.5, color=MUTED, lw=1, ls=(0, (4, 3)))
            ax.text(a.bands_day - 0.6, ymax * 0.97, "treatments on →", ha="right", va="top", fontsize=9.5,
                    color=MUTED)

        ends = []
        for i, p in enumerate(pots):
            rows = data[p]
            days = [d for d, *_ in rows]
            vals = [g if g is not None else float("nan") for _, g, *_ in rows]
            ax.plot(days, vals, color=COLOURS[i], ls=DASHES[i], lw=2, zorder=3)
            seen_plant = False
            glare_days = []
            for d, g, flag, odd in rows:
                if g is None:
                    continue
                ax.plot(d, g, marker=MARKERS[i], ms=8 if odd else 6.5, mec=COLOURS[i], mew=2,
                        mfc=SURFACE if odd else COLOURS[i], zorder=4, ls="none")
                note = next((r for r in NOT_PLANT if r[0] == p and r[1] == d), None)
                if note:
                    ax.annotate("not a plant", (d, g), xytext=(-10, 0), textcoords="offset points",
                                ha="right", va="center", fontsize=9.5, color=MUTED)
                elif "GLARE" in flag and g == 0 and seen_plant:
                    # A plant was already there, so this zero is the glare, not an empty pot.
                    glare_days.append(d)
                seen_plant = seen_plant or g > 0
            # One "glare" label per run of consecutive glare days, centred over the run.
            runs = []
            for d in glare_days:
                if runs and d == runs[-1][-1] + 1:
                    runs[-1].append(d)
                else:
                    runs.append([d])
            for run in runs:
                ax.annotate("glare", ((run[0] + run[-1]) / 2, 0), xytext=(0, 9), textcoords="offset points",
                            ha="center", va="bottom", fontsize=9.5, color=MUTED)
            end = next(((d, g) for d, g, *_ in reversed(rows) if g is not None), None)
            if end:
                ends.append([end[1], end[0], p])

        # Spread the end labels apart so pots that finish at the same value stay readable.
        gap = ymax * 0.05
        ends.sort()
        for k in range(1, len(ends)):
            ends[k][0] = max(ends[k][0], ends[k - 1][0] + gap)
        for y, d, p in ends:
            ax.annotate(p, (d, y), xytext=(10, 0), textcoords="offset points", va="center",
                        fontsize=10, color=INK, annotation_clip=False)

        ax.set_title(name, loc="left", fontsize=13, color=INK, pad=30)
        ax.set_xlim(0.5, last + 1.2)
        ax.set_xticks(range(1, last + 1), [f"D{d}" for d in range(1, last + 1)])
        ax.set_ylim(0, ymax)
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=MUTED, length=0)
        # One legend per panel, so identity never depends on colour alone.
        handles = [plt.Line2D([], [], color=COLOURS[i], ls=DASHES[i], lw=2, marker=MARKERS[i], ms=6.5)
                   for i in range(3)]
        ax.legend(handles, pots, loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False, ncol=3,
                  fontsize=10, handlelength=2.6, borderaxespad=0.1)

    axes[0].set_ylabel("Green pixel ratio, pot area (%)", color=MUTED)
    axes[0].yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    fig.suptitle(f"Pechay Growth Monitoring (Run 2): Green Pixel Ratio per Pot, D1–D{last} (Noon Capture)"
                 + (f" — {a.label}" if a.label else ""),
                 x=0.06, y=0.96, ha="left", fontsize=15, color=INK)
    fig.text(0.06, 0.885, "cell_gpr: green pixels in each pot's area ÷ area. Missed days are left blank, "
             "never filled in.", fontsize=10.5, color=MUTED)
    fig.text(0.06, 0.06, "Hollow marker = glare or dim light logged that day (glare_log.csv), or a green "
             "object that is not a plant (P-03 on D7).", fontsize=10, color=MUTED)
    fig.text(0.06, 0.025, "D8: seedlings moved into P-01, P-03, P-06 (~11:00) and small cloths over P-01, "
             "P-04, P-07 (~11:40), before the noon photo. Details in field_log.csv.", fontsize=10, color=MUTED)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(f"wrote {out}  (D1–D{last}, missed days: {missed})")


if __name__ == "__main__":
    main()
