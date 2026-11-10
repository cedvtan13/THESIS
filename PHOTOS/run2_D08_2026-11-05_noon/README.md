# Run 2, D8 (2026-11-05): noon overlay and glare checks

- `D08_overlay.jpg`: the official D8 noon capture (12:00), with detected plant pixels and the pot circles. This is the frame behind the D8 rows of `growth_dataset.csv`.
- `check_1135_before_cloths_overlay.jpg`: test shot at 11:35, before the cloths. Sun patches over the right column; P-01, P-04, P-05 and P-08 read 0 % although seedlings are visible.
- `check_1150_with_cloths_overlay.jpg`: test shot at 11:50, with small cloths over P-01, P-04 and P-07. All 9 pots detected.

Both test shots were taken with `capture_gpr.py --no-write` (same camera settings as the noon capture, gain locked at 1.0). They are not part of the dataset.

D8 glare check (`glare_log.csv`): P-04 MILD, P-07 MILD, the other pots ok.
