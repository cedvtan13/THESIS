# Growth model results (pre-harvest), Nov 17, 2026

**Protocol:** `DATA/2026-11-17-growth-model-protocol.md`, committed in `1a4e050` (Nov 17, 17:42) **before** this run.

**Code:** `tools/growth_model.py`, same commit, unchanged.

**Data:** `Dual_Archi/growth_dataset.csv` at commit `978b2b0`. The md5 hashes of the files used for this run match the committed ones (data `b513e3bb…`, code `3244f895…`).

**Run by:** Claude, Nov 17, 2026. Outputs are in this folder.

## 1. Result against the decision rule (protocol section 7)

| Design A (fit D1 to D15, test D16 to D20) | Median skill vs persistence, logistic (M1) | Median skill vs persistence, Gompertz (M2) |
|---|---|---|
| Run 1, all rows | **−0.22** | **−0.31** |
| Run 2, flagged rows removed | **−0.16** | **−0.15** |

Neither S-shaped model beats "the canopy stays as it is", in either run.

By the rule set in advance, the conclusion is: **up to D20 the canopy growth did not follow a predictable trend, and the growth model does not beat persistence.**

## 2. Pooled errors (all 8 plants, test days D16 to D20)

| Model | Run 1 MAE (pp) | Run 1 skill | Run 2 MAE (pp) | Run 2 skill |
|---|---|---|---|---|
| M1 logistic | 0.120 | −0.39 | 0.063 | −0.09 |
| M2 Gompertz | 0.119 | −0.38 | 0.063 | −0.09 |
| M3 linear | 0.106 | −0.23 | 0.063 | −0.10 |
| B1 persistence | 0.086 | 0 | 0.058 | 0 |
| B2 mean of last 3 days | 0.087 | −0.01 | 0.060 | −0.03 |

**Rolling test (Design B, `metrics_B.csv`):**
- At 1, 2 and 3 days ahead, all three growth models are worse than persistence in both runs.
- The mean of the last 3 days is slightly better than persistence: skill +0.05 to +0.12 in Run 1, and +0.07 to +0.15 in Run 2.

**By group (Run 1, Design A):**
- **Low:** the models beat persistence slightly (skill +0.06 to +0.10).
- **Medium and High:** the models are worse (skill −0.2 to −1.3).

## 3. Why the models fail (from `plot_pots_A.png` and `fits.csv`)

1. **The canopy stopped growing early.**
   - For 6 of the 8 plants, the fitted logistic curve flattens at **0.14 to 0.25 % of the pot area**, with the steepest growth already between D5 and D9.
   - This matches Kent's Nov 17 photos: every plant is still at the seed-leaf stage, with leaves about 1 cm across.
   - With no growth left, the best forecast is "same as before", which is persistence.
2. **The day-to-day noise is as large as the signal.**
   - From D9 to D18, the median change from one day to the next is **0.050 pp**, against a mean canopy of **0.175 %**.
   - Single days jump and fall back, for example P-04 at 0.39 % on D7 then 0.00 % on D9; P-01 at 0.35 % on D12 then 0.06 % on D13.
   - Likely causes:
     - leaf edges on 1 cm seedlings, where a few pixels change the value a lot;
     - light and colour differences between days (blue frames on D19 and D20; D17 mildly blue);
     - P-01's transplant on D8;
     - outside greenery on P-08 and P-09.
3. **Some fits are degenerate:**
   - P-02, P-05 and P-08 have r at the upper bound (3 per day), so the curve is a step.
   - P-04 has r ≈ 0, a flat line.
   - P-06 and P-09 extrapolate upward, because of late rises (P-09's include the inflated D13 and D15 rows).
4. **No fit failed to converge** (0 failures).

## 4. Moisture question (descriptive only, protocol section 7)

Mean cell GPR from D8 to D18 (Run 1):

| Group | Mean | Median |
|---|---|---|
| High | **0.244 %** | 0.230 % |
| Low | 0.164 % | 0.175 % |
| Medium | 0.114 % | 0.110 % |

- **High has the most canopy.** Low and Medium are not in the expected order: Medium is the lowest.
- Two cautions for the Low group: P-01 has been waterlogged since Nov 8, and P-03 died and is excluded, so "Low" is not a clean low-moisture group.
- With 2 to 3 plants per group, no test is run.

## 5. Deviations from protocol

- **None in the analysis.**
- It was run on a copy of the committed files in Claude's environment, because Kent's laptop VM has no scipy. The hashes above show the copy is identical.

## 6. Literature for the early-checking request (Sir AJ, Nov 5)

Checked by reading the source pages on Nov 17. Each source is listed with what it supports.

1. **Florence, A., Revill, A., Hoad, S., Rees, R., and Williams, M. (2021).** The effect of antecedence on empirical model forecasts of crop yield from observations of canopy properties. *Agriculture*, 11(3), 258. https://doi.org/10.3390/agriculture11030258
   - **What it did:** in winter wheat, models based on canopy observations taken at different growth stages forecast yield before harvest.
   - **Key finding:** "the information content of data for yield prediction degraded strongly with time before harvest". The forecast error fell from about 26 % (early May) to about 4 % (early July).
   - **Supports:** canopy data collected before harvest *can* form a yield model, but earlier data gives weaker forecasts.
2. **Suarez, L. A., Robertson-Dean, M., Brinkhoff, J., et al., and Robson, A. (2024).** Forecasting carrot yield with optimal timing of Sentinel-2 image acquisition. *Precision Agriculture*, 25(2), 570–588. https://doi.org/10.1007/s11119-023-10083-z
   - **What it did:** in carrot, the best model used imagery from 70 days after sowing, giving a forecast 20 to 60 days before harvest. The error on new crops was about 27 % of yield.
   - **Supports:** an image-based yield forecast before harvest, timed to the growth stage.
3. **Kim, J. G., Moon, S., Park, J., Kim, T., and Chung, S. (2024).** Development of a machine vision-based weight prediction system of butterhead lettuce (*Lactuca sativa* L.) using deep learning models for industrial plant factory. *Frontiers in Plant Science*, 15, 1365266. https://doi.org/10.3389/fpls.2024.1365266
   - **What it did:** from top-view images, projected leaf area alone predicted lettuce fresh weight with R² 0.77 (linear) and 0.83 (cubic). Deep-learning models reached R² 0.95.
   - **Supports:** top-view canopy area is a valid predictor of leafy-vegetable fresh weight, which is our GPR → yield link. A curved (non-linear) term helps, which is consistent with our GPR² term.
4. **Lin, Z., Fu, R., Ren, G., Zhong, R., Ying, Y., and Lin, T. (2022).** Automatic monitoring of lettuce fresh weight by multi-modal fusion based deep learning. *Frontiers in Plant Science*, 13, 980581. https://doi.org/10.3389/fpls.2022.980581
   - **What it did:** in lettuce, all geometric image traits, including projected area, correlated significantly with fresh weight (P < 0.001).
   - **Supports:** the same link as source 3.

**What this means for our case:**
- The literature supports building a model from pre-harvest canopy data in principle.
- It also shows two conditions that our run does not yet meet:
  - the canopy has to be **growing** for early data to carry information;
  - a yield model still needs **real harvest weights** to be fitted and checked.

Our canopy stalled at the seed-leaf stage, so a pre-D30 growth model cannot carry information about the final weight here. That is consistent with Florence et al. (2021): information degrades with lead time, and here there has been almost no growth to learn from.

## 7. Files in this folder

| File | Contents |
|---|---|
| `fits.csv` | per plant, model and run: parameters, converged yes/no |
| `test_A.csv` | Design A predictions and errors for every test day |
| `metrics_A.csv` | MAE, RMSE and skill per plant, group and all |
| `metrics_B.csv` | Design B errors by horizon, per model |
| `plot_pots_A.png` | one panel per plant: training points, fitted curves, test points, baselines |
| `plot_groups.png` | group mean GPR per day |
