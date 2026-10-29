Picking up work in progress. Handoff written 2026-10-29, ~00:30, the night before run 2's sowing. You have no prior history with this; everything you need is below.

**What the user wants next: preparing for the panel's checking.** They will ask:
1. Which data do we need right now for the panel's Day 1 checking?
2. Which deliverables can't we achieve right now?

The deliverables are Table I of the manuscript, transcribed in the section "Deliverables (Table I)" with a first-pass status for each. Start from that section and check each item against the files on the Pi.

## Project
AgriSentry is an undergraduate thesis: "Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse".
- 9 pechay pots in 3 soil-moisture groups.
- Every day at noon, a top-down camera measures each pot's canopy Green Pixel Ratio (GPR).
- After harvest, an OLS polynomial regression with leave-one-plant-out cross-validation (LOOCV) predicts each plant's harvest weight.

**People**
- Adviser: **Engr. Alvin Joseph Macapagal** ("sir AJ").
- Students: Cedric Vince Tan (the user), Kent Vincent Godinez, Rey Emmanuel Adag.

**Hardware**
- **Raspberry Pi Zero 2 W** (`crk@groupb.local`): camera, GPR, CSV logging.
- **Custom ESP32-S3 board:** reads the soil probes through a MUX, plus a BMP388 sensor, and drives 12 relays (9 valves, pump, Pi fans, capture light). It runs the watering by itself and doesn't need the Pi for it.
- The two talk over UART (`/dev/ttyAMA0`, 115200).

**Network**
- The Pi is offline except when the iPhone hotspot "Cvtan" is on. On the hotspot it is `172.20.10.7`.
- The ESP32 has its own Wi-Fi network (see Run 2 status).

**Pot layout, as seen by the camera** (unchanged from run 1, confirmed by the user Oct 28):

| | left | middle | right |
|---|---|---|---|
| top | P-03 | P-02 | P-01 |
| middle | P-06 | P-05 | P-04 |
| bottom | P-09 | P-08 | P-07 |

**Moisture groups (bands)**
- P-01 to P-03: low, 30–40%.
- P-04 to P-06: optimal, 50–60%.
- P-07 to P-09: high, 70–80%.
- The % is relative to the two-point calibration (0 = oven-dried soil, 100 = saturated soil), **not true VWC**.

## Run 2 (current): status as of Oct 29, ~00:30
**Why there is a run 2.** Run 1 (sown Oct 6) had three problems: slow growth from low light, leaning plants falling outside the pot circles, and treatments only half reached. The team moved the whole greenhouse to a sunnier spot on Oct 28 and starts fresh.

**Dates**
- **Sowing Oct 29 = D1.** D30 = **Nov 27** (`CYCLE_DAYS = 30`).
- **The panel checks the system from D1 to D30.** How exactly they will check is still to be asked.
- 1st checking: 1st week of November (≈ D4–D10).
- 2nd checking: Nov 23–28 (≈ D26–D31).

### Not done yet: due on the morning of Oct 29, before 12:00
1. **Start the run:** `PI_HOST=172.20.10.7 ./system.sh new-run 2026-10-29` from the Mac (THESIS folder), then answer `y`.
   - This archives all of run 1 to `~/archive/run_sown_2026-10-06_archived_<stamp>/` on the Pi. Nothing is deleted.
   - It sets the sowing date, sends `--reset-state` (germination mode ON, so all pots are kept at 50–60%), and turns on the 12:00 capture and the hourly light log.
   - **If this isn't done by 12:00**, the noon capture is written as D24 of run 1 (the Pi's `sowing_date.txt` still says 2026-10-06).
2. **Valve test:** on the ESP32 web page, run each pot for 2 s and check that water comes out at the right pot.
3. **Sow:** 3–4 seeds per pot, plus a backup tray. Thin to 1 seedling at D7–10, choosing the most uniform 9, and log it.
4. **After 12:50:** check that D1 is in `growth_dataset.csv` (9 rows, now including `cell_gpr`), and look at `~/agrisentry_data/frames/overlay/D01_overlay.jpg`.
5. **Treatments:** start them after thinning with `./system.sh bands-on`, which ends germination mode. The team proposes D8; ask the panel or sir AJ.

### What was done on Oct 28 (all pushed to GitHub `cedvtan13/THESIS`, `main`)
- **New tools for run 2** (commit `9041f31`):
  - `agrisentry.sh new-run DATE` and `bands-on`.
  - Live **pot-area GPR** (`cell_gpr`, `cell_green_px` and `cell_total_px` columns): each pot owns the pixels nearest its centre, up to 175 px, with no overlap. This is the main growth measure from now on.
  - A daily check picture: `frames/overlay/DXX_overlay.jpg`.
  - `tools/light_log.py`, cron `30 6-11,13-18`: camera exposure used as a light meter, written to `light_log.csv`.
  - `analyze_yield.py --gpr-column`, defaulting to `cell_gpr`.
- **Checklist for the team:** `MOVE_AND_D1_CHECKLIST.md`. Notes for classmates: `TEAM_NOTES_2026-10-28.md`.
- **After the move, the ESP32 was silent in both directions.** The TX and RX wires were swapped while the 1 Hz heartbeat LED still blinked. Fixed by the user.
  - Correct wiring: Pi pin 8 (TX) → ESP32 GPIO44 (RX); Pi pin 10 (RX) ← ESP32 GPIO43 (TX); Pi pin 16 → EN; Pi pin 18 → BOOT.
- **ESP32 firmware v6-web** (commits `6faf5ba`, `c8a970a`, `682ead4`, all flashed and checked):
  - The ESP32 runs its own Wi-Fi network **"AgriSentry"** (password `agrisentry`) with a live page at **http://192.168.4.1**.
  - The page shows fresh readings of all 9 probes every 2 s in the camera layout, and a probe finder that highlights the tile whose reading jumps.
  - **Test watering:** valve + pump, 1–10 s, per pot. It runs the existing `MANUAL_WATER` command and is logged on the Pi as `LOG,WEB_TEST` + `ACK,MANUAL_WATER`.
  - The page's display readings are separate from the control loop (no fault counting).
  - Probes are on ADC1, so Wi-Fi doesn't disturb them: raw readings stayed within ±2 counts with Wi-Fi on.
  - **Don't join AgriSentry from the phone that runs the hotspot.** That turns the hotspot off and cuts the Pi off.
- **Probe check:** the user confirmed every probe sits in the right pot (using the web page).
- **Calibration offset for P-03 and P-05** (commit `682ead4`):
  - The user cleaned all probes and held them in air. Seven read 4.1–7.0% (mean 5.9%); P-03 read 13.5% and P-05 11.4%.
  - The dry and wet points of those two were shifted by −103 and −75 counts, so they now read about 5.9% in air like the rest. The span is unchanged.
  - Checked after flashing: P-03 went from 66.9% to 59.2% and P-05 from 51.6% to 46.1%; the other probes were unchanged.
  - The user asked for only this adjustment, not a full per-probe recalibration.
- **Pot circles re-fitted** (commit `8d69302`, file on the Pi too):
  - A Hough circle fit per pot on a night frame (flashlight), r = 77 px for all pots (fitted rims were 70–81 px). The run-1 geometry is in `pot_rois_before_run2.json`.
  - The rims are smaller than run 1's r = 85, so **the camera is probably about 10–15% higher than 136 cm. Ask the user to measure it** (lens to soil) and log it.
  - The pots look slightly off-centre: the camera sees the side walls of the outer pots. That's fine.
- **The Pi boot-looped on Oct 28 evening.** The journal shows several boots that each died about 13 s in. The user says it was from the system being moved around; it was stable (`throttled=0x0`) afterwards. If it happens again, suspect the power supply first.
- **Capture light:** the relay ACKs, but the night frame didn't get brighter. The lamp is probably unplugged or not aimed at the pots at the new site. It only matters on very dark days.
- **The ESP32 is still in run 1's band mode** (germination OFF) until `new-run`, so it may water P-04 to P-09 overnight. That's harmless before sowing.

### Live readings (Oct 28, ~21:03, after the P-03/P-05 fix)
P-01 29.6, P-02 40.5, P-03 59.2, P-04 100.0, P-05 46.1, P-06 66.9, P-07 99.3, P-08 93.3, P-09 40.6 (%). P-04, P-07 and P-08 were wet from automatic watering and from the valve tests.

## Deliverables (Table I of the manuscript) and first-pass status
The manuscript says **35 days** and **315 rows** (9 × 35). The live system runs **30 days** (`CYCLE_DAYS = 30`, so 270 rows), and D30 = Nov 27 is already at the 2nd checking (Nov 23–28). A 35-day run would end Dec 2, after the checking. **The mismatch has to be resolved with the adviser or panel, or the manuscript updated.**

| # | Objective | Deliverables | Status for D1 | Can't be done yet |
|---|---|---|---|---|
| 1 | Deploy 1:1 solenoid baseline irrigation for 3 VWC groups (30–40, 50–60, 70–80%) | Two-point sensor calibration log; 35-day automated irrigation log (CSV: timestamp, pot ID, VWC, pulse duration) | **Calibration values exist** (2483/1120: oven-dried at 150 °C for 6 h, and saturated), plus the Oct 28 offsets. **A written calibration log/report is not yet written** (the Oct 20 adviser update asked for it). `irrigation_log.csv` starts empty at `new-run`; its columns cover the deliverable. Flow is 18 mL/s on all valves (Oct 12/21 test). | The groups aren't active until `bands-on` (~D8), so D1–D7 is germination mode (all 50–60%). There's only a 30-day log, not 35. % ≠ true VWC. |
| 2 | Uniform growing environment, controlled conditions | Day 0 pH table for 9 pots; pre-calibration report (HSV tuning values); ROI mask config `pot_rois.json` | **pH: unknown whether measured.** It must be done on Day 0/D1 (before or at sowing), or it can't be done at all. HSV values are fixed in code (H 38–85, S ≥ 100, V ≥ 55, 3×3 opening; `calibrate_hsv.py`), but there's no write-up yet. `pot_rois.json` ✓ (re-fitted Oct 28). | — |
| 3 | Daily canopy images, GPR for 9 plants over 35 days | Nine 35-day GPR CSVs (date, timestamp, pot ID, GPR, smoothed GPR, anomaly flag); daily capture log; GPR plots | `growth_dataset.csv` has all of these columns in one file. It can be split per pot. `smooth_gpr` is filled after harvest (centred 3-day average). Capture log: `cron.log` + `exposure_log.csv` + saved frames and overlays. Plots: `tools/gpr_view.py`. | Only D1 exists (from noon Oct 29). GPR ≈ 0 until emergence (~D3–5). Only 30 days, not 35. |
| 4 | Ground-truth fresh-weight biomass at harvest | 9-pot harvest table (pot ID, SM group, harvest date, fresh weight g); scale check sheet | `record_harvest.py` is ready (writes `harvest_weights.csv`). The **scale check can be done now** (weigh a known mass 3×). | The weights exist only at harvest (D30 = Nov 27). |
| 5 | Multivariate polynomial regression | 315-row training CSV; equation with β0–β5; feature correlation matrix | `analyze_yield.py` (six-term spec = β0–β5; `--self-test` proves the machinery). | Everything needs harvest weights. 270 rows, not 315. |
| 6 | LOOCV performance | LOOCV R²; MAE (g); predicted vs actual table; residual plots per SM group | Same script. | After harvest. |
| 7 | Software failure detection and recovery | 35-day error log; reliability summary (scheduled vs successful vs NaN-interpolated) | `error_log.csv`, `power_log.csv`, `band_log.csv`; `reliability_report.py` (built for 35 days/315 rows; use `--days 30`). It can be run daily from D1. | A full summary needs the whole run. |

**Other evidence the panel may want on D1:**
- photos of the setup and the sowing;
- `field_log.csv` (restarted by `new-run`; log the sowing time and seed count);
- the live web page;
- the hardware test results (relays and flow Oct 21, valve test Oct 29);
- the GPR validation vs hand labels from run 1 (IoU 0.64 vs 0.79 human-human; bias +0.04 pp; MAE 0.28 pp). Run 1's data is archived and can be shown as a pilot.

## Run 1 (sown Oct 6, archived): what to remember
- Data D8–D22/23 is complete (135 rows by D22). Raw noon frames exist from D12. Pot-area GPR was recomputed for D12–D21 (`cell_gpr.csv`).
- 18 automatic doses. Group means near the end: low 52%, optimal 67%, high 76%. Only P-02 reached the low band. P-06 stuck at ~87% (cause unconfirmed).
- **Problems:**
  - Slow, leggy growth with leaning plants. Noon light varied 7× between days.
  - Leaning plants made pot-circle GPR read 0 (P-05, P-07, P-01), so `cell_gpr` replaced it.
  - The camera was knocked (Oct 21) and drifted 15 px (Oct 27); the ROIs were shifted each time.
  - 17+ Pi power cuts.
  - Probes were wired rotated 180° until Oct 16 (fixed in firmware: `POD_MUX_CH = {8,7,6,5,4,3,2,1,0}`).
- **GPR validation (D12/D13, Cedric + Kent):** program vs humans IoU 0.64, MAE 0.28 pp, bias +0.04 pp; human vs human IoU 0.79, 0.19 pp. Tool: `tools/gpr_validate.py`.
- **Decks:**
  - Oct 22 deck: https://www.canva.com/d/u_OWN5QGGVcM5Lm
  - Oct 28 deck (12 slides): https://www.canva.com/d/Toa08xJjBmFmAnk
  - Sir AJ's answers to the six Oct 28 questions were **never reported back**; ask the user.

## Decisions already made
- **Sowing day = D1.**
- **One capture per day at 12:00**, with retries to 12:50 and a duplicate-day guard. Re-capture only after a technical fault, and log it.
- **Brightness-matched exposure** (target mean V 73; gain and white balance locked). The capture light is used only when 100 ms is still too dark.
- **Pot-area GPR (`cell_gpr`) is the main growth measure in run 2.** `raw_gpr` (pot circle) and `terr_gpr` stay as extra columns.
- **No grow light.** Light is logged hourly with the camera instead.
- **Calibration:** shared two-point (oven-dried / saturated), plus offsets for P-03 and P-05. The user does NOT want a full per-probe recalibration.
- **Fix alignment and mapping in software.** The user prefers not to move hardware; log every change in `field_log.csv`.
- **Generated or made-up data is never accepted as measured data.** Manual data may only go in as clearly labelled supplementary data.

## Gotchas
- **SSH from Claude's Bash:**
  - Needs `dangerouslyDisableSandbox: true`.
  - `groupb.local` often doesn't resolve, so use `crk@172.20.10.7` with `-o HostKeyAlias=groupb.local`.
  - For the Mac scripts: `PI_HOST=172.20.10.7 ./system.sh …`, `./flash_esp.sh`, `./sync_pi.sh push`.
  - In zsh, `$SSH` from `.pi_host.sh` doesn't word-split, so wrap it in `bash -c '…'`.
- **`sync_pi.sh push` sends `.json` files**, so the Mac's `pot_rois.json` overwrites the Pi's. They are identical now (Oct 28); keep them in sync.
- **`simple_command` (`pi_link.py --ping/--status/--bands-on/--reset-state`) needs `pi-link` stopped first.** Serial tools stop `pi-link` and swallow ESP32 events while they run; restart with `sudo -n systemctl restart pi-link`.
- **`GET_SM`/`--snapshot` returns the cached 15-min values.** For fresh readings use `GET_SM_FRESH` or `GET_RAW`, or the web page.
- **Only one program can use the camera at a time.** Never leave `live_feed.py` running near 12:00. The light log skips 12:xx.
- **The Pi has no RTC.** After a power loss it uses a saved clock until the hotspot syncs it; the ESP32 can hand its time back.
- **Quarantine, irrigation counts and germination mode persist in ESP32 flash** across reflashes. `--reset-state` is for a new planting only; `--clear-faults` clears a quarantine.
- **A probe pulled into air reads ~0–6%**, which triggers a dose at the next 15-min check. Unplug the pump for probe work.
- **The user acts fast.** For "do X while I watch" tests, say "wait for my READY".
- **The user may interrupt long waiting loops.** Prefer single checks over polling.

## Files
- **Mac:** `/Users/moapilaw/Desktop/THESIS/`
  - Scripts: `system.sh`, `daily_checkin.sh`, `flash_esp.sh`, `sync_pi.sh`, `gpr_view.sh`, `actuator_test.sh`, `flow_test.sh`, `.pi_host.sh`.
  - Docs: `MOVE_AND_D1_CHECKLIST.md`, `TEAM_NOTES_2026-10-28.md`, `ADVISER_UPDATE_2026-10-20.md`, `DEPLOYMENT_NOTES.md` (dated; doesn't cover run-2 tools).
  - `DATA/`: a snapshot of run 1 up to D22.
- **Pi:** `~/thesis` = `~/THESIS/Dual_Archi`.
  - `growth_dataset.csv`, `exposure_log.csv`, `light_log.csv`, `field_log.csv` (`date,day,pot_id,note`), `cron.log`, `pi_link.log`, `sowing_date.txt`, `pot_rois.json`.
  - `~/agrisentry_data/`: `sm_log.csv` (every 30 min), `irrigation_log.csv`, `error_log.csv`, `band_log.csv`, `power_log.csv`, `frames/` (+ `overlay/`).
  - `~/archive/`: run 1 after `new-run`.
  - `~/fw_main/`: the last flashed firmware.
- **Code:**
  - `Dual_Archi/capture_gpr.py`: noon capture.
  - `Dual_Archi/pi_link.py`: logger daemon.
  - `Dual_Archi/Dual_Archi_Firmware/src/main.cpp` + `include/web_dashboard.h`: ESP32 firmware.
  - `Dual_Archi/tools/agrisentry.sh`: start/stop/status/new-run/bands-on.
  - `Dual_Archi/tools/recompute_cell_gpr.py`: run-1 ROI schedule kept.
  - `Dual_Archi/analyze_yield.py`, `record_harvest.py`, `reliability_report.py`.

## Open questions for the user
- Was the Day 0 pH measured? (Deliverable 2.)
- How will the panel check from D1, and what do they want to see each time?
- Which day do the treatments start (D8 proposed)?
- 30 vs 35 days, and 270 vs 315 rows: what does the adviser accept?
- Camera height at the new site.
- Sir AJ's answers from the Oct 28 meeting.
