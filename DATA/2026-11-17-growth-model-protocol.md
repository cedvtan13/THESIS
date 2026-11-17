# Growth model protocol (fixed before analysis)

**Written:** Nov 17, 2026 (D20), by Claude with Kent. The team chose the options in sections 4 and 6.

**Purpose:** carry out the plan recorded in the counselling logbook on Nov 9, 2026: "an out-of-sample canopy growth model fitted on days 1 to 15 and evaluated on days 16 to 20". It needs no harvest weights.

**This file is committed before the model is run.** The commit time on GitHub shows the rules were set before anyone saw the results. Anything done differently from this protocol is reported in the results under "Deviations from protocol".

## 1. Question

Can each plant's canopy growth up to a given day predict its canopy on the following days, better than simply assuming the canopy stays as it is?

## 2. Data

| Item | Rule |
|---|---|
| File | `Dual_Archi/growth_dataset.csv` at repo commit `978b2b0` (Nov 17) |
| Variable | `cell_gpr`: Green Pixel Ratio of each pot's area, in percent; raw daily values, no smoothing |
| Days | D1 and D4 to D20. D2 and D3 do not exist (power outage) and are **not** filled in |
| D20 | the **12:42** set only (team decision, Nov 17). The 09:36 set (catch-up capture outside the noon window) is not used |
| Plants | **8 plants:** P-01, P-02, P-04, P-05, P-06, P-07, P-08, P-09. **P-03 is excluded:** the seedling died; its GPR is 0.00 from D17 and was only above 0 from D8, after transplanting |
| Groups (for group results) | Low: P-01, P-02. Medium: P-04, P-05, P-06. High: P-07, P-08, P-09 |
| Soil moisture | **not used** in this model. Part of the D20 readings are invalid because of the probe fault that started Nov 16 23:44 |

## 3. Models (one fit per plant)

| Code | Model | Formula (t = day) | Why |
|---|---|---|---|
| M1 | Logistic | GPR = K / (1 + exp(−r (t − t0))) | S-shaped crop growth (Archontoulis and Miguez, 2015) |
| M2 | Gompertz | GPR = K · exp(−b · exp(−r t)) | S-shaped curve with an earlier inflection, common for early growth |
| M3 | Linear trend | GPR = a + c t, fitted on D8 to the last training day only | the simplest growth model; D8 is when the treatments started and most seedlings had emerged |
| B1 | Persistence (baseline) | every future day = the last training value | the "nothing changes" benchmark |
| B2 | Recent mean (baseline) | every future day = mean of the last 3 training values | the same benchmark, less sensitive to one noisy day |

**Fitting details:**
- M1 and M2 use non-linear least squares (`scipy.optimize.curve_fit`) with bounds: K from 0 to 5 %, r from 0 to 3 per day, t0 from 0 to 40, b from 0 to 50.
- Start values: K = 1.5 × the highest training value, r = 0.3, t0 = 10, b = 5.
- If a fit fails to converge, that model is recorded as **failed** for that plant and day and left out of the averages, and the count of failures is reported.
- M3 uses ordinary least squares.

## 4. Two test designs (both reported)

### A. Primary: the logbook design
- **Train:** D1 and D4 to D15.
- **Test:** D16 to D20.
- No test day is used in fitting.

### B. Secondary: rolling-origin test
This is the standard way to test forecasts on a time series (Hyndman and Athanasopoulos, *Forecasting: Principles and Practice*).
- For every last training day T from D10 to D19:
  - fit on all available days up to T;
  - forecast the next 1, 2 and 3 days (only days that exist, up to D20);
  - require at least 6 training days.
- Errors are pooled by forecast horizon (1, 2 or 3 days ahead).

## 5. Error measures

All in GPR percentage points (pp):

| Measure | Meaning |
|---|---|
| MAE | mean absolute error |
| RMSE | root mean square error |
| Skill vs B1 | 1 − MAE(model) / MAE(B1). Above 0 means the model beats "nothing changes"; 0 or below means it does not |

**Reported:**
- per plant;
- per moisture group (pooled errors of that group's plants);
- over all 8 plants (pooled);
- the median skill across plants.

## 6. Flagged rows: two runs (both reported)

- **Run 1 (main):** every row as measured.
- **Run 2 (sensitivity):** the flagged rows below are removed from **both** training and testing, under the same rule as the deviations section of the manuscript:

| Row | Reason |
|---|---|
| P-08 D13 | green object outside the pot counted (field log) |
| P-09 D13 | weed protruding into the pot area (field_log.txt) |
| P-09 D15 | outside greenery in the pot area (field log) |
| all plants D19 | blue colour cast, blue/red 1.84; captured 12:47 |
| all plants D20 | blue colour cast, blue/red 1.57; dim; P-04 handled before the retake |

D12 (12:00 photo, normal colour) and D17 (blue/red 1.20, below the 1.25 limit) are kept in both runs.

## 7. Decision rule, stated in advance

| Result (Design A, Run 1) | Conclusion |
|---|---|
| The median skill vs B1 of the better S-shaped model (M1 or M2) **is above 0** | "the canopy growth model predicts D16 to D20 better than persistence" |
| Otherwise | "up to D20 the canopy growth did not follow a predictable trend; the model does not beat persistence". This is reported as a result, together with the canopy values and the plant observations |

The moisture question is **descriptive only**: do the fitted plateau (K) and rate (r) order as Low < Medium < High? With 2 to 3 plants per group, no significance test is run.

## 8. Outputs (in `DATA/model_preview/`)

| File | Contents |
|---|---|
| `fits.csv` | per plant, model and run: parameters, converged yes/no |
| `test_A.csv` | Design A predictions and errors for every test day |
| `metrics_A.csv` | MAE, RMSE and skill per plant, group and all |
| `metrics_B.csv` | Design B errors by horizon, per model |
| `plot_pots_A.png` | one panel per plant: training points, fitted curves, test points, baselines |
| `plot_groups.png` | group mean GPR per day with the fitted curves |
| `2026-11-17-growth-model-results.md` | results, deviations from protocol, and notes |

**Code:** `tools/growth_model.py` (Python 3 with numpy, scipy, matplotlib). It reads only the file in section 2 and writes only to `DATA/model_preview/`.

## 9. What this model is not

- It does **not** predict harvest weight. The six-term yield model (Chapter 3) still needs the D30 harvest weights (Nov 27).
- This is a pre-harvest result on canopy growth only. It supports the Nov 5 request from Sir AJ: evidence that data collected before D30 can form a model.
