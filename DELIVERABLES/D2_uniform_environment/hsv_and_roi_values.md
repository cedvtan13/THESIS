# HSV tuning values and ROI configuration (Deliverable 2)

AgriSentry, run 2. Source: `Dual_Archi/capture_gpr.py` and `Dual_Archi/pot_rois.json`. These values are fixed for the whole run.

## 1. Green threshold (HSV)
| Channel | Value used (OpenCV units) | Meaning | On the usual scale |
|---|---|---|---|
| Hue | **38 to 85** | Green range | about 76° to 170° on the colour wheel |
| Saturation | **at least 100** (of 255) | Rejects grey, dry soil and washed-out pixels | at least 39 % |
| Value (brightness) | **at least 55** (of 255) | Rejects deep shadow | at least 22 % |

**Units:** OpenCV stores hue on a 0–179 scale (half-degrees). The manuscript's "35° ≤ Hue ≤ 85°" uses OpenCV units, so the degree sign should be removed or the range rewritten as about 70°–170°. Halving the numbers to 18–42 would select orange-yellow, not green.

**Why 38 rather than 35:** tuned on a real foliage frame, where accepted leaf pixels had a median hue of 67 (5th–95th percentile 43–82). 38 keeps all of that and cuts more yellowish soil and husk.

## 2. Mask cleanup
| Step | Value |
|---|---|
| Morphological opening | 3 × 3 pixel kernel |
| What it removes | Specks and bridges thinner than about 2.2 mm (below a pechay petiole) |

## 3. Camera settings (locked, the same every day)
| Setting | Value |
|---|---|
| Camera | Raspberry Pi Camera Module 3 (Sony IMX708 sensor) |
| Capture size | 1296 × 1296 px |
| Analogue gain | 1.0 (fixed) |
| Colour gains (white balance) | 1.8, 1.6 (fixed) |
| Exposure | Starts at 6 ms and is adjusted until the frame's mean brightness (V) reaches **73**, matching the reference frame from 2026-10-13 12:00. Only brightness changes; hue does not. Logged daily in `exposure_log.csv` |
| Capture light | Used only if the scene is too dark to reach the target. **Not used on any run 2 day so far** (`light_used = 0`, D1–D8) |
| Schedule | 12:00 daily, retries every 10 min until 12:50, one capture per day |

## 4. Regions of interest (`pot_rois.json`)
Frame 1296 × 1296 px. Circular pot regions, radius 77 px.

| Pot | Centre x | Centre y |
|---|---|---|
| P-01 | 968 | 309 |
| P-02 | 621 | 307 |
| P-03 | 274 | 314 |
| P-04 | 992 | 656 |
| P-05 | 647 | 673 |
| P-06 | 290 | 699 |
| P-07 | 1003 | 1030 |
| P-08 | 651 | 1045 |
| P-09 | 277 | 1072 |

**Three GPR measures per pot:**
| Column | Area | Use |
|---|---|---|
| `cell_gpr` | Pot-area cell: pixels nearer this pot's centre than any other, up to 175 px | **Main measure.** A plant leaning past its rim stays in its own cell |
| `raw_gpr` | Pot circle, r = 77 px | Secondary |
| `terr_gpr` | Territory circle, r = 221 px | Extra column (still on run 1's scale) |

**ROI history (all logged, with backups):**
- 2026-10-29 13:15, 14:38 and 14:45 (D1): fitted after sowing and after the camera and pots were moved.
- 2026-11-03 16:00 (D6): re-centred after the camera drifted about 16 px to the right. Applies from D7. Backup: `pot_rois_before_D6_recentre.json`.

## 5. Validation (from run 1)
Compared with hand-labelled photos:
- **Overlap (IoU):** 0.64 for the pipeline, against 0.79 between two human labellers.
- **Bias:** +0.04 percentage points.
- **MAE:** 0.28 percentage points.

## 6. Day 0 pH (still to do)
The pH sensor (PH-4502C) arrives next week. The table template is in `pH_table_template.csv`. Method: 1 : 2.5 soil to distilled water, 3 readings each, two-point calibration with pH 7.00 and 4.00 buffers.
