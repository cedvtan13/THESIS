Picking up work in progress. Handoff first written 2026-10-29 ~00:30 (the night before run 2's sowing). **Merged 2026-11-01** from two sources: Cedric's Oct 29 session (start of run 2, ROI re-fits, answers from the adviser) and Kent's Nov 1 handoff (D3 check on Oct 31). Kent's claims were checked against his data snapshot (commit `ab88adb`); corrections are marked. You have no prior history with this; everything you need is below.

**Read "Run 2 problems" first.** The run is in trouble on day 3 for the same reason run 1 was, and the cause is power, not software.

## READ FIRST: status Nov 17, 2026 (D20) and rules until harvest

*Updated by Claude with Kent, Nov 17. The latest state is here; older sections below are history.*

### Rules until harvest (Nov 27)
1. **No git commands on the Pi.**
   - On Nov 15 a `git pull`/merge on the Pi put back old copies of `growth_dataset.csv` (wiping the D18 rows written at 12:00) and of `sowing_date.txt` (2026-10-06). Every capture then refused to run until Nov 16.
   - On Nov 17 a Pi pull hit merge conflicts in the live CSVs.
   - `protect_data.sh` (fix kit) blocks merges on the Pi.
   - **Data path:** Pi → laptop (`pull_from_pi.bat`) → GitHub from the laptop.
   - **Code path:** scp only.
2. **Don't run `capture_gpr.py` by hand.** If a retake is truly needed, log who did it, when, why and the exact command.
3. **Don't run `agrisentry.sh start`.** It turns the hourly camera job back on, and that job crashes the Pi at :30.
4. **No re-flashing the ESP32, no moving pots, no replanting.**
5. Every manual action goes in `Dual_Archi/field_log.csv` in the format `date,day,pot_id,"note with time"`.
6. **Complete event log:** `DATA/2026-11-17-run2-event-log.md` records every event of the run (field log plus everything found in the data and logs).
   - Add to it at every update; add corrections as new lines, never edit old entries.
   - The team decides what goes into the manuscript.

### Fix kit (now in the repo: `tools/greenhouse_kit/`, see its README)
- Windows `.bat` files and a Mac/Linux `kit.sh` with the same commands.
- Pulls go to `pi_pulls/` next to THESIS, outside the repo.
- Kent's original copy is in `ThesisCoWork\2026-11-16-greenhouse-kit\`.

Windows `.bat` files: they SSH to the Pi for you and work on the hotspot without internet. The Pi side lives in `~/fixkit/`.

| File | What it does |
|---|---|
| `find_pi.bat` | finds the Pi |
| `send_kit_to_pi.bat` | installs the kit and the 13:15 / 23:45 backups to `~/backups` |
| `check_pi.bat` | daily health check: missing days, sowing date, blue cast, camera shift, pots out of band, logger alive, unlogged doses |
| `pull_from_pi.bat` | copies all data and frames to `ThesisCoWork\pi_pulls\<date>` |
| `tomorrow_fixes.bat` | runs `protect_data.sh` (git guard, hourly light_log off, sowing-date check) and `add_field_notes.py` |
| `apply_cast_guard.bat` | **optional:** blue (overcast) noon frames are retried at the next 10-minute slot; the 12:50 retry always writes |
| `fix_d20.bat` | limits `catch_up.sh` to 12:00 to 12:55 and resolves the duplicate D20 rows |
| `fix_d18.bat`, `run_mask_compare.bat` | done Nov 16 |

Full instructions: `2026-11-16-greenhouse-fix-plan.md` and `2026-11-16-masterplan-nov17.md`.

### Data state (repo, Nov 17)
- **`growth_dataset.csv`:**
  - D1 to D20 present, except D2 and D3 (lost to the Oct 30 to 31 outage, not back-filled);
  - **D18** was recovered Nov 16 from the saved frame;
  - **D20 has two sets** (09:36 from `catch_up.sh` after a reboot, and a 12:42 manual retake).
    - **Decision (Kent): keep 12:42**, flag R.
    - The 12:42 set was a hand run of `capture_gpr.py` (with `--force`, which appends; the team recalls about 1 pm). This is why there are 18 rows. Never use `--force` for a retake.
    - The 09:36 set is moved aside with `fix_d20.bat` at the next visit.
    - Every soil reading rose 15 to 20 points between the two captures.
      - Team suspects the valves actuated (Rey sprayed only P-04).
      - To check at the next pull: sm_log timing, irrigation_log, pi_link.log, power_log.
- **Logs** in `DATA/agrisentry_data/` run to Nov 16 16:57.
- **Change logs:** `DATA/2026-11-16-data-update-log.md`, `DATA/2026-11-17-data-update-log.md`.
- **Full event log:** `DATA/2026-11-17-run2-event-log.md`.

### State of the Pi after Nov 17 afternoon (Kent)
- **Git guard ON:** data files skip-worktree, merge hook installed.
- **Hourly `light_log.py` camera job OFF.**
- **Cast guard APPLIED from D21:** a blue noon frame (blue/red > 1.25) is retried; 12:50 always writes.
- **Backups** at 13:15 and 23:45 to `~/backups`.
- **Still to do:** `fix_d20.bat` (D20 has 18 rows; keep 12:42; it also limits `catch_up.sh` to 12:00 to 12:55).
- **NEW PROBLEM, probe readings oscillate:** since Nov 16 23:44 all probes jump up 15 to 20 points together and drop back within 20 to 30 min, 12 times by Nov 17 13:44.
  - It is electrical (probe supply or ADC), not water.
  - D20 12:42 soil moisture is invalid-high.
  - Check probe power wiring, connectors, moisture on the boards, and the supply.
- **Plants still at the seed-leaf stage at D20** (phone photos), so the mask is reading them correctly.

### Findings (Nov 16 to 17)
- **errors=5946:** all from Nov 9 (D12). 5,910 are repeated BMP388 read failures during the supply fault, and 36 are probe range and quarantine lines. No errors since.
- **Unlogged dose:** P-05, at Nov 9 12:48.
- **Low-GPR days are blue frames.** Overcast light under the locked daylight white balance:

  | Day | Blue/red |
  |---|---|
  | normal days | about 1.0 |
  | D04 | 1.34 |
  | D05 | 1.53 |
  | D12 retake | 1.49 |
  | D19 | 1.84 |

  Loosening the HSV mask doesn't help (tested on the 18 hand-labelled pots: current IoU 0.630 / bias +0.04 pp is already the best). Excess Green indices fail because the rice-hull mulch reads as green.
- **Pi crashes:** 12 Pi-only crashes since Nov 12, mostly at :30, when the hourly `light_log.py` turns the camera on.
- **P-06** reads 25 to 35 points higher after every ~17 mL dose. Likely cause: its tube outlet sits next to the probe (to check).
- **Plants:**
  - **P-01** is waterlogged (90 to 100 %, soil wet to the touch);
  - **P-03** is dead (GPR 0 since D17);
  - **P-04** is wilting (D20: bent by irrigation, straightened, 20 sprays).
- **Canopy stalled after about D11,** at 0.1 to 0.3 % of the pot area (about 1 to 2 cm² of leaf). Raise with Rey (agronomy).
- **Manuscript error to fix:** 4.2.2, Chapter 5 and the abstract say Low < Medium at D12. With P-01 included, Low (61.4) > Medium (53.9). Without P-01, Low is 46.3, so the ordering is correct.

### Growth model (Phase 5, no harvest weights needed)
- **Protocol fixed before analysis:** `DATA/2026-11-17-growth-model-protocol.md`, committed before any run.
- **Design:** 8 plants (P-03 excluded), `cell_gpr`; D20 = the 12:42 set.
- **Primary test:** fit D1 to D15, test D16 to D20. **Secondary:** a rolling 1 to 3 day forecast.
- **Flagged rows:** run with all rows, and again without them.
- **Models:** logistic, Gompertz, linear, against persistence baselines.
- **Next:** Claude writes `tools/growth_model.py` and the results go to `DATA/model_preview/`; then the team debriefs.

### Next (see the masterplan)
1. On site:
   - `tomorrow_fixes.bat`;
   - `fix_d20.bat`;
   - the decision on `apply_cast_guard.bat`;
   - physical checks: phone close-ups of P-01, P-04, P-05, P-07 and P-03; the P-06 outlet; the P-01 saucer; the camera mount;
   - `run_mask_compare.bat`;
   - `pull_from_pi.bat`.
2. **Growth model (logbook Nov 9 plan, no harvest weights needed):**
   - fit `cell_gpr` on D1 to D15 and test on D16 to D20 against a "last value" baseline;
   - the protocol is committed *before* running, in `DATA/2026-11-17-growth-model-protocol.md`.
3. Literature on early-season prediction (Sir AJ, Nov 5).
4. Harvest Nov 27 (D30): 0.01 g pocket scale checked with a new coin; `record_harvest.py`.

## Current Status & Manuscript Overhaul (November 12, 2026)
- **Manuscript Overhaul:** Located in `2026-11-11-GroupB-Manuscript-Draft1/`. Chapters 1, 2, and 3 have been completely overhauled:
  - Tense pass (past/present).
  - Scope and bench parameters reconciled (30-day cycle, 9 pots, up to 270 rows).
  - Substrate specification: 8:4:3 volumetric mix (garden soil : carbonized rice hull : vermicast).
  - Truncated-cone pots: 110 mm top, 85 mm base, 80 mm depth ($601\text{ cm}^3$ volume, 388 g dry / 662 g saturated substrate).
  - Moisture calibration: Two-point calibration (2483 ADC dry to 1120 ADC saturated) mapped to True VWC ($\times 0.456$).
  - Vision pipeline: Raspberry Pi Camera Module 3 (IMX708) at 136 cm elevation, brightness-normalized exposure ($V = 73$), locked WB, Voronoi pot-area `cell_gpr` ($r \le 175\text{ px}$), $3 \times 3$ morphological opening kernel, and lossless noon PNG archival from D12.
  - Predictive modeling: Parsimonious 6-term polynomial model evaluated strictly by LOOCV.
  - Literature: 5 key references added and cited (Ding 2022, Cho 2015, Hosoda 2024, Kim 2022, Lee 2024).
- **Appendices Updated:** Appendix 4 (BOM updated to 9 sensors, 9 valves, Camera Module 3, BMP388, cooling fans), Appendix 6 (WBS), Appendix 7 (Vision daemon pseudocode), Appendix 8 (CSV log structure with `Cell GPR`).
- **Panel Revision Letter:** `REVISION_LETTER.md` in root contains the complete 9-item formal revision letter to Dr. Cañete, Engr. D’Silva, and Engr. Labarosa with all measurements and rationale filled in.
- **Fast Build & Live Preview:** Run `./compile.sh` inside `2026-11-11-GroupB-Manuscript-Draft1` to compile the 78-page `thesis.pdf` in ~5 seconds. Run `python3 auto_watch.py` for background auto-recompilation on save.
- **Run 2 State:** Sown Oct 29, 2026 (D1). D8 bands activated Nov 5 at 11:44 AM. Currently at D14/D15. D2–D3 outage reported transparently in Chapter 4 without synthetic data. Harvest scheduled on D30 (November 27, 2026).
- **Daily Inspection Command (`./check_system.sh`):** Connect laptop to Pi hotspot (or pass `PI_HOST=<ip>`), run `./check_system.sh` (or tell AI **"check system"**). It checks NTP clock sync, service daemons, Run 2 progress, pot moisture vs. bands, noon capture GPR, runs `roi_drift.py` on the latest frame to check camera/pot alignment, copies the alignment verification image to `~/Desktop/AgriSentry_ROI_Check.jpg`, and pulls latest telemetry to `_pi_data/`.
- **Handoff & Work Sync Command (`./sync_work.sh [hardware|manuscript|auto]`):**
  - For hardware/field checks: `./sync_work.sh hardware "D15 field check notes"` (or tell AI **"update handoff"**). Updates `HANDOFF.md` with Run 2 Day index, local telemetry stats, commits, and pushes to git.
  - For manuscript work: `./sync_work.sh manuscript "revised Ch3"` (or tell AI **"update manuscript"**). Recompiles `thesis.pdf` via Tectonic, updates word counts in `MANUSCRIPT.md`, commits, and pushes to git.

## Project
AgriSentry is an undergraduate thesis: "Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse".
- 9 pechay pots in 3 soil-moisture groups.
- Every day at noon, a top-down camera measures each pot's canopy Green Pixel Ratio (GPR).
- After harvest, an OLS polynomial regression with leave-one-plant-out cross-validation (LOOCV) predicts each plant's harvest weight.

**People**
- Adviser: **Engr. Alvin Joseph Macapagal** ("sir AJ"). Chair panel: **Sir Luis**.
- Students: Cedric Vince Tan, Kent Vincent Godinez, Rey Emmanuel Adag.

**Hardware**
- **Raspberry Pi Zero 2 W** (`crk@groupb.local`): camera, GPR, CSV logging.
- **Custom ESP32-S3 board:** reads the soil probes through a MUX, plus a BMP388 sensor, and drives 12 relays (9 valves, pump, Pi fans, capture light). It runs the watering by itself and doesn't need the Pi for it.
- The two talk over UART (`/dev/ttyAMA0`, 115200).

**Network**
- The Pi is offline except when a phone hotspot is on.
- **The IP changes with whose hotspot is used.** It was `172.20.10.7` on the iPhone hotspot "Cvtan"; on Oct 31 it was `10.25.220.66`. Find it by MAC instead of guessing. **The Pi's MAC is `88:a2:9e:51:89:a0`.**
  - Windows: `1..254 | ForEach-Object { ping -n 1 -w 100 10.25.220.$_ > $null }; arp -a | findstr 88-a2-9e-51-89-a0` (adjust the subnet to the laptop's own IP).
  - Mac: `arp -an | grep -i 88:a2:9e:51:89:a0` after a ping sweep, or `dns-sd -G v4 groupb.local`.
- The ESP32 has its own Wi-Fi network **"AgriSentry"** (password `agrisentry`), live page at **http://192.168.4.1**. **Don't join it from the phone running the hotspot**: that turns the hotspot off and cuts the Pi off.
- **The Pi Zero 2 W only does 2.4 GHz.** On an iPhone hotspot, turn on "Maximize Compatibility".

**Pot layout, as seen by the camera**

| | left | middle | right |
|---|---|---|---|
| top | P-03 | P-02 | P-01 |
| middle | P-06 | P-05 | P-04 |
| bottom | P-09 | P-08 | P-07 |

**Moisture groups (bands)**
- P-01 to P-03: low, 30 to 40%.
- P-04 to P-06: optimal, 50 to 60%.
- P-07 to P-09: high, 70 to 80%.
- The % is relative to the two-point calibration (0 = oven-dried soil, 100 = saturated soil), **not true VWC**.
- **Until `bands-on`, germination mode holds every pot at 50 to 60%.**

---

## Run 2 dates and plan
- **Sowing Oct 29 (~12:30) = D1, 2 seeds per pot. D30 = Nov 27** (`CYCLE_DAYS = 30`). Nov 1 = D4.
- **Emergence:** first seedlings seen in P-04 and P-08 on D3 (phone photos). Check every pot for a seedling; with only 2 seeds, a pot with none by ~D6 needs a transplant from the backup tray (log it).
- **Thin to 1 seedling per pot by D7 = Nov 4** (the most uniform 9; log it).
- **Treatments start D8 = Nov 5:** `./system.sh bands-on` (ends germination mode).
- **Harvest D30 = Nov 27.** 2nd checking Nov 23 to 28.
- **Panel checks:** the chair panel (Sir Luis, via Sir AJ) had the team plant and start the system on Oct 29 and checked it that afternoon (~15:00). They check from D1 on, going by whichever deliverables exist at that point. What they want each time is still to be confirmed.

---

## Run 2 problems (found Oct 31, D3): READ THIS FIRST

### 1. Power: the Pi was off for about 41 hours straight, and the ESP32 loses power too
- **Only D1 was captured**, by hand at **13:14** on Oct 29 (the Pi was off at 12:00; see the Oct 29 session below). D2 (Oct 30) and D3 (Oct 31) never ran.
- `sm_log.csv` (every 30 min) and `light_log.csv` (hourly) both have **no rows at all from Oct 30 00:27 to Oct 31 17:21**. That is one continuous outage of about 41 hours, covering both noons. Roughly 25 of ~106 due soil readings exist.
- Every restart in `power_log.csv` since sowing:
  - Oct 29 13:20 and 13:44, and ~14:24 (while the camera rig was being moved). At 13:20 and 13:44 the **ESP32 restarted too**.
  - Oct 29 17:19, 17:24 and 17:29 (Pi only).
  - Oct 30 00:15 (Pi only), then 00:48 (**ESP32 too**). Then nothing until Oct 31 ~16:50 (**ESP32 too**).
- **The ESP32 losing power at the same moments as the Pi means the shared supply or main plug is cutting out, not just the Pi's cable.** The Pi also boot-looped on Oct 28 evening and overnight into Oct 29.
- The cron is ON and the system is healthy whenever it is up.
- **This is the top priority.** Check what the rig is plugged into at the new site, whether the UPS is carrying it, and whether the Pi's charger and cable are solid (5 V, at least 2.5 A, short cable, into the **PWR** port).

### 2. D2 and D3 GPR are marked MISSED, not back-filled
- Decision by Cedric, Nov 1: *"well mark that nalang nga missed day"*, and *"as long as wala tay gi modify"*.
- This follows the standing decision below: generated data is never accepted as measured data.
- **Do not write zeros for D2 or D3.** A zero is a measurement, and no measurement was taken.
- D3 GPR cannot be recovered. The only D3 image is a `roi_view.jpg` taken at 19:00 that came back at mean V 0.1 (a black frame). A phone photo is not a substitute: GPR needs the rig camera at the locked geometry with the fitted ROIs.
- **D3 soil moisture from 17:21 on IS logged and valid.** Only the GPR is missing.
- **Settled with Cedric (Nov 1):** D2 = missed day (GPR and soil, apart from 00:27). D3 = GPR missed, soil moisture valid.
- **D3 phone photos are kept as supplementary evidence only:** `PHOTOS/run2_D03_2026-10-31_phone_SUPPLEMENTARY/` (3 evening photos, a zoom and the 18:21 soil screenshot; README explains). They show the **first seedlings in P-04 and P-08**. They give no GPR value: different camera with auto exposure and white balance, handheld and tilted, at dusk.
- **The misses are not in `field_log.csv` yet** (as of the Oct 31 snapshot). Add them, plus the seed count and the D3 emergence note.

### 3. The soil is saturated, and it got wetter with no irrigation
Germination mode targets 50 to 60%. Readings at Oct 31 18:21:

| Pot | % | | Pot | % | | Pot | % |
|---|---|---|---|---|---|---|---|
| P-01 | 71.6 | | P-04 | 100.0 | | P-07 | 100.0 |
| P-02 | 59.5 | | P-05 | 89.6 | | P-08 | 99.5 |
| P-03 | 71.9 | | P-06 | 79.3 | | P-09 | 100.0 |

- Eight of nine above band, four at or near saturation. **342 above-band notices, 0 irrigation events.**
- The watering logic is behaving correctly. The soil started saturated (it was watered at sowing).
- **Moisture rose while the system gave no water:** P-03 went 55.1% (Oct 29 13:14) → 59.1% (Oct 30 00:27) → 71.9% (Oct 31 18:21); P-01 66.9 → 71.6; P-05 83.2 → 89.6. Something added water: hand watering, rain or leaks through the cover, or a valve leak. **Ask the team.**
- `TEAM_NOTES_2026-10-28.md` set the fix for this: *"Mix all the soil, then let it air-dry until it's moist, not saturated, so the treatments start within days."* That was not done.
- Run 1 failed partly because the low group never dried. The same thing is happening again on day 3.

### 4. ~~D1 may be missing P-03~~: RESOLVED, D1 has all 9 pots
Checked in Kent's snapshot (`DATA/thesis/growth_dataset.csv`, commit `ab88adb`): D1 has 9 rows, P-01 to P-09, all at 13:14. P-03 is there (sm 55.1%). Nothing to log.

### 5. The capture light does not work
Confirmed Oct 31, 19:00. `roi_view.py` reported mean V 0.1 at 100 ms, auto-switched the capture light on, and brightness moved only to 0.3. The relay ACKs but the lamp does nothing. It matters on dark days and for any night ROI work.

### 6. The Pi cannot reach GitHub, and holds work that exists nowhere else
- **Outdated (Nov 17):** the Pi did push over HTTPS on Nov 15 and Nov 17, and both times git damaged live data. Since Nov 17: no git on the Pi; see READ FIRST at the top.
- On the Pi: `git pull` fails with `ssh: connect to host github.com port 22: Connection timed out`. Port 22 is blocked on the hotspot.
- `git status` on the Pi: **1 commit ahead of origin**, plus about 40 modified or deleted files uncommitted, including `pot_rois.json`, `sowing_date.txt`, `capture_gpr.py`, `pi_link.py` and `tools/` (including Kent's `tools/roi_view.py`, which is not in the repo).
- **That work exists only on the SD card.** If the card fails, it is gone.
- Fix options: switch the Pi's remote to HTTPS so port 443 is used instead of 22, or pull the files off by `scp` and commit them from a laptop.
- The Mac now has the Oct 29 versions of `pot_rois.json` (+ 3 backups) and `tools/agrisentry.sh` (status fix); see the Oct 29 session.

### 7. ROI drift check still outstanding
Could not be done Oct 31 (darkness). Must be done **in daylight, 09:00 to 11:30**, before the noon capture window.

**Important: `DXX_overlay.jpg` cannot be used for this.** `capture_gpr.py` draws the **cell** and territory boundaries on that file, not the pot circles. They are more than twice the radius and will never line up with a rim.

**Use `tools/roi_view.py`** (on the Pi only), which draws yellow = pot circle (r = 77), cyan = pot cell, magenta = counted green:
```bash
ssh crk@<ip> "cd ~/THESIS/Dual_Archi && LIBCAMERA_LOG_LEVELS='*:ERROR' python3 tools/roi_view.py /tmp/roi_view.jpg"
scp crk@<ip>:/tmp/roi_view.jpg .
```
`roi_view.jpg` has a 70 px caption band stacked on top, so **subtract 70 from any y read in an image viewer**.

**Current centres to compare against** (the live `pot_rois.json`, re-centred Nov 3 16:00 for the D5→D6 drift, r = 77; the Oct 29 14:45 fit is in `pot_rois_before_D6_recentre.json`):

| Pot | centre x | centre y | | Pot | centre x | centre y |
|---|---|---|---|---|---|---|
| P-01 | 968 | 309 | | P-06 | 290 | 699 |
| P-02 | 621 | 307 | | P-07 | 1003 | 1030 |
| P-03 | 274 | 314 | | P-08 | 651 | 1045 |
| P-04 | 992 | 656 | | P-09 | 277 | 1072 |
| P-05 | 647 | 673 | | | | |

**Measure drift on the saved noon frame** (`frames/DXX_*.png`) instead of taking a new photo: it needs no camera, so it can't clash with the cron jobs or trigger a restart.

Drift is a rigid shift: all nine offsets should point the same way by about the same amount. Scattered offsets mean measurement error, not drift. One pot off and eight fine means that pot moved, not the camera.

---

## Oct 29 session (Cedric + Claude): start of run 2
- **The Pi was off or boot-looping from ~21:17 Oct 28 until 12:57 Oct 29**, so the 12:00 capture never ran.
- **13:05: `new-run 2026-10-29`.** Run 1 archived to `~/archive/run_sown_2026-10-06_archived_20261029_130528/` (nothing deleted). The ESP32 ACKed `RESET_STATE` (germination mode ON). Logger, 12:00 capture and hourly light log ON.
- **The camera shifted ~50 px between 13:06 and 13:11.** Pot circles re-fitted (Hough on a daylight frame).
- **13:14: D1 captured by hand** (logged as a one-off technical fault). 9 rows, GPR 0.00% everywhere (nothing germinated), plus `frames/D01_2026-10-29_1314.png` and `D01_overlay.jpg`.
- **14:28 to 14:45: the team repositioned the camera**, removed a plastic sheet from the view and nudged P-07 to P-09. Circles re-fitted at 14:38 (all pots, `frames/roi_fit_D01.png`), then P-01 re-centred and P-07 to P-09 re-fitted at 14:45 (`frames/roi_fit_D01_b.png`, zoomed rim crops). Backups: `pot_rois_before_D1_realign.json` (Oct 28 night fit), `pot_rois_before_D1_1440_realign.json`, `pot_rois_before_D1_1445_tweak.json`.
- **The pot cells (`cell_gpr`, 175 px) were checked:** one per pot, no overlap, none clipped by the frame edge, green net and grass at the edges excluded.
- **The territory circle (`terr_gpr`) still uses run 1's scale** (`PX_PER_MM = 1.34`, r = 221 px; about 200 px would be right at the new height). Left as is: it's an extra column. Fix once the camera height is measured.
- **`agrisentry.sh status` now shows the watering mode** (germination: all pots vs 50 to 60% until `bands-on` appears in `field_log.csv`; then the three bands). It also prints the log tail cleanly when `pi_link.log` holds NUL bytes from power cuts. Deployed to the Pi.
- **All of this is in `field_log.csv` on the Pi** (6 lines, Oct 29).

---

## Nov 1 to Nov 3 (D4 to D6)
- **Nov 1:** Cedric powered the Pi at 11:42. Field log filled in (2 seeds per pot, D2/D3 misses, seedlings, power cut). **Hand watering by the team since sowing explains the rising moisture; decision: it stops from Nov 1, the ESP32 does all watering.**
- **D4, D5, D6 captured** (12:10, 12:10, 12:00). Seedlings counted in P-04, P-05, P-07, P-08, P-09. Rey pushed the D6 snapshot (`ed48eaf`).
- **Soil is drying** since hand watering stopped: P-02 back in band (55.8%), P-01 68%, P-03 63% (Nov 3 14:46). P-04/P-07/P-09 still 96-100%.
- **The Pi restarts when the camera starts.** It went down right at the 12:00 capture on Nov 1 and Nov 2 (the 12:10 retry worked), at 15:30 on Nov 1 (that light reading is missing) and at 15:30 on Nov 3 (three boots, two dying in seconds). Other restarts happened with the camera idle, and the ESP32 lost power too (latest Nov 3 15:02). **Fix: a proper 5.1 V 3 A Pi supply with a short thick cable, ideally its own adapter; check the rig's main outlet.**
- **P-07 read 0% on D6 although it has seedlings:** it was in direct sun (D6 exposure 1.6 ms, about 5× shorter than D4/D5) and the seedlings looked yellowish, so they fell outside the green thresholds. A detection miss, not drift: every pot is well inside its cell. The exposure floor is 1 ms (`EXPOSURE_MIN_US`), and the 10:30 light reading on Nov 3 was over-bright even at 1 ms. Shade over the top would help.
- **Camera drift confirmed (Rey was right):** on the noon frames vs Oct 29 14:41 the shift was ~+7 px (D4), ~+5 (D5), ~+16 to +20 (D6), all to the right, so it moved mostly between D5 and D6. Pots stayed well inside their cells (`cell_gpr` unaffected). **Pot circles re-centred Nov 3 ~16:00** on the D6 noon frame (P-01, P-04, P-07 by eye; saucer and glare pulled their fits); applies from D7. Logged in `field_log.csv`.
- **The uneven noon light** is sun patches through the frame and cover: on D6 the sunlit P-07 pot read ~3× brighter than shaded pots (V ~198 vs ~71), and its leaves clipped and read hue 30-33, under the H 38 threshold. **Proposed fix: a diffuser (white shade net or translucent sheet) over the top; log the date.** Not a software threshold change.
- **Until the diffuser is in, glare is logged per pot per day:** `tools/glare_check.py` reads the saved noon frame (never the camera) and writes `~/thesis/glare_log.csv` (clipped %, brightness vs the median pot, level GLARE / MILD / DARK / ok) plus one `field_log.csv` line on flagged days. Back-filled: D1 and D4 clean, D5 P-07 MILD, D6 P-01/P-04/P-07 GLARE and P-09 DARK. Daily run at 12:55 via `GLARE_LINE` in `agrisentry.sh` (`cron_set`). **`growth_dataset.csv` is never edited for glare.** `analyze_yield.py` joins `glare_log.csv` on (day, pot_id): by default all rows are used and the six-term model is fitted again without the GLARE rows (reported as the glare check); `--exclude-glare glare|glare+mild|any` makes an exclusion the main fit. Rows are dropped before the 3-day smoothing.
- **`DATA/` run 1 leftovers moved to `DATA/run1_leftovers/`** (README inside).
- **The Pi's CSVs use Windows line endings (CRLF); the copies in `DATA/` use LF** (except `power_log.csv`). Match the committed style when copying, or every row shows as changed.

---

## Nov 4 (D7)
- **Power got worse:** 13 Pi restarts between 16:26 and 20:06 on Nov 3 with the camera idle, then the rig was off ~15 h until ~11:34 Nov 4 (ESP32 too). **Replace the Pi's supply/cable; this is the top risk.**
- **D7 captured at 12:00 on the first try, no restart.** Camera ~1 px from D6 (11:45 check frame `frames/roi_check_D07.png`); circles on the rims.
- **D7 GPR (cell, %):** P-08 0.45, P-04 0.39, P-09 0.23, P-05 0.21, P-02 0.05 (new seedling today), P-01/P-06 0.
  - **P-03 0.70 is not a plant:** a green object on the cloth outside the pot, in the P-03 cell. Logged; remove it before D8 noon.
  - **P-07 0 = glare again** (pot V ~181, 5.5 % clipped, ~2.4× the median pot). Its spot (bottom right) gets the noon sun through the same gap every sunny day. **Not re-captured:** glare is the real noon light, not a technical fault; re-taking at another time would cherry-pick conditions. Fix: a white diffuser over the top.
- **Hand spraying:** Nov 3 ~15:00 all pots (~12 sprays each); Nov 4 11:39-12:03 P-03 (~12 sprays, 65.7 -> 74.5 %). Both logged. No more watering by hand from D8.
- **Emergence:** seedlings in P-02, P-04, P-05, P-07, P-08, P-09; **none in P-01, P-03, P-06.** Seeds were placed on the surface; the empty pots look more covered by light flakes, but moisture level doesn't explain it (the wettest pots germinated). **Decision: don't re-mix those pots** (would disturb the probes and the uniform soil). Transfer spares (P-04, P-07, maybe P-08) on D7 ~16:00 into P-01 and P-03 first, then P-06: push the flakes aside only at the planting spot, plant with a soil plug, log each move. Then `bands-on` on D8.

---

## Deliverables (Table I of the manuscript) and status
**30 days / 270 rows is accepted** (Oct 29): the adviser does not require the manuscript's 35 days / 315 rows, prefers an earlier harvest if justified, and asked the team to **find sources showing pechay can be harvested at ~30 days (or earlier)**. The manuscript has to be updated. Missed days (D2, D3) lower the row count further.

| # | Objective | Deliverables | Status | Can't be done yet |
|---|---|---|---|---|
| 1 | Deploy 1:1 solenoid baseline irrigation for 3 VWC groups | Two-point sensor calibration log; automated irrigation log | Calibration values exist (2483/1120, oven-dried 150 °C for 6 h, and saturated), plus the Oct 28 offsets. **A written calibration log is still not written** (asked for in the Oct 20 adviser update). `irrigation_log.csv` is empty: 0 doses so far, because every pot is above band. Flow 18 mL/s on all valves. | Groups inactive until `bands-on` (D8). % is not true VWC. |
| 2 | Uniform growing environment | Day 0 pH table; HSV tuning values; `pot_rois.json` | **pH: planned for Oct 29 after sowing; not confirmed done, and not in `field_log.csv`.** HSV fixed in code (H 38 to 85, S ≥ 100, V ≥ 55, 3×3 opening); no write-up yet. `pot_rois.json` done (Oct 29 14:45 fit). | If pH wasn't measured on Oct 29, Day 0 has passed. |
| 3 | Daily canopy images, GPR for 9 plants | Per-pot GPR CSVs; daily capture log; GPR plots | **Only D1 exists, and it is all zeros. D2 and D3 are missed days.** Capture log: `cron.log`, `exposure_log.csv`, saved frames and overlays. Plots: `tools/gpr_view.py`. | **The series has a two-day hole at D2 and D3.** Must be disclosed in the results. |
| 4 | Ground-truth fresh-weight biomass | 9-pot harvest table; scale check sheet | `record_harvest.py` ready. **The scale check can be done now** (weigh a known mass 3×). | Weights exist only at harvest (D30 = Nov 27). |
| 5 | Multivariate polynomial regression | Training CSV; equation with β0 to β5; correlation matrix | `analyze_yield.py` (six-term spec; `--self-test` proves the machinery). | Needs harvest weights. 270 rows minus missed days. |
| 6 | LOOCV performance | LOOCV R²; MAE (g); predicted vs actual; residual plots | Same script. | After harvest. |
| 7 | Software failure detection and recovery | Error log; reliability summary | `error_log.csv`, `power_log.csv`, `band_log.csv`; `reliability_report.py` (use `--days 30`). **The power events and missed captures are themselves evidence for this deliverable** and should be reported as findings, not hidden. | A full summary needs the whole run. |

**Other evidence the panel may want:**
- photos of the setup and sowing;
- `field_log.csv` (sowing time is logged; **seed count, pH and the D2/D3 misses still need adding**);
- the live web page;
- hardware test results (relays and flow Oct 21, valve test Oct 29);
- GPR validation vs hand labels from run 1 (IoU 0.64 vs 0.79 human-human; bias +0.04 pp; MAE 0.28 pp). Run 1's data is archived and can be shown as a pilot.

---

## Still to do (in order)
1. **Fix the power** (problem 1). Nothing else matters until the Pi stays up through noon.
2. **Add to `field_log.csv` on the Pi** (needs the Pi online): 2 seeds per pot at sowing; D2 missed (GPR and soil); D3 GPR missed, soil valid; D3 first seedlings in P-04 and P-08 (supplementary phone photos); the pH readings, if measured.
3. **Find out what wetted the soil** after sowing (problem 3) and decide what to do about saturation before D8.
4. **ROI drift check in daylight** against the corrected table.
5. **Get the Pi's uncommitted work off the SD card** (problem 6).
6. **Thin by D7 (Nov 4)**, then **`bands-on` on D8 (Nov 5)**.
7. Measure the camera height (lens to soil) and log it.
8. Sources for a ~30-day pechay harvest, for the manuscript.

---

## Run 1 (sown Oct 6, archived): what to remember
- Data D8 to D22/23 complete (135 rows by D22). Raw noon frames from D12. Pot-area GPR recomputed for D12 to D21 (`cell_gpr.csv`).
- **Commit `ab88adb` replaced the run 1 snapshot in `DATA/` with run 2's.** Run 1's snapshot is still in git history (before `ab88adb`) and in full on the Pi in `~/archive/`.
- 18 automatic doses. Group means near the end: low 52%, optimal 67%, high 76%. Only P-02 reached the low band. P-06 stuck at ~87%.
- **Problems:** slow leggy growth with leaning plants; noon light varied 7× between days; leaning plants made pot-circle GPR read 0 (P-05, P-07, P-01), so `cell_gpr` replaced it; the camera was knocked (Oct 21, 209 px) and drifted (Oct 27, 15 px); 17+ Pi power cuts; probes wired rotated 180° until Oct 16.
- **GPR validation (D12/D13, Cedric + Kent):** program vs humans IoU 0.64, MAE 0.28 pp, bias +0.04 pp; human vs human IoU 0.79, 0.19 pp. Tool: `tools/gpr_validate.py`.
- **Decks:** Oct 22 https://www.canva.com/d/u_OWN5QGGVcM5Lm ; Oct 28 https://www.canva.com/d/Toa08xJjBmFmAnk

---

## What was done on Oct 28 (pushed to GitHub `cedvtan13/THESIS`, `main`)
- **New tools for run 2** (commit `9041f31`): `agrisentry.sh new-run DATE` and `bands-on`; live pot-area GPR (`cell_gpr`, `cell_green_px`, `cell_total_px`): each pot owns the pixels nearest its centre, up to 175 px, with no overlap; daily `frames/overlay/DXX_overlay.jpg`; `tools/light_log.py` (cron `30 6-11,13-18`); `analyze_yield.py --gpr-column` (default `cell_gpr`).
- **Checklist:** `MOVE_AND_D1_CHECKLIST.md`. Team notes: `TEAM_NOTES_2026-10-28.md`.
- **UART wiring after the move** (TX/RX had been swapped): Pi pin 8 (TX) → ESP32 GPIO44 (RX); Pi pin 10 (RX) ← ESP32 GPIO43 (TX); Pi pin 16 → EN; Pi pin 18 → BOOT.
- **ESP32 firmware v6-web** (commits `6faf5ba`, `c8a970a`, `682ead4`): own Wi-Fi + live page (all 9 probes every 2 s, probe finder); **test watering** (valve + pump, 1 to 10 s, logged as `LOG,WEB_TEST` + `ACK,MANUAL_WATER`); probes on ADC1, so Wi-Fi doesn't disturb them.
- **Probe check:** every probe confirmed in the right pot.
- **Calibration offset for P-03 and P-05** (commit `682ead4`): their dry and wet points shifted by −103 and −75 counts so they read ~5.9% in air like the others. Span unchanged.
- **Pot circles fitted on a night frame** (commit `8d69302`), r = 77. Superseded by the Oct 29 daylight fits.

---

## Decisions already made
- **Sowing day = D1.**
- **One capture per day at 12:00**, retries to 12:50, duplicate-day guard. Re-capture only after a technical fault, and log it.
- **A capture that did not run is a missed day.** It is never back-filled with a zero or any other value (Cedric, Nov 1).
- **30-day run, 270 rows** (adviser, Oct 29). **Treatments start D8 = Nov 5**; thin by D7.
- **Brightness-matched exposure** (target mean V 73; gain and white balance locked). The capture light is used only when 100 ms is still too dark, and **as of Oct 31 the capture light does not work**.
- **Pot-area GPR (`cell_gpr`) is the main growth measure in run 2.** `raw_gpr` and `terr_gpr` stay as extra columns.
- **No grow light.** Light is logged hourly with the camera instead.
- **Calibration:** shared two-point (oven-dried / saturated), plus offsets for P-03 and P-05. No full per-probe recalibration.
- **Fix alignment and mapping in software.** Prefer not to move hardware; log every change in `field_log.csv`.
- **Generated or made-up data is never accepted as measured data.** Manual data may only go in as clearly labelled supplementary data.

---

## Gotchas
- **The daily overlay `DXX_overlay.jpg` draws cell/territory boundaries, not pot circles.** Use `tools/roi_view.py` for any ROI drift check (subtract 70 from y).
- **`make_rois.py` rewrites `_comment` and destroys the ROI change history.** Its defaults are also stale (200 mm pots, 350 mm pitch, 2304×1296 frame). Never use it to realign; set the circles by hand (or by a per-pot rim fit) and prepend to `_comment`.
- **Moving the camera rig has cut the power more than once.** Fix the cables before touching the rig, and only move the camera with the Pi unplugged.
- **The `.sh` wrappers are Mac-only** (`rsync`, `open`, `uname != Darwin`). On Windows, run the Python over SSH directly.
- **Git push from a phone hotspot often fails** with `Recv failure: Connection was reset`. Fix: `git config --global http.version HTTP/1.1` and `git config --global http.postBuffer 524288000`.
- **The Pi's git remote uses SSH, and port 22 times out on the hotspot.** Switch it to HTTPS or move files by `scp`.
- **SSH from Claude's Bash:** needs `dangerouslyDisableSandbox: true`; `groupb.local` often doesn't resolve, so use the IP with `-o HostKeyAlias=groupb.local`. In zsh, a command held in a variable doesn't word-split: write the ssh command out in full (or wrap it in `bash -c`).
- **The Pi's `/tmp` is cleared on every restart.** Keep reference frames in `~/agrisentry_data/frames/`.
- **`sync_pi.sh push` sends `.json` files**, so the Mac's `pot_rois.json` overwrites the Pi's. Keep them in sync.
- **`pi_link.py --ping/--status/--bands-on/--reset-state` needs `pi-link` stopped first.** Restart with `sudo -n systemctl restart pi-link`.
- **To log a soil reading on demand without stopping `pi-link`:** `touch ~/agrisentry_data/request_sm`; a row lands in `sm_log.csv` within seconds (cached 15-min values).
- **The ESP32's 30-min soil report restarts its timer every time the ESP32 restarts**, so after a power cut the next row can be up to 30 min late.
- **`GET_SM`/`--snapshot` returns cached 15-min values.** For fresh readings use `GET_SM_FRESH`, `GET_RAW`, or the web page.
- **Only one program can use the camera at a time.** Never leave `live_feed.py` running near 12:00. The light log skips 12:xx.
- **The Pi has no RTC.** After a power loss it uses a saved clock until the hotspot syncs it. A wrong clock at noon means a wrong day number, and D is a term in the model.
- **Quarantine, irrigation counts and germination mode persist in ESP32 flash** across reflashes. `--reset-state` is for a new planting only; `--clear-faults` clears a quarantine.
- **A probe pulled into air reads about 0 to 6%**, which triggers a dose at the next 15-min check. Unplug the pump for probe work.
- **Pi LED:** steady ~1 s blink = crashed (cut power and restart); fast random blinks = running normally.

---

## Files
- **Mac:** `/Users/moapilaw/Desktop/THESIS/`: scripts `system.sh`, `daily_checkin.sh`, `flash_esp.sh`, `sync_pi.sh`, `gpr_view.sh`, `.pi_host.sh`; docs `MOVE_AND_D1_CHECKLIST.md`, `TEAM_NOTES_2026-10-28.md`, `ADVISER_UPDATE_2026-10-20.md`, `DEPLOYMENT_NOTES.md`. `DATA/`: run 2 snapshot as of Oct 31 18:30 (`ab88adb`).
- **Windows (Kent):** `C:\Users\Dell\Desktop\RESEARCH CODES - AGRISENTRY\THESIS`: same repo, `DATA/` snapshots committed from here.
- **Pi:** `~/thesis` = `~/THESIS/Dual_Archi`.
  - `growth_dataset.csv`, `exposure_log.csv`, `light_log.csv`, `field_log.csv` (`date,day,pot_id,note`), `cron.log`, `pi_link.log`, `sowing_date.txt`, `pot_rois.json` (+ `pot_rois_before_*.json` backups).
  - `~/agrisentry_data/`: `sm_log.csv` (every 30 min), `irrigation_log.csv`, `error_log.csv`, `band_log.csv`, `power_log.csv`, `frames/` (+ `overlay/`, `roi_fit_D01*.png`).
  - `~/archive/`: run 1.
- **Code:** `capture_gpr.py` (noon capture), `pi_link.py` (logger daemon), `Dual_Archi_Firmware/src/main.cpp` + `include/web_dashboard.h` (ESP32), `tools/agrisentry.sh`, `tools/recompute_cell_gpr.py`, `tools/roi_view.py` (Pi only), `analyze_yield.py`, `record_harvest.py`, `reliability_report.py`.

---

## Open questions for the user
- **What is powering the rig at the new site, and is the UPS carrying it?** The ESP32 lost power too, at least four times since sowing.
- **What wetted the soil after sowing?** Moisture rose with zero irrigation.
- **Was the Day 0 pH measured on Oct 29?** If so, add the readings to `field_log.csv`.
- **What did the panel say at the Oct 29 ~15:00 check, and what do they want to see next time?**
- Camera height at the new site, lens to soil.
- Sources for a ~30-day pechay harvest.


## Daily Sync & Field Log History

- **Sync (2026-11-17 evening):** growth model protocol committed before analysis (Phase 5.1).

- **Sync (2026-11-17 afternoon) -- Day 20 (Claude with Kent):**
  - Fixes run on the Pi: git guard, light_log off, cast guard applied, field notes.
  - Pull `pi_pulls/2026-11-17_1606` copied into the repo.
  - Kit added to `tools/greenhouse_kit/`; `pi_pulls/` added to `.gitignore`.
  - Probe oscillation found. D20 duplicate still to fix.

- **Sync (2026-11-17) -- Day 20 of 30 (Claude with Kent):**
  - Nov 16: fix kit installed on the Pi; D18 recovered from the saved frame; data pulled and pushed from the laptop (`8ae042d`, log `DATA/2026-11-16-data-update-log.md`).
  - Nov 17: D20 pushed from the Pi by Rey (`c52f561`, merge `2f10bb1`); D20 has duplicate rows (09:36 and 12:42), fix prepared (`fix_d20.bat`); log `DATA/2026-11-17-data-update-log.md`.
  - Rules added at the top: no git on the Pi, how to push.

- **Sync Check (2026-11-12 01:13:18) -- Day 15 of 30:**
  - Run 2 timeline: 15 days remaining until harvest on 2026-11-27.
  - Local data mirror: 668 soil moisture readings, 126 canopy GPR rows.
  - Notes: docs: document check_system.sh and sync_work.sh workflows in HANDOFF.md and MANUSCRIPT.md

- **Sync Check (2026-11-12 01:11:32) -- Day 15 of 30:**
  - Run 2 timeline: 15 days remaining until harvest on 2026-11-27.
  - Local data mirror: 668 soil moisture readings, 126 canopy GPR rows.
  - Notes: feat: add check_system.sh daily inspector and sync_work.sh workflow tools
