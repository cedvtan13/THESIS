# Data update log: Nov 19, 2026 (D22)

**Done by:** Kent at the greenhouse (health check 14:51, quick pull 15:05 `pi_pulls/2026-11-19_1505_quick`). Copied into the repo by Claude: every changed file was checked to be the old repo file plus new rows only (nothing earlier was altered).

## 1. What arrived

| File | New rows |
|---|---|
| `Dual_Archi/growth_dataset.csv` | +9 (D22, 12:00) |
| `Dual_Archi/align_log.csv`, `exposure_log.csv` | +1 each |
| `Dual_Archi/glare_log.csv` | +9 |
| `DATA/agrisentry_data/sm_log.csv` | +50 (to Nov 19 14:22) |
| `DATA/agrisentry_data/irrigation_log.csv` | +7 doses |
| `DATA/agrisentry_data/power_log.csv` | +2 events |
| `DATA/agrisentry_data/throttle_log.csv`, `band_log.csv` | +303, +249 |
| `DATA/agrisentry_data/frames/` | `D22_2026-11-19_1200.png`, `overlay/D22_overlay.jpg` (in the frames README with checksums) |

`error_log.csv`, `field_log.csv` and `light_log.csv` did not change.

## 2. D22 capture: the first normal-colour day since D18

- Written at **12:00** on the first try. Exposure **2.4 ms** (sunny), colour blue/red **1.00**, alignment confidence 0.24.
- check_pi warned "camera moved 21 px". The D21 position came from a dim, blue frame with a weak match (0.19), and the D22 overlay shows the circles on the pots, so this is most likely D21's estimate being off rather than the camera moving. A side photo of the mount is still to be taken.

| Pot | D18 | D21 (blue) | D22 |
|---|---|---|---|
| P-01 | 0.19 | 0.07 | 0.17 |
| P-02 | 0.24 | 0.10 | 0.18 |
| P-04 | 0.07 | 0.01 | 0.02 |
| P-05 | 0.31 | 0.21 | 0.42 |
| P-06 | 0.11 | 0.03 | 0.22 |
| P-07 | 0.28 | 0.14 | 0.22 |
| P-08 | 0.33 | 0.14 | 0.37 |
| P-09 | 0.31 | 0.07 | 0.21 |

Group means (cell GPR %): Low (P-01, P-02) D18 0.215, D22 0.175; Optimal (P-04 to P-06) D18 0.163, D22 0.22; High (P-07 to P-09) D18 0.307, D22 0.267. D22 is back near D18: the plants are still about the same size, and the D19 to D21 dip was mostly the blue cast.

## 3. Doses: 7 new

| Time | Pot | Reading | Dose |
|---|---|---|---|
| Nov 18 15:22 | P-06 | 49.9 | 16.2 mL |
| Nov 19 11:52 | P-02 | 29.9 | 16.1 mL |
| Nov 19 14:38:44 | P-04 | 48.1 | 22.1 mL |
| 14:38:46 | P-05 | 47.3 | 24.4 mL |
| 14:38:48 | P-07 | 69.0 | 19.2 mL (first ever) |
| 14:38:50 | P-08 | 67.8 | 22.9 mL |
| 14:38:52 | P-09 | 68.4 | 21.1 mL (first ever) |

The five 14:38 doses came about 15 minutes after the ESP32 restarted at 14:23, on readings 2.7 to 4.6 points **lower** than the same pots at 14:22 (P-04 50.8, P-05 51.9, P-07 71.5, P-08 70.3, P-09 70.8). This is a second, smaller downward shift at an ESP32 power-up (the first was about -10 at Nov 17 16:32).

## 4. Power: 2 events

| Time | Event |
|---|---|
| about 14:23 | full power loss (Pi and ESP32). Kent was on site that afternoon: to confirm whether anything was touched |
| 14:39:51 | **ESP32 rebooted while the Pi stayed up**, about one minute after the 5-dose burst |

An ESP32-only reboot right after several valves and the pump switched is consistent with a brownout on the shared 5 V supply (relay coils). To check: multimeter on the ESP32 5 V during a dose; earlier `ESP32_RESTART` rows against dose times.

**Pattern so far:** the full power losses on Nov 17 (16:32), Nov 18 (Rey's restarts) and Nov 19 (14:23) all happened while a team member was at the greenhouse.

## 5. Open

1. What was done around 14:20 on Nov 19 (plugs, cables, the box)?
2. Multimeter: 5 V at the ESP32 during a dose; probe supply.
3. Camera mount side photo.
