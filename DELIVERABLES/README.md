# AgriSentry deliverables (Table I), status at D8 (2026-11-05)

| # | Deliverable | Folder | Status |
|---|---|---|---|
| 1 | Two-point calibration log; automated irrigation log | `D1_calibration_and_irrigation/` | Calibration log written (date and names to fill in). Irrigation log running: 1 dose so far |
| 2 | Day 0 pH table; HSV tuning values; `pot_rois.json` | `D2_uniform_environment/` | HSV values and ROI file done. pH table template ready; sensor arrives next week |
| 3 | 9 per-pot GPR time-series; capture log; GPR plots | `../DATA/thesis/gpr_per_pot/` | D1–D8, updated daily (D2, D3 missed) |
| 4 | 9-pot harvest table; scale check sheet | — | Harvest on D30 (2026-11-27), recorded with `Dual_Archi/record_harvest.py` |
| 5–6 | Regression model; LOOCV R² and MAE | — | After harvest, with `Dual_Archi/analyze_yield.py` |
| 7 | Error log; reliability summary | `D7_reliability/` | Snapshot to D8 |

The CSV files here are copies taken on D8. The live versions are in `DATA/` (pulled from the Pi) and on the Pi itself.
