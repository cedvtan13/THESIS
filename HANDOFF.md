Picking up work in progress (handoff written 2026-10-16, 12:45). Context below — you have no prior history with this.

## Project
AgriSentry, an undergraduate thesis ("Computer Vision-Based Growth Monitoring and Yield Prediction for Pechay Under Differential Soil Moisture Treatments in a Greenhouse"). 9 pechay pots under 3 soil-moisture bands. Each day at noon, a top-down camera measures canopy Green Pixel Ratio (GPR). After harvest, OLS regression + LOOCV predict harvest weight.
- **Hardware:**
  - Raspberry Pi Zero 2 W (`crk@groupb.local`): camera, GPR, CSV logging.
  - Custom ESP32-S3-WROOM-1 PCB: soil sensors through a MUX, BMP388, 12 relays (9 solenoids, pump, Pi fans, capture light).
  - The two talk over UART (`/dev/ttyAMA0`, 115200).
- **People:** the adviser is **Engr. Alvin Joseph Macapagal**. Students: Cedric Vince Tan (the user), Kent Vincent Godinez, Rey Emmanuel Adag.
- **Grow-out schedule:**
  - Sown 2026-10-06 = **D1** (sowing day counts as D1). 30-day cycle, **harvest D30 = 2026-11-04**.
  - Automated data runs **D8–D30 = 207 rows**. D1–D7 were hardware commissioning, so no automated data exists for them.
- **Network:** the Pi runs offline and connects only to an iPhone hotspot ("Cvtan") for a few minutes a day; school Wi-Fi blocks SSH.
- **Power:** a UPS gives ~10.8 h on battery. Mains is unplugged every night, so the Pi usually dies around 07:00 and comes back when someone plugs it in.

## Where things stand
- **Running:**
  - `pi-link` systemd service: ESP32 logger, soil moisture every 30 min.
  - Cron runs `capture_gpr.py` at 12:00, retrying every 10 min until 12:50. A duplicate-day guard means only the first successful run writes.
- **`growth_dataset.csv`** has D8–D11 (36 rows). D11 (12:00 Oct 16) is the first day with the re-fitted ROIs.
- **Pump:** plugged back in (user confirmed, ~12:50 Oct 16), after being unplugged 10:35–12:50 for the probe work. At 12:29 every pot was above its band.
- **Firmware** (commit `1beedcf`, flashed 12:28 Oct 16):
  - Pot → MUX remap: `POD_MUX_CH = {8,7,6,5,4,3,2,1,0}`.
  - `ACTUATORS_ENABLED = true`, `PUMP_FLOW_ML_PER_S = 18.0`, treatment bands ON.
  - The ESP32 has its own 15-min irrigation check. It waters on a single below-band reading, then locks that pot out for 2 h.
- **Exposure:** brightness-matched on every capture. It starts at 6 ms and rescales until the frame's mean V ≈ 73. Gain 1.0 and white balance are locked. The capture light is used only if even 100 ms is >20% too dark (logged as `light_used` in `exposure_log.csv`).
- **Raw noon frames are kept from D12** as lossless PNGs in `~/agrisentry_data/frames/` (commit `9546229`). An 11:44 Oct 16 pre-noon reference frame is saved there too.
- **Code:** GitHub `cedvtan13/THESIS` `main` @ `9546229`, pushed, and synced to the Pi.
- **Progress-report slides (Canva):** https://www.canva.com/d/h0rLqS0UtsIH032. Still to fill: camera height and pot spacing (slide 15), and a Pi-enclosure photo (slide 10).

## What happened on 2026-10-16 (all in `field_log.csv` with times)
1. **P-02 soil moisture had read 100% since ≥ Oct 12.** Diagnosis found the real cause, which had nothing to do with P-02 itself.
2. **The soil probes were wired rotated 180°:** the probe in pot P-0n sat on MUX channel 10−n.
   - Proven by `tools/map_probes.py` (pull one probe at a time), a hand-over-pot camera frame, and a valve spray test (`tools/valve_sequence.py`).
   - Camera ROI labels, valves and the team's own pot numbers all agree with each other. Only the probes were rotated.
3. **Fix:**
   - Firmware remap, flashed 12:28.
   - `sm_pct` swapped P-0k ↔ P-0(10−k) in `growth_dataset.csv` (D8–D11) and `~/agrisentry_data/sm_log.csv` (rows before 12:28:30). P-05 is unchanged.
   - Backups: `*_before_probe_remap_20261016.csv` (Pi `~/agrisentry_data/` and `~/thesis/`).
   - `band_log`, `error_log` and `irrigation_log` entries before 12:28 were **not** rewritten (explained in `field_log`).
4. **The stuck-100% probe was in pot P-08** (raw ~1056, below the shared `wetADC` 1120, so clamped).
   - Spare probes were put into pot P-02 (~10:40) and pot P-08 (~10:45).
   - **P-08's `sm_pct` before Oct 16 is unreliable.**
   - All 9 probes were pulled and reinserted 11:00–11:25, so every pot's SM steps at that time.
5. **The 07:50 auto-dose** (20 mL into pot P-08) was triggered by P-02's probe under the old mapping. The 10:50 event was NOT delivered (pump unplugged); the row was added to `irrigation_log` by hand. The ESP32 irrigation count for P-08 is 2.
6. **ROIs re-fitted at 11:46** (commit `4b0ad2c`, user request).
   - The old circles (r = 70 px) sat ~45 px left of the pots and missed rim seedlings.
   - The D10 zeros for P-01 and P-06 were ROI misses, not dead plants.
   - New circles are centred on Hough-detected rims, r = 85 px, so the denominator goes 15373 → 22701 px. Applies from D11. D8–D10 can't be recomputed.
   - Old geometry: `Dual_Archi/pot_rois_before_20261016.json`. Pots were **not** moved; the user refuses to move hardware.
7. **P-06 read wet (raw ~1108) after the valve spray test**, probably water from its hose. Watch it.

## Next action
Daily routine:
1. Plug mains back in early. If the Pi is still off at 12:50, that day is lost.
2. Hotspot on, then: `cd ~/Desktop/THESIS && ./daily_checkin.sh`. It syncs the clock, shows status and backs up to `_pi_data/`.
3. After 12:00, `./system.sh status`: confirm 9 new rows, and that the new frame exists in `~/agrisentry_data/frames/`.

Pending with the user:
- **Tell the adviser** about the three methodology events: the SM probe mapping fixed for D8–D11, the ROIs re-fitted from D11, and probes replaced in P-02 and P-08.
- **Manuscript Appendix G** says the raw frame is discarded ("storage autonomy"). Frames are now kept from D12, so the text needs updating, or switch saving off if the adviser objects.
- **Harvest weights** must be recorded with the pot IDs (P-01…P-09). The team's numbering matches the system's.
- `DEPLOYMENT_NOTES.md` doesn't mention the new tools yet.

## Decisions already made
- **Brightness-matched exposure, not a fixed exposure.** Auto-exposure was rejected because it also moves colour.
- **Capture light OFF by default; on only when it's really dark.** A lit frame read +40–100% higher GPR.
- **ROI circles = pot soil openings (r = 85) from D11.** This replaces the older "ROIs locked" rule. Don't change them again without a reason, and log any change. The territory circles (r = 221 px, the `terr_*` columns) are unchanged.
- **Day numbering: sowing day = D1.**
- **The dataset starts at D8.** A user-supplied D1–D7 CSV looked generated and was **refused** as measured data. Real manual D1–D7 data may only go in as clearly labelled supplementary data.
- **Pot labels:** row by row, right to left: top row P-03 P-02 P-01, middle P-06 P-05 P-04, bottom P-09 P-08 P-07. Bands: P-01–03 = 30–40%, P-04–06 = 50–60%, P-07–09 = 70–80%.
- **One capture per day.** Re-capture only after a technical fault, and log it. Never re-capture because the numbers look low.
- **No physical changes to the rig** (the user's rule): fix alignment and mapping in software.
- **Sync Mac → Pi with `./sync_pi.sh push`.** Never `git pull` on the Pi.

## Gotchas — don't repeat these
- **SSH from Claude's Bash:**
  - It needs `dangerouslyDisableSandbox: true`.
  - `groupb.local` does **not** resolve from Claude's shell, even though it works in the user's terminal. On the hotspot the Pi is **`172.20.10.7`**, or IPv6 link-local `fe80::3ec2:74a:7085:10f9%en0` (scp form: `crk@[fe80::...%en0]`).
  - Always pass `-o HostKeyAlias=groupb.local`.
  - For the Mac scripts: `PI_HOST=172.20.10.7 ./sync_pi.sh push`. `flash_esp.sh` fails at host discovery, so build with `pio run`, scp the `.bin`s to `~/fw_main/`, and run `tools/flash_esp.py ~/fw_main` on the Pi under `nohup`.
- **The hotspot link drops every few minutes.** Run anything longer than ~10 s on the Pi under `nohup ... > ~/file.txt &` and read the file afterwards, or the job hangs when SSH dies.
- **The user acts fast.** For any "do X while I watch" test, say explicitly "wait for my READY". Twice the user did the action before the logger was running.
- **Serial-port tools (`raw_watch.py`, `map_probes.py`, `bench_check.py`, `actuator_test.py`) stop `pi-link` and swallow ESP32 event lines** while they run. An irrigation EVT during that window is not logged. Restart with `sudo -n systemctl restart pi-link`. Avoid running them across the ESP32's 15-min checks.
- **Pulling a probe into air reads ~0%**, which triggers a dose at the next 15-min check. Unplug the pump for probe work.
- **`pkill -f live_feed.py` over SSH kills your own session.** Use `pkill -f "python3 -u [l]ive_feed.py"`.
- **Only one program can use the camera at a time.** Never leave `live_feed.py` running near 12:00.
- **The Pi has no RTC.** After a total power loss it boots with a stale clock until the hotspot syncs it.
- **Quarantine and irrigation counts persist in ESP32 flash** across reflashes. Use `pi_link.py --reset-state` only for a new planting, or `--clear-faults` to clear a quarantine.
- **All 9 probes share one calibration** (`dryADC` 2483 / `wetADC` 1120). Probe-to-probe offsets of ~5–10% are normal. A spare probe in the same soil read ~150 counts higher than the old P-08 probe.

## Files
- `/Users/moapilaw/Desktop/THESIS/DEPLOYMENT_NOTES.md`: user-facing command cheat sheet.
- Mac scripts in `/Users/moapilaw/Desktop/THESIS/`: `system.sh`, `daily_checkin.sh`, `bench_test.sh`, `gpr_view.sh`, `live_feed.sh`, `flash_esp.sh`, `actuator_test.sh`, `flow_test.sh`, `sync_pi.sh`, `.pi_host.sh`.
- `Dual_Archi/capture_gpr.py`: noon capture. Exposure matching, frame saving (`FRAME_DIR`), HSV mask H 38–85, S ≥ 100, V ≥ 55, 3×3 opening.
- `Dual_Archi/pi_link.py`: `pi-link` daemon.
- `Dual_Archi/pot_rois.json`: 9 circles, r = 85, from D11. `pot_rois_before_20261016.json` is the old geometry.
- `Dual_Archi/Dual_Archi_Firmware/src/main.cpp`: ESP32 firmware. `POD_MUX_CH` remap, `ACTUATORS_ENABLED`.
- `Dual_Archi/tools/` (Pi-side), new on Oct 16:
  - `raw_watch.py`: raw ADC once a second.
  - `map_probes.py`: which channel moves when a probe is pulled.
  - `valve_sequence.py`: valves P-01→P-09 with the pump, for hose checks.
- On the Pi, `~/thesis` = `~/THESIS/Dual_Archi`: `growth_dataset.csv`, `exposure_log.csv`, `field_log.csv` (`date,day,pot_id,note`), `cron.log`, `pi_link.log`.
- `~/agrisentry_data/` on the Pi: `sm_log.csv`, `irrigation_log.csv`, `error_log.csv`, `band_log.csv`, `power_log.csv`, `frames/`, the remap backups, and `archive_*/` (old test data, never deleted).
- `/Users/moapilaw/Desktop/THESIS/_pi_data/`: Mac backup from `sync_pi.sh pull`. **Stale since Oct 15**; re-pull.

## Open questions
- Camera height above the pot rims and pot centre-to-centre spacing (cm): needed for the manuscript, not yet measured.
- The pilot was described as "13 days", but the archived pilot CSV has days 1–15 [unconfirmed].
