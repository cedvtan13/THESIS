# Vision reliability: ROI and GPR (part of Deliverable 7)

Pechay Growth Monitoring & Yield Prediction (Run 2), evidence to D8 (2026-11-05). Three questions: do the pot circles stay on the pots (ROI), does GPR count the right pixels (accuracy), and is the light kept the same (consistency)?

## Files in this folder
| File | What it is |
|---|---|
| `gpr_validation_D12_D13_leafonly.csv` | Program vs hand labels, per pot: precision, recall, IoU, Dice, GPR auto vs manual. 2 labellers (Cedric, Kent) × 18 pot images (run 1, D12 and D13 noon frames) |
| `gpr_validation_error_map_D13.png` | Where the program and the hand label disagree (green = agree, red = missed by the program, blue = extra) |
| `glare_log.csv` | Per pot, per noon photo: clipped pixels, brightness relative to the other pots, level (ok / MILD / GLARE / DARK) |
| `exposure_log.csv` | Per noon photo: exposure time, mean brightness reached, target, whether the capture light was used |
| `roi_checks/` | Photos with the pot circles drawn, used to fit and check the ROI (D1 fits, D4 and D7 checks) |

## 1. ROI reliability: do the circles stay on the pots?
Camera shift measured against the reference frame (2026-10-29 14:41), from `field_log.csv`:

| Day | Shift | Action |
|---|---|---|
| D1 | Pots and camera moved during setup | Circles fitted 3 times (13:15, 14:38, 14:45), each logged with a backup |
| D4 | about 7–8 px | None needed |
| D5 | about 5 px | None needed |
| D6 | about **16 px** right (rim fits +11 to +22 px on 8 pots) | Circles re-centred at 16:00, applying from D7. Backup: `pot_rois_before_D6_recentre.json` |
| D7 | about **1 px** from D6 | None needed. Circles on the rims (`roi_check_D07.png`) |

- **Why a 16 px shift didn't spoil D4–D6:** the main measure, `cell_gpr`, counts each pot's whole area, up to 175 px from the centre, not just the 77 px pot circle. The pots stayed well inside their areas, so the plant pixels were still counted for the right pot.
- **Backups:** every earlier ROI file is kept in `Dual_Archi/` (`pot_rois_before_*.json`), so each day's number can be traced to the exact circles used. `glare_log.csv` names the ROI file for each photo.
- **Not measured yet on D8.** Do the next drift check on a D9 or D10 check photo.

## 2. GPR accuracy: does it count the right pixels?
### Against hand labels (run 1, D12 and D13, leaf blades only)
Same thresholds, camera and settings as run 2.

| | Program vs Cedric | Program vs Kent | Program vs both | **Cedric vs Kent (human benchmark)** |
|---|---|---|---|---|
| Pixel IoU (all pixels pooled) | 0.64 | 0.64 | **0.64** | **0.79** |
| GPR mean absolute error | 0.29 pp | 0.27 pp | **0.28 pp** | **0.19 pp** |
| GPR bias | −0.05 pp | +0.14 pp | **+0.04 pp** (vs their average) | Cedric +0.19 pp larger on every pot |
| Precision / recall (pooled) | | | 0.77 / 0.79 | |

- **No systematic error:** the program falls between the two people (bias +0.04 pp).
- **Less precise per pot than two people are with each other:** IoU 0.64 against 0.79, and 0.28 pp against 0.19 pp. At seedling size, the target "as close to a person as two people are to each other" is **not yet met**. The extra error is scatter of about ±0.3 pp per pot, not bias.
- **Plants were small** (hand-labelled GPR 0.5–2.1 %), so 0.28 pp is about 20 % of a typical plant. **Plan:** repeat the check on run 2 photos around D20 and D26, when the plants are bigger, with `Dual_Archi/tools/gpr_validate.py`.

### Empty pots (run 2, false positives)
Pot photos taken while the pot had no seedling: D1 all 9 pots, P-02 on D4–D6, and P-01, P-03, P-06 on D4–D7. That is **24 pot photos.**

| Result | Count |
|---|---|
| Read 0.00 % (correct) | **23 of 24** |
| False positive | **1:** P-03 on D7 read 0.70 %. A green object on the cloth outside the pot, inside P-03's area. The pot circle itself read 0.00. Logged in `field_log.csv` and left as measured |

So soil, shadows, tubes and sensor boards are not being counted as plant.

## 3. Light consistency
### Exposure (`exposure_log.csv`)
Gain (1.0) and colour gains (1.8, 1.6) are locked. Only the exposure time changes, so that each noon photo reaches the same brightness (mean V target 73).

| Measure | D1–D8 (6 photos) |
|---|---|
| Brightness reached | 70.6 to 74.9 (target 73, within ±2.4) |
| Exposure time | 1.6 ms (sunny) to 9.3 ms (D1, 13:14) |
| Capture light used | **0 of 6** |

### Glare and darkness (`glare_log.csv`)
Checked per pot on every noon photo (54 pot photos so far):

| Level | Rule | Count |
|---|---|---|
| ok | none of the below | **44** (81 %) |
| MILD | pot ≥ 1.4 × brighter than the median pot | 4 (P-07 D5, P-04 D7, P-04 D8, P-07 D8) |
| GLARE | ≥ 5 % clipped pixels **and** ≥ 1.4 × brighter | 4 (P-01, P-04, P-07 on D6; P-07 D7) |
| DARK | ≤ 0.6 × the median pot (deep shade) | 2 (P-09 D6, D7) |

- **Effect:** glare can wash out leaves. For example, P-07 read 0.00 % on D6–D7 although its seedling was present.
- **Fix:** small cloths over P-01, P-04 and P-07 on D8 (11:35–11:45). The D8 noon photo had no GLARE pots and all 9 detected. Before and after: `Desktop/AgriSentry_Run2_Photos/3_checks/D08_1135_masked_before_cloths.jpg` and `D08_1150_masked_cloths.jpg`. A full shade cloth over all 9 pots is planned from D9.
- **Use in the analysis:** flagged rows are kept, not deleted. The model is run with and without them.

## Limitations
- The accuracy figures come from run 1 seedlings (D12, D13). They still have to be confirmed on run 2 photos with bigger plants.
- No repeat-shot (repeatability) test yet: 3 photos a few minutes apart in the same light, with nothing changed.
- The camera drift check is manual (rim fits on a check photo), not automatic.
