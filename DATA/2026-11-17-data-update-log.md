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

## 6. Afternoon visit, Nov 17 (Kent): fixes run and data pulled (`pi_pulls/2026-11-17_1606`)

### Done on the Pi

| Time (approx.) | Action | Result |
|---|---|---|
| 15:35 | `tomorrow_fixes.bat` | 10 data files protected from git; merge hook installed; hourly `light_log.py` turned OFF; sowing date OK; 5 field-log notes added |
| about 15:45 | `apply_cast_guard.bat` | **applied**: `capture_gpr.py` patched (backup `capture_gpr.py.before_cast_guard`); D19 test reads blue/red 1.84. From D21, a noon frame with blue/red > 1.25 is retried; 12:50 always writes |
| 16:01 | `check_pi.bat` | D20 colour 1.57 (blue), alignment confidence 0.20 |
| about 16:03 | `run_mask_compare.bat` | read-only |
| 16:06 | `pull_from_pi.bat` | data and frames to the laptop |

**Not done yet:** `fix_d20.bat`. D20 still has 18 rows; run it at the next visit and type `12:42`.

### Copied into the repo from the pull

| File | Change |
|---|---|
| `Dual_Archi/light_log.csv` | +2 lines |
| `Dual_Archi/field_log.csv` | +5 notes |
| `Dual_Archi/capture_gpr.py` | now the patched version running on the Pi (cast guard) |
| `DATA/agrisentry_data/sm_log.csv` | to Nov 17 15:44 |
| `DATA/agrisentry_data/power_log.csv` | updated |
| `DATA/agrisentry_data/error_log.csv` | +2 lines |
| `DATA/agrisentry_data/band_log.csv` | updated |
| `DATA/agrisentry_data/throttle_log.csv` | updated |

`irrigation_log.csv` is unchanged: no doses since Nov 16 09:27.

### Answer to 3.2 (the all-pot soil rise): a measurement fault, not water

**Valves:**
- `irrigation_log` has no dose on Nov 17.
- Rey sprayed only P-04.

**What `sm_log` shows:** all probes jump up together and come back down within 20 to 30 minutes, again and again:

| Time | P-02 | P-03 | P-05 | P-07 |
|---|---|---|---|---|
| 08:44 | 42.1 | 48.6 | 60.9 | 82.6 |
| 09:14 | 63.2 | 66.1 | 83.4 | 99.3 |
| 09:33 | 45.6 | 44.5 | 58.6 | 82.3 |
| 10:14 | 62.9 | 63.6 | 78.6 | 96.8 |
| 11:44 | 46.4 | 46.9 | 57.0 | 82.6 |
| 12:14 | 63.3 | 63.9 | 77.5 | 97.2 |
| 12:42 | 63.4 | 64.2 | 78.4 | 98.0 |

Water cannot enter and leave a pot in 20 minutes, so this is electrical: the probe supply or the ADC reference, the same family as the D12 VCC fault.
- The first such jump is **Nov 16 23:44**. There are 12 jumps up to Nov 17 13:44, several at night.
- `error_log` also has `SENSOR_RANGE` at Nov 17 08:44 (P-05 raw 135, P-06 raw 18).

**Consequences:**
- **D20 soil moisture (the 12:42 readings) is invalid-high** and stays flagged. The nearest low-phase reading is 11:44 (P-02 46.4, P-03 46.9, P-04 61.4, P-05 57.0, P-06 67.5, P-07 82.6, P-08 77.5, P-09 81.6; P-01 96.0). Whether to use it is for the team.
- **Irrigation decisions** during high phases may skip doses, and during low phases may dose.
- **Physical check at the next visit:**
  - probe power wiring and connectors;
  - moisture or condensation on the ESP32 board, MUX or buck converter (the jumps happen at night too);
  - the supply.

### Phone photos (Kent, Nov 17 afternoon, `2026-11-16-greenhouse-kit/pot1.jpg` to `pot9.jpg`)

- **Every plant is still at the seed-leaf (cotyledon) stage at D20, with about 1 cm leaves.** No true leaves are visible.
- **P-03** is empty.
- **P-04** is tiny but present.
- **The mask is not the problem:** the seedlings really are that small, matching cell GPR of about 0.1 to 0.3 %.
- **P-06:** the tube outlet ends at the pot edge, a few centimetres from the probe, not on it. Its earlier spikes are not explained by the outlet position.
- **Camera mount:** checked by Kent, fine.
