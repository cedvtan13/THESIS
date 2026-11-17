# Data update log: Nov 17, 2026 (D20)

**Done by:** Rey on the Pi (commit `c52f561`, then merge `2f10bb1`, pushed from the Pi using "Way B"). Kent pulled the result to his laptop. Checked by Claude.

**Note:** this was the last push from the Pi. From now on, git merges on the Pi are blocked (`protect_data.sh`), and data goes Pi → laptop (`pull_from_pi.bat`) → GitHub.

## 1. What arrived (commit `c52f561` + merge `2f10bb1`)

| File | Change |
|---|---|
| `Dual_Archi/growth_dataset.csv` | +18 rows: **two D20 sets** (09:36 and 12:42; see 3.1) |
| `Dual_Archi/align_log.csv` | +3 rows (D20 at 09:33, 09:36, 12:41) |
| `Dual_Archi/exposure_log.csv` | +2 rows (D20 at 09:36 and 12:42) |
| `Dual_Archi/glare_log.csv` | +9 rows |
| `Dual_Archi/light_log.csv` | +7 rows |
| `Dual_Archi/field_log.csv` | +2 lines from Rey (P-04 retake and P-04 sprays; see 3.4) |
| `Dual_Archi/catch_up.sh` | first time in the repo (it already existed on the Pi) |
| `*.before_*` backups (3 files) | backups made by the Nov 16 fixes; harmless |

**Not updated:** `DATA/agrisentry_data/` (soil moisture, irrigation and power logs). These stop at Nov 16 16:57 until the next `pull_from_pi.bat`.

**Checked:**
- no conflict markers in any CSV;
- D1 to D19 unchanged;
- D18 is the recovered set.

## 2. D20 values (as recorded)

| Pot | 09:36 SM | 09:36 GPR | 12:42 SM | 12:42 GPR |
|---|---|---|---|---|
| P-01 | 93.5 | 0.07 | 100.0 | 0.10 |
| P-02 | 45.6 | 0.07 | 63.4 | 0.10 |
| P-03 | 44.5 | 0.00 | 64.2 | 0.00 |
| P-04 | 60.6 | 0.00 | 77.9 | 0.00 |
| P-05 | 58.6 | 0.20 | 78.4 | 0.15 |
| P-06 | 69.0 | 0.14 | 84.5 | 0.11 |
| P-07 | 82.3 | 0.08 | 98.0 | 0.17 |
| P-08 | 78.5 | 0.17 | 93.8 | 0.16 |
| P-09 | 80.2 | 0.06 | 97.0 | 0.07 |

Capture conditions:

| Capture | Exposure | Brightness (target 73) | Alignment confidence |
|---|---|---|---|
| 09:36 | 3.3 ms | 74.8 | 0.26 |
| 12:42 | 10.9 ms (dim) | 70.0 | 0.20 |

## 3. Problems found

1. **D20 has 18 rows, two sets of 9.** A duplicated plant-day breaks the leave-one-plant-out analysis, so one set must be set aside.
   - **09:36:** `catch_up.sh` runs a capture 2 minutes after any reboot if today has no frame. The Pi rebooted at about 09:31, so D20 was captured in morning light, outside the 12:00 to 12:50 protocol.
   - The 12:00 cron then refused, because the day was already written.
   - **12:42:** the manual retake after P-04 was straightened.
   - **Fix prepared:**
     - `fix_d20.bat` limits `catch_up.sh` to 12:00 to 12:55;
     - it keeps one D20 set and moves the other to `growth_dataset_setaside_D20_<time>.csv` (nothing is deleted).
   - **Decision (Kent, Nov 17):** keep **12:42**. It is inside the protocol window and P-04 was upright. Flag it R (dim light, P-04 handled before the photo).
   - The 09:36 set is moved aside, not deleted, with `fix_d20.bat` at the next visit.
   - Note on soil moisture: the 12:42 readings are **further** from the bands than the 09:36 ones, because every pot rose 15 to 20 points between the two (see 3.2). The 12:42 set is kept for the capture time, not for its soil readings, and those readings are flagged until the rise is explained.
2. **All 9 soil readings rose 15 to 20 points between 09:36 and 12:42**, for example P-02 from 45.6 to 63.4 and P-07 from 82.3 to 98.0.
   - The field log only records sprays to P-04.
   - A rise in every pot at once means either water reached every pot (hand watering, sprays, rain through the roof) or a probe or supply problem like D12.
   - **To answer:** what happened between 09:36 and 12:42?
3. **P-04** reads GPR 0.00 in both D20 captures. Rey logged it as bent by irrigation (straightened) and wilting/dying, with 20 sprays to P-04 only. Those sprays are unequal treatment, so they go in the deviations table.
4. **Rey's two field-log lines are in the wrong format.** They read `D20,P-04,...` with no date, where the file expects `date,day,pot_id,"note"`. They will be rewritten in the right format with the times once confirmed.

## 4. Open questions for the group

- What happened between 09:36 and 12:42? Team answer: Rey sprayed only P-04; the team suspects the valves actuated. To be checked against sm_log, irrigation_log, pi_link.log and power_log at the next pull.
- Who ran the 12:42 retake, and how (`capture_gpr.py --force`)?
- Why did the Pi reboot at about 09:31? Team: unknown. To be checked in power_log at the next pull.

## 5. Complete event log

Every event of the run, including those not in the field log, is now kept in `DATA/2026-11-17-run2-event-log.md`.
- It records everything.
- What goes into the manuscript's deviations table is decided by the team.
