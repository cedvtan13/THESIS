# Data update log: Nov 18, 2026 (D21)

**Done by:** Rey (health check 13:29, full pull 13:47 `pi_pulls/2026-11-18_1347`, pushed from his laptop as `ef98699`). Checked by Claude from the files on GitHub.

## 1. What arrived (`ef98699`, 14 files)

| File | Change |
|---|---|
| `Dual_Archi/growth_dataset.csv` | D20 09:36 set removed (fix_d20, Nov 17 16:57); D21 added (9 rows, 12:54). D20 is now the 12:42 set only |
| `Dual_Archi/growth_dataset_setaside_D20_20261117_1657.csv` | new: the 9 set-aside D20 09:36 rows |
| `Dual_Archi/catch_up.sh` | the fixed version (captures only 12:00 to 12:55) |
| `Dual_Archi/align_log.csv`, `exposure_log.csv`, `glare_log.csv`, `field_log.csv` | D21 rows; the D20 fix note |
| `DATA/agrisentry_data/sm_log.csv` | +40 rows, to Nov 18 13:52 |
| `DATA/agrisentry_data/irrigation_log.csv` | +3 doses (below) |
| `DATA/agrisentry_data/power_log.csv` | +5 events (below) |
| `DATA/agrisentry_data/throttle_log.csv`, `band_log.csv` | new rows; no under-voltage flags |
| `DATA/agrisentry_data/frames/` | `D21_2026-11-18_1254.png` and `overlay/D21_overlay.jpg` (added to the frames README with checksums) |

`error_log.csv` and `light_log.csv` did not change: no new errors since Nov 17 08:44, and the hourly camera job is off.

## 2. Power: 5 events in 24 hours

Times corrected with the Pi's uptime in `throttle_log.csv` where the Pi clock was not yet synced.

| Pi down | Back | Type |
|---|---|---|
| Nov 17 about 16:32 | 16:33 | **full power loss** (ESP32 restarted too) |
| Nov 17 about 17:10 | 17:10 | Pi only |
| Nov 18 about 10:17 | **11:50** | **full power loss**, about 1.5 hours |
| Nov 18 about 12:09 | 12:10 | Pi only |
| Nov 18 about 12:30 | **12:52** | **full power loss**, about 22 minutes |

- The Pi never logged under-voltage, so the supply voltage didn't sag; the power was **cut**.
- Full power losses before these: Nov 5, Nov 7 (×4), Nov 8, Nov 9 (×2), Nov 16. Several are on days the team worked at the greenhouse. **To ask:** was anyone on site at Nov 17 16:32, and did the site lose power on Nov 18 around 10:17 and 12:30, or was a plug or extension touched?
- The light Rey saw at about 11:51 was the Pi starting up after the 10:17 to 11:50 outage.

## 3. D21 capture

- Tries at 12:00, 12:13 and 12:20 were not written (frames blue, alignment confidence 0.15 to 0.21).
- The Pi restarted at about 12:09, then lost power from about 12:30 to 12:52, so the 12:30, 12:40 and 12:50 tries never ran.
- `catch_up.sh` captured at **12:54**, inside the 12:00 to 12:55 limit.
- D21: blue/red **1.65**, exposure **14.9 ms** (dim), alignment confidence **0.19**. The overlay shows the circles on the pots. **Flag R**: the third blue day in a row (D19, D20, D21).

| Pot | D20 GPR | D21 GPR | D21 soil |
|---|---|---|---|
| P-01 | 0.10 | 0.07 | 82.2 |
| P-02 | 0.10 | 0.10 | 33.4 |
| P-03 | 0.00 | 0.00 | 40.3 |
| P-04 | 0.00 | 0.01 | 54.3 |
| P-05 | 0.15 | 0.21 | 56.1 |
| P-06 | 0.11 | 0.03 | 53.6 |
| P-07 | 0.17 | 0.14 | 73.4 |
| P-08 | 0.16 | 0.14 | 75.4 |
| P-09 | 0.07 | 0.07 | 74.6 |

## 4. Soil readings: a new level shift

At the full power loss of **Nov 17 16:32**, every probe dropped about **10 points** at once and stayed there:

| Pot | Nov 17 16:14 | Nov 17 17:03 |
|---|---|---|
| P-01 | 95.9 | 82.8 |
| P-02 | 43.7 | 32.7 |
| P-04 | 69.9 | 59.6 |
| P-05 | 57.3 | 47.0 |
| P-07 | 81.0 | 72.9 |
| P-08 | 76.2 | 67.4 |

- Water can't leave nine pots in 30 minutes, so this is electrical, like the D12 shift (8 to 31 points lower after the supply fix).
- **Consequence:** the ESP32 watered on the shifted readings. P-05 got 25.3 mL and P-08 got 24.3 mL at 16:48, and P-05 got 20.7 mL more on Nov 18 12:04.
- Since then the readings are steady, apart from one +10 jump at 07:32 that reverted by 09:32.
- So the soil record now has at least three electrical level changes: D12, the jumps from Nov 16 23:44, and this drop. **D21's "Low in band" readings come after the drop**, so they are not evidence that Low dried into its band.
- **What would settle it:** measure the probe supply voltage with a multimeter (at a probe connector and at the ESP32) and compare with the readings shown at the same moment.

## 5. Open questions

1. Who was at the greenhouse on Nov 17 at 16:32? Was anything unplugged?
2. Did the site lose power on Nov 18 around 10:17 and 12:30, or was a plug touched?
3. Probe supply voltage (multimeter), and photos of the probe wiring.
4. Cleanup of `b812af3` (40 unrelated files): pending Kent's OK.
