# Clean mask vs hand labels (Nov 19, 2026)

*Claude with Cedric. This is a read-only check: no thesis data was changed.*

## Question

Commit `77544a9` added a "clean" mask next to the original one. It is the second track that `capture_gpr.py` now writes to `growth_dataset_clean.csv`. It has three steps:

1. A sunny-day white balance.
2. Keep only the green blobs of at least 12 px that touch the inner pot disc (r = 68 px).
3. Add weak-threshold pixels within 1 px of those blobs (edge recovery).

Is it closer to the hand-painted leaves than the original mask?

## Method

- **Ground truth:** the same as the committed validation.
  - Run 1, D12 (Oct 17) and D13 (Oct 18): 9 pots each, painted independently by Cedric and Kent, so 36 pot-images in all.
  - Files: `labels_Cedric.json` and `labels_Kent_v2.json`.
  - Pot circles: `pot_rois_before_20261021.json` (r = 85 px).
- **Scoring:** the same as `gpr_validate.py score`, using the deployed `clean_green_mask()` function itself.
- **Setup check:** the "original" row reproduces the committed `results_Cedric_Kent_D12_D13_leafonly.csv` exactly: all 36 rows, IoU 0.630, bias +0.044 pp, MAE 0.281 pp.
- **Steps scored separately:** each step of the clean mask was also scored on its own, to see which one helps and which one hurts.
- **Script:** `Dual_Archi/tools/validate_clean_mask.py`.
  - Per-pot tables: `results_clean_mask_D12_D13_leafonly.csv` and `results_clean_mask_D12_D13_plants.csv`.

Frame colour cast (blue/red; about 1.0 is normal): D12 is 1.32 (moderately blue), D13 is 1.16.

## Result (leaf blades, both annotators, n = 36)

| Mask | IoU | Precision | Recall | Bias (pp) | MAE (pp) | Pearson r |
|---|---|---|---|---|---|---|
| **Original (main track)** | **0.630** | **0.77** | 0.79 | **+0.04** | **0.28** | 0.82 |
| Step 1: sunny WB only | 0.624 | 0.68 | 0.88 | +0.39 | 0.44 | 0.82 |
| Steps 1+2: WB + blob filter | 0.562 | 0.67 | 0.78 | +0.22 | 0.52 | 0.56 |
| Steps 1+3: WB + edge recovery | 0.560 | 0.58 | 0.95 | +0.80 | 0.80 | 0.85 |
| **Full clean, as deployed** | **0.502** | 0.57 | 0.83 | **+0.58** | **0.80** | 0.56 |
| Full clean, no inner limit (r = 85) | 0.566 | 0.59 | 0.95 | +0.78 | 0.78 | 0.87 |

- **Whole-plant labels** (stems kept) give the same order:
  - original: IoU 0.577, MAE 0.39 pp;
  - clean: IoU 0.481, MAE 0.71 pp.
- **On the bluer frame (D12, 1.32) the original is still better:**
  - original: IoU 0.653, bias +0.06 pp;
  - clean: IoU 0.506, bias +0.71 pp.

## What it means

1. **The clean mask fails validation.** It agrees less with the human labels than the original on every measure except recall. It over-counts: the bias is +0.58 pp, against a mean labelled leaf cover of about 1 to 2 %, and the MAE is about 3× the original's.
2. **Where the extra pixels come from:**
   - The white balance turns non-leaf pixels green.
   - Edge recovery puts a ring around every leaf. On seedlings this small, a 1 px ring is a large share of the leaf.
   - In numbers: the clean mask has about 2× the original's false-positive pixels at leaf edges (within 2 px) and about 8× away from any leaf (1,518 vs 180 px).
3. **The blob filter (r = 68 px) also cuts real leaf pixels near the rim.** Recall on D13 drops from 0.82 to 0.71. This partly comes from run 1's larger pot circles, but removing the limit (last row) still leaves the clean mask worse than the original.
4. **So the 3 to 4× higher clean GPR on the blue run 2 days (D19, D21) should not be read as recovered growth.** On the only ground truth we have, most of that increase looks like over-counting.

## Limits

- The labels are from run 1, and the bluest labelled frame is 1.32. The run 2 days the clean mask was built for are bluer: D19 1.84, D21 1.65. Whether it helps on frames that blue is **untested**.
- Only 2 frames and 18 pots, the same set as the committed validation.

## Recommendation

- Keep the **original** track as the thesis measure, and keep reporting the blue days as a known light problem.
- If the clean track is shown on Saturday, show it as **"tested against the hand labels; over-counts (bias +0.58 pp); not used"**, which is a real finding.
- To settle the blue-day question, Cedric and Kent should hand-label one blue run 2 frame (D19) and one sunny one (e.g. D17) independently with `gpr_validate.py export`. Then score both masks with the same method. That is about an hour of painting.
