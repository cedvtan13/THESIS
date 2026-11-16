# Data update log: Nov 16, 2026 (D19)

**Done by:** Kent (on site, Pi steps), with Claude (analysis, scripts, copying into the repo).

**Source:** pull from the Pi on Nov 16 at 16:57, saved locally in `ThesisCoWork\pi_pulls\2026-11-16_1657\`. The frames are not committed (about 90 MB); they stay in that folder.

## 1. What changed on the Pi (Nov 16, PH time)

| Time | Change | Where (on the Pi) |
|---|---|---|
| 16:36 | Fix kit installed in `~/fixkit/`. Backup scheduled at 13:15 and 23:45 daily. First backup made. | crontab; `~/backups/` |
| 16:39 | Health check run (read-only). | `~/fixkit/reports/check_2026-11-16_1639.txt` |
| 16:47 | **D18 rows re-added** (9 rows), measured from the saved frame `D18_2026-11-15_1200.png` with the noon-capture code. Soil moisture comes from the sm_log reading at 12:00:19. CSV backed up first. | `~/thesis/growth_dataset.csv` (backup `growth_dataset.csv.before_recover_D18_20261116_1647`) |
| 16:47 | Field log: D18 recovery line added; D15 P-09 interference note copied over from `field_log.txt`. | `~/thesis/field_log.csv` (backups `.before_recover_D18`, `.before_add_notes`) |
| about 16:50 | Mask comparison run (read-only). | `~/fixkit/mask_compare/` |
| 16:57 | Full data pull to the laptop. | none |

**Physical check by Kent (afternoon of Nov 16):**
- **P-01:** soil wet to the touch; no dripping from its hose.
- **P-03:** seedling looks dead.
- **P-04:** alive and looks okay.

These are **not yet in the Pi's field log**. `tomorrow_fixes.bat` adds them on Nov 17.

## 2. What changed in this repo (Nov 16)

Each file was overwritten with the Pi's version. The Pi is the master copy, and the repo copies were older and shorter versions of the same files.

| File | Lines before → after | What is new |
|---|---|---|
| `Dual_Archi/growth_dataset.csv` | 145 → 154 | D18 (9 rows, recovered) |
| `Dual_Archi/align_log.csv` | 13 → 14 | D18 alignment row from the recovery |
| `Dual_Archi/glare_log.csv` | 145 → 154 | D19 glare check |
| `Dual_Archi/light_log.csv` | 149 → 153 | Nov 16 hourly light readings |
| `Dual_Archi/field_log.csv` | 53 → 55 | D18 recovery note, D15 P-09 note |
| `Dual_Archi/sowing_date.txt` | same date (2026-10-29) | line ending only |
| `DATA/agrisentry_data/sm_log.csv` | 451 → 702 | soil moisture to Nov 16 16:44 |
| `DATA/agrisentry_data/irrigation_log.csv` | 15 → 26 | doses Nov 11 to Nov 16 (25 in total) |
| `DATA/agrisentry_data/power_log.csv` | 78 → 90 | power events to Nov 16 |
| `DATA/agrisentry_data/band_log.csv` | 6135 → 8902 | to Nov 16 |
| `DATA/agrisentry_data/throttle_log.csv` | 1721 → 3191 | to Nov 16 |

`DATA/agrisentry_data/error_log.csv` was left unchanged: there have been no new errors since Nov 9.

## 3. What we found

1. **Why D18 was missing.** The D18 rows **were** written at 12:00 on Nov 15: `cron.log` says "day 18 is already in the CSV" at 12:10.
   - From 12:20 on, the Pi's `sowing_date.txt` read 2026-10-06, and `growth_dataset.csv` no longer had D18.
   - The most likely cause is a git pull/merge on the Pi around 12:16 (repo commit 2b909b9, "Resolve file deletion conflicts"). It put back the repo's old copies of both files.
   - Every capture from Nov 15 12:20 to Nov 16 12:40 then refused to run ("D=41/42 outside the cycle") until the sowing date was fixed on Nov 16.
   - **Root problem:** the Pi's live data files sit inside the git folder `~/THESIS`, so any git pull on the Pi can overwrite them. `protect_data.sh` (Nov 17) closes this.
2. **Why the D19 masks are small.** The D19 frame has a **blue colour cast**: blue/red is 1.84, against about 1.0 on normal days.
   - It was captured at 12:47 under overcast light. The capture was late because of the sowing-date problem and a Pi crash at 12:16.
   - The camera's white balance is locked for sunlight, so overcast light turns the frame blue. Leaf saturation drops below the S ≥ 100 threshold, and GPR reads about half of D18's.
   - The same effect shows on D04 (1.34), D05 (1.53) and the D12 12:42 retake (1.49). D17 is mild (1.20).
   - Loosening the mask does not fix it: the two-level mask only reaches 0.132 % on D19. Colour-correcting the frame fully recovers D12 (0.099 → 0.189 %) but only partly recovers D19 (→ 0.104 %).
   - **D19 should be flagged R.**
3. **Pi crashes.** There have been 12 Pi-only crashes since Nov 12, most at :30, which is when the hourly `light_log.py` turns the camera on. The ESP32 kept running through all of them.
4. **The errors=5946 count.** All 5,946 lines are from Nov 9 (D12): 5,910 are repeated BMP388 read failures during the supply fault, and 36 are probe range and quarantine messages. There have been no errors since.
5. **Unlogged dose.** P-05's dose number jumps from 2 to 4 at Nov 9 12:48, so one dose was not logged.
6. **P-06 reading spikes.** Doses of 17 to 19 mL make P-06 read 25 to 35 points higher within hours, which should be about 6 points. For example, on Nov 15 it went from 49.7 % at 18:27 to 91.6 % at 02:27. With no dripping, the likely cause is that its tube outlet sits next to the probe. Check this on Nov 17.
7. **P-01** reads 90 to 95 % and is in fact waterlogged (Kent felt the soil). This is real moisture, not a probe fault.

## 4. Not in this commit

- The noon frames (in `pi_pulls\2026-11-16_1657\agrisentry_data\frames\`).
- The fix kit: `ThesisCoWork\2026-11-16-greenhouse-kit\`.
