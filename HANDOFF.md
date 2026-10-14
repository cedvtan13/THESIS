Picking up work in progress (handoff written 2026-10-14, 13:00). Context below — you have no prior history with this.

## Project
AgriSentry, an undergraduate thesis ("Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse"). 9 pechay pots under 3 soil-moisture bands. Each day at noon, a top-down camera measures canopy Green Pixel Ratio (GPR). After harvest, OLS regression + LOOCV predict harvest weight.
- **Hardware:**
  - Raspberry Pi Zero 2 W (`crk@groupb.local`): camera, GPR, CSV logging.
  - Custom ESP32-S3-WROOM-1 PCB: soil sensors through a MUX, BMP388, 12 relays (9 solenoids, pump, Pi fans, capture light).
  - The two talk over UART (`/dev/ttyAMA0`, 115200).
- **People:** the adviser is **Engr. Alvin Joseph Macapagal**. Students: Cedric Vince Tan (the user), Kent Vincent Godinez, Rey Emmanuel Adag.
- **Grow-out schedule:**
  - Sown 2026-10-06 = **D1** (sowing day counts as D1). 30-day cycle, **harvest D30 = 2026-11-04**. Checking: 1st week of November.
  - Automated data runs **D8–D30 = 207 rows**. D1–D7 were hardware commissioning, so no automated data exists for them.
- **Network:** the Pi runs offline. It connects only to an iPhone hotspot ("Cvtan") for a few minutes a day; school Wi-Fi blocks SSH.
- **Power:** a UPS gives ~10.8 h on battery. Mains is unplugged every night (the lab closes), so the Pi usually dies around 07:00 and comes back when someone plugs it in. A permanent outdoor outlet is planned.

## Where things stand
- **Deployed and running since 2026-10-13 11:56:**
  - `pi-link` systemd service: ESP32 logger, soil moisture every 30 min.
  - Cron runs `capture_gpr.py` at 12:00, with retries every 10 min until 12:50. A duplicate-day guard means only the first successful run writes.
- **`growth_dataset.csv`** has D8 + D9 (18 rows), all with soil moisture.
  - D9 was replaced twice, both documented in `field_log.csv` and `cron.log`, with backups in `~/agrisentry_data/`. The rows kept are from 12:50, taken after the leaning seedlings were firmed with soil.
- **Firmware:** `ACTUATORS_ENABLED = true`, `PUMP_FLOW_ML_PER_S = 18.0` (measured 90 mL / 5 s on all valves), treatment bands ON.
  - Every pot is currently above its band (soil still wet), so no automatic irrigation has happened yet (`irrigation_log.csv` is empty).
- **Exposure:** brightness-matched on every capture. It starts at 6 ms and rescales until the frame's mean V ≈ 73, the reference Oct 13 noon frame. Gain 1.0 and white balance are locked.
  - The capture light is used only if even 100 ms is >20% too dark. Light days get `light_used = 1` in `exposure_log.csv`.
- **Progress report (Oct 13)** is in Canva: https://www.canva.com/d/h0rLqS0UtsIH032 (17 slides, saved). The original Oct 5 deck was left untouched. Still to fill on the slides: camera height and pot spacing `[ __ cm ]` (slide 15), and a Pi-enclosure photo or render (slide 10).
- **Code:** all in GitHub `cedvtan13/THESIS` (`main`, last commit `4ed2fcc`) and synced to the Pi.

## Next action
Nothing urgent. The system runs on its own. Each day:
1. Plug mains back in early. If the Pi is still off at 12:50, that day is lost.
2. Hotspot on, then on the Mac: `cd ~/Desktop/THESIS && ./daily_checkin.sh`. It syncs the Pi clock, shows status, and backs up data to `_pi_data/`.
3. After 12:00, `./system.sh status`: confirm 9 new rows for the day.

The user may send **real** manual D1–D7 measurements. Add them only as clearly labelled supplementary data, never into the training rows.

## Decisions already made
- **Brightness-matched exposure, not a fixed exposure.** 24 ms washed seedlings out on a sunny noon (57 vs ~1,500 px detected). 6 ms was far too dark on a cloudy noon (mean V 13 vs 73). Auto-exposure was rejected because it would also move colour; only brightness is matched, with gain and white balance locked.
- **Capture light OFF by default; on only when it's really dark.** A lit test frame read +40–100% higher GPR (more saturated green), and daylight still dominates the scene. Switching mid-cycle would create a fake growth jump.
- **Outer "territory" circles left as they are** (radius 221 px), even though they overlap neighbours. The user declined a non-overlapping radius. Only the `terr_*` columns are affected; `raw_gpr` is the main metric.
- **Day numbering: sowing day = D1** (`capture_gpr.day_index`). The user's notes had used "day 0 = Oct 6" before agreeing to this.
- **The dataset starts at D8.** A user-supplied D1–D7 CSV looked generated (its D7 values equalled a live reading taken at 19:30; it used an old `total_px` of 14073). It was **refused** as measured data. The honest panel wording is: commissioning on D1–D7, dataset D8–D30 = 207 rows, planned 270.
- **Pot labels go row by row, right to left:** top row P-03 P-02 P-01, middle P-06 P-05 P-04, bottom P-09 P-08 P-07. Bands by row: P-01–03 = 30–40%, P-04–06 = 50–60%, P-07–09 = 70–80%. Sensors and valves were already wired that way; only the camera labels were fixed. **Don't change `pot_rois.json` geometry**; the ROIs are locked.
- **One capture per day.** Re-capture only after a technical or measurement fault, and log it. Never re-capture because the numbers look low (that's cherry-picking).
- **Sync Mac → Pi with `./sync_pi.sh push`** (rsync, code only, never CSVs, logs or images). Never `git pull` on the Pi.

## Gotchas — don't repeat these
- **SSH from Claude's Bash needs `dangerouslyDisableSandbox: true`**, because the sandbox blocks the LAN. On home Wi-Fi `groupb.local` may not resolve: use `arp -a | grep groupb` and `ssh -o HostKeyAlias=groupb.local crk@<ip>`. In zsh, `$SSH` from `.pi_host.sh` doesn't word-split, so wrap commands in `bash -c '...'`.
- **`pkill -f live_feed.py` over SSH kills your own SSH session**, because the pattern is in the command line. Use `pkill -f "python3 -u [l]ive_feed.py"`.
- **`pi-link` holds `/dev/ttyAMA0` exclusively.** Bench, actuator and flow tests stop it, so run `./system.sh start` afterwards. `agrisentry.sh start` does **not** restart an already-running service; use `sudo -n systemctl restart pi-link` after changing `pi_link.py`.
- **Only one program can use the camera at a time.** Never leave `live_feed.py` running near 12:00.
- **The Pi rebooted repeatedly** (sudden 5V cuts, `throttled=0x0`) while the UPS recharged from empty, under live-feed load. A 20 s light pulse plus a capture passed on Oct 14. Keep the live feed at 1 fps.
- **The Pi has no RTC.** After a total power loss it boots with a stale clock until the hotspot syncs it. `pi_link` borrows time from the ESP32 if the ESP32 stayed up. `power_log.csv` records every unplanned shutdown.
- **NetworkManager used to give up after 4 failed Wi-Fi attempts.** That's fixed (`autoconnect-retries 0` plus a Wi-Fi watchdog timer, installed by `tools/install_stability.sh`).
- **Quarantine and irrigation counts persist in ESP32 flash** across reflashes. Use `python3 ~/thesis/pi_link.py --reset-state` only for a new planting, or `--clear-faults` to clear a quarantine.
- **The capture light browned out the Pi once** with a continuous live feed. That's the source of the caution above.
- **Canva tool quirks:** `copy-design` with `page_numbers` errors ("design not found"); `recolor_element` on the status-card graphics recolours the whole card.

## Files
- `/Users/moapilaw/Desktop/THESIS/DEPLOYMENT_NOTES.md` — **user-facing command cheat sheet** (current). Read this first.
- `/Users/moapilaw/Desktop/THESIS/*.sh`, run on the Mac, all current:
  - `system.sh start|stop|status|reset-data|ups-test`
  - `daily_checkin.sh`
  - `bench_test.sh` (sensors and camera; photo goes to the Desktop)
  - `gpr_view.sh` (visual of what GPR counts)
  - `live_feed.sh` (1 fps alignment stream)
  - `flash_esp.sh` (builds and flashes `Dual_Archi/Dual_Archi_Firmware/src/main.cpp`)
  - `actuator_test.sh`, `flow_test.sh`, `sync_pi.sh push|pull`
  - `.pi_host.sh` (finds the Pi)
- `Dual_Archi/capture_gpr.py` — noon capture. Exposure matching, `USE_CAPTURE_LIGHT = False`, `AUTO_LIGHT_WHEN_DARK`, `CYCLE_DAYS = 30`. ROI and HSV mask: H 38–85, S ≥ 100, V ≥ 55, 3×3 opening.
- `Dual_Archi/pi_link.py` — `pi-link` daemon. CSV routing, ESP32↔Pi clock backup, heartbeat and power log.
- `Dual_Archi/pot_rois.json` — 9 circular ROIs, 140 px, 1296×1296 frame. **Locked.**
- `Dual_Archi/Dual_Archi_Firmware/src/main.cpp` — ESP32 firmware. `ACTUATORS_ENABLED` switch at the top.
- `Dual_Archi/tools/` — Pi-side helpers: `agrisentry.sh`, `bench_check.py`, `esp_link.py`, `flash_esp.py`, `gpr_view.py`, `actuator_test.py`, `flow_test.py`, `wifi_watchdog.sh`, `install_stability.sh`, `init_csvs.py`.
- On the Pi, `~/thesis` = `~/THESIS/Dual_Archi`:
  - `growth_dataset.csv` — main dataset.
  - `exposure_log.csv`, `field_log.csv` (`date,day,pot_id,note`), `cron.log`, `pi_link.log`, `sowing_date.txt` (2026-10-06).
- `~/agrisentry_data/` on the Pi:
  - `sm_log.csv`, `irrigation_log.csv`, `error_log.csv` (real faults only), `band_log.csv` (routine "above band" notices), `power_log.csv`, `wifi_watchdog.log`.
  - `archive_*/` — old and test data. Never deleted.
- `/Users/moapilaw/Desktop/THESIS/_pi_data/` — Mac backup copy from `sync_pi.sh pull`. Can be stale; re-pull.
- `/Users/moapilaw/Desktop/THESIS/_archive/2026-10-11/` — files archived during cleanup (old datasets, Gemini notes). Stale.

## Open questions
- Camera height above the pot rims and pot centre-to-centre spacing (cm): needed for the manuscript, not yet measured.
- Whether all the leaning seedlings were firmed **before** the 12:50 D9 re-capture [unconfirmed]. All pots rose 20–100% between 12:35 and 12:50, which would be explained if they were.
- The pilot was described as "13 days", but the archived pilot CSV has days 1–15 [unconfirmed].
