# Progress on the Adviser's Comments (Oct 20, 2026, D15) — Pechay Growth Monitoring & Yield Prediction

Our response to Engr. Macapagal's three comments from last week's meeting.

---

## 1. How do we prove GPR is correct?

**Method: compare the program's mask with leaves labelled by hand.** This is the standard way to validate image segmentation.

1. Saved noon frames are cut into per-pot crops (`tools/gpr_validate.py export`).
2. At least two team members paint every leaf pixel on their own, in a labelling page (`GPR_VALIDATION/annotate_*.html`). They never see the program's mask.
3. `tools/gpr_validate.py score` compares the automatic HSV mask with each person's labels. It applies the same HSV band, opening and ROI circle as the live pipeline, and reports:
   - **Pixel accuracy:** precision, recall, IoU and Dice. These show whether the program finds the leaves and nothing else.
   - **GPR agreement:** GPR(auto) vs GPR(hand) as mean absolute error and bias in percentage points, Pearson r, and Bland–Altman 95% limits.
   - **Inter-annotator agreement:** how closely two people agree with each other. This is the best accuracy anyone could expect.
4. **Proposed acceptance criterion:** the program-vs-human difference is no larger than the human-vs-human difference.

**Status:**
- The tool is built. The scoring was checked with a self-test: labels identical to the mask score IoU = 1.000 and error = 0.
- Two annotators are done: Cedric, and Kent (his second, independent attempt). Annotator 3 (Rey) is not yet available.
- Annotator 2's first attempt was discarded because it was not independent. The labelling page had reloaded annotator 1's saved work in the same browser, so 99.7% of annotator 2's pixels sat inside annotator 1's labels.
  - The page now keeps separate saved work for each name.
  - The scoring script now flags any pair of labellers that isn't independent.
  - Kent's redo shares no identical images with Cedric's labels.
- We repeat the check on later frames (around D20 and D26), when the plants are larger.

**Results: 2 annotators, D12 + D13, 18 pot images each, leaf blades only**

Thin stems are removed from all hand labels, because GPR measures leaf cover.

| | Program vs Cedric | Program vs Kent | Program vs average of both | **Cedric vs Kent (human benchmark)** |
|---|---|---|---|---|
| Pixel IoU | 0.64 | 0.64 | n/a | **0.79** |
| GPR mean absolute error | 0.29 pp | 0.27 pp | 0.28 pp | **0.19 pp** |
| GPR bias | −0.05 pp | +0.14 pp | **+0.04 pp** | Cedric is +0.19 pp larger than Kent on every pot |
| Pearson r | 0.82 | 0.85 | 0.84 | n/a |

How to read it:
- **No systematic error.** The program's GPR falls between the two humans, with a bias of +0.04 pp against their average. It doesn't over- or under-count leaf area.
- **The program is less precise per pot than the humans.**
  - The two humans agree better with each other (IoU 0.79, 0.19 pp) than the program agrees with either of them (IoU 0.64, about 0.28 pp).
  - So, at this seedling size, the acceptance criterion ("program as close to a human as two humans are to each other") is **not yet met**.
  - The extra error is scatter of about ±0.3 pp per pot, not a bias.
- **The humans disagree too, but in a consistent way.** Cedric painted larger than Kent on all 18 pots (+0.19 ± 0.11 pp). Even careful people place leaf edges differently by about one pixel.
- **The error is small in absolute terms but large relative to these plants.** Human-labelled GPR is only 0.5–2.1% here, so 0.28 pp is about 20% of a typical plant. This should shrink as the plants grow, but it has to be shown on later frames, not assumed.

Whole-plant comparison (Cedric only, stems included): IoU 0.53 and bias −0.44 pp. The difference from the leaf-only result is almost entirely the stems.

What the error map shows (`GPR_VALIDATION/errors_D13_Cedric.png`; green = agree, red = missed by the program, blue = extra):
- **Almost everything the program misses is the thin seedling stem.** Stems are 1–2 px wide and pale, and make up 22% of Cedric's labelled pixels.
  - The pipeline drops them on purpose: the 3×3 opening removes anything thinner than about 2.2 mm.
  - Stems also fall under the saturation cutoff (84% of the missed pixels have S < 100).
- **The leftover disagreement is a 1-pixel rim around each leaf.**
- **Lowering the saturation threshold makes the mask worse, not better.**
  - S ≥ 70 raises recall to 0.78, but precision drops to 0.35 and IoU to 0.32, because soil and debris start passing.
  - The current threshold (S ≥ 100) had the best IoU of the settings tested.
  - We did **not** retune the thresholds on this data. Tuning on the same images used for validation would be circular.

**Still needed:**
- Repeat the check with both annotators on larger plants (around D20 and D26). That's when we'll know whether the program reaches human-level agreement.
- Add Rey as a third annotator if possible.

**Already found:** the seedlings are still very small. At D13, GPR is 0.7–2.7% of the pot area, about 150–600 pixels per plant.
- At this size, a 1-pixel difference at the leaf edges changes GPR by about 0.5 percentage points, roughly 30% relative.
- So we will report the error in percentage points, and repeat the validation on larger plants.

**Supporting checks:**

| Check | What it shows | When |
|---|---|---|
| 5 back-to-back captures after noon, CSV untouched | Repeatability: coefficient of variation of GPR from camera and exposure noise | Any day after 12:50 |
| Green card of known area (e.g. 5 × 5 cm) placed on the soil, then removed | Measured vs known area: checks the pixel-to-mm scale and the segmentation of a known object | After the noon capture |
| D30 GPR vs harvest fresh weight | End-to-end validation (already RQ1 and RQ3) | Harvest |

---

## 2. Data proving each deliverable (Table I)

| # | Deliverable (Table I) | Evidence we have | Gap / to do |
|---|---|---|---|
| 1 | Two-point sensor calibration log; automated irrigation log | `sm_log.csv` (every 30 min), `irrigation_log.csv` (timestamp, pot, VWC, dose mL, pulse ms), `band_log.csv`. Flow rate is 18 mL/s on all 9 valves (Oct 12). | Write up the calibration record: oven-dried soil (150 °C, 6 h) = 0%, saturated = 100%, raw ADC 2483 / 1120. Re-run the flow test today (3 runs per valve, saved to CSV). |
| 2 | Day-0 pH table; HSV tuning report; `pot_rois.json` | `pot_rois.json` (current and pre-Oct 16 geometry); the HSV thresholds and how they were chosen are documented in `capture_gpr.py` | pH table: confirm it exists. HSV report: add the GPR validation from section 1. |
| 3 | GPR time-series CSV; daily capture log; GPR plots | `growth_dataset.csv` (D8 onward, 9 rows/day), `exposure_log.csv`, `cron.log`, raw noon frames kept from D12 | Make the GPR plots. Smoothed GPR is filled in by `analyze_yield.py`. |
| 4 | Harvest weight table; scale check sheet | `record_harvest.py` is ready | Scale check: weigh a known mass before the harvest and record it. |
| 5–6 | Training dataset, regression equation, LOOCV R² and MAE | `analyze_yield.py` is ready | Needs the harvest weights |
| 7 | Error log; reliability summary | `error_log.csv`, `power_log.csv` (every Pi outage), `reliability_report.py` | Run the report for the 30-day cycle (the script text still says 35 days / 315 rows) |
| HW | Hardware test data (requested) | Today's panel test: sensor repeatability, relay pass/fail, flow per valve | Run today after 12:50; it becomes the baseline for future checks |

---

## 3. Ending earlier ("meet in the middle")

**Literature search:** we did **not** find any study showing that pechay fresh weight at D25–26 equals D30.
- Sources put pechay harvest at about **30–45 days after sowing**. Some guides say harvest can start at 3–4 weeks.
- Pak choi growth follows an S-shaped curve and is still rising at that age (Ding et al., 2022, *HortScience* 57(5)).
- So the claim "D26 = D30" would not be supported.

**Our own data also argues against harvesting early:**
- The plants are still at an early stage (GPR 0.7–2.7% on D13).
- The soil is drying slowly. The low band (30–40%) has not been reached: P-01 to P-03 were at 52–76% on Oct 19. Only 4 irrigation events have been logged so far, and 2 of them were not delivered.
- Harvesting at D26 would cut the treatments' effect further.

**The checking date makes this a real constraint.** Our Oct 13 progress report puts the checking in the **1st week of November**, the same week as a D30 harvest on Nov 4. So keeping D30 leaves no buffer week.

**Options (same lettering as the slides):**

| Option | Data ends | Pros | Cons |
|---|---|---|---|
| A. Redefine harvest as D26 (Oct 31), harvested the same day as the last capture. D26 becomes the harvest day; we don't claim D26 = D30. | Oct 31 | About a week before checking | Fewer rows (171 vs 207), smaller plants, weaker treatment effect; must be stated as a limitation |
| B. Keep D30 (Nov 4), with every chapter and the analysis pre-built on D8–D26 | Nov 4 | Design unchanged | Results only on harvest day; needs the checking moved to the 2nd week of November |
| C. Fit an S-curve to each pot's GPR up to D26, and use it to argue a plateau only if one is actually seen | Nov 4 | Evidence from our own data | Cannot be promised in advance; doesn't solve the date problem alone |

With either A or B, the harvest-day weights go straight into `analyze_yield.py`, which produces the model and LOOCV results the same day.

**Decision for the adviser:** Option A or Option B.

---

## Methodology events to report (since last meeting)
1. **Soil probes were wired rotated 180°.** Fixed in firmware on Oct 16; the D8–D11 soil moisture values were corrected and backups kept.
2. **ROI circles were re-fitted to the pot rims from D11.** The old circles were offset by about 45 px. The old geometry is kept.
3. **Spare probes were installed in P-02 and P-08** (Oct 16). P-08's soil moisture before Oct 16 is unreliable.
4. **Raw noon frames are kept from D12.** They make the GPR validation possible. The manuscript text (Appendix G) says frames are deleted, so it needs updating.
5. **Question for the adviser:** how were the treatment bands defined, given that the % scale runs from oven-dried soil (0%) to saturated soil (100%)?

**Sources:**
- [Ding et al. 2022, HortScience](https://journals.ashs.org/view/journals/hortsci/57/5/article-p643.xml)
- [Pechay production guide](https://bontorns.yolasite.com/blog/pechay-production-guide)
- [Pechay plant guide](https://urbangoesgreen.com/plant-guide/edible/pechay/)
- [Manila Bulletin, "Growing pechay in just a month"](https://mb.com.ph/2021/7/3/growing-pechay-in-just-a-month)
- [Hydroponic pechay, harvest at 35 DAS](https://www.researchgate.net/publication/372554844_Performance_evaluation_of_pechay_Brassica_rapa_var_chinensis_using_different_organic_growing_media_under_hydroponic_system)
- [Treepedia 2.0, IoU against manual masks](https://arxiv.org/pdf/1808.04754)
- [EasyPCC, canopy coverage benchmark](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5422159/)
