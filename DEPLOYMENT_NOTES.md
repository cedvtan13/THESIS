# AgriSentry: Deployment Notes & Command Cheat Sheet

_Last updated: 2026-10-11_

Run every command below **on your Mac, from the THESIS folder**, unless it says "on the Pi".

```bash
cd ~/Desktop/THESIS
```

---

## Tomorrow's deployment checklist

1. **Power up** the Pi and ESP32 board. Plug in the **soil moisture sensors** (and the BMP388 if it's ready).
2. **Health check:**
   ```bash
   ./bench_test.sh
   ```
   - `PING/PONG` should say **5/5**.
   - Every pot (P-01 to P-09) should **PASS**: raw ADC between about 1120 (wet) and 2483 (dry). If all nine read about 550 and show WARN, the sensors aren't connected.
   - The camera photo with the pot circles is saved to **Desktop → AgriSentry Bench Photos** and opens by itself. Check that every pot sits inside its cyan circle.
3. **Start the system:**
   ```bash
   ./system.sh start
   ```
   You should see `ESP32 link OK`, `pi-link service : active`, `12:00 GPR cron : ON`.
4. **Check it a minute later:**
   ```bash
   ./system.sh status
   ```
5. The first automatic GPR row is written at **12:00 noon**. Run `./system.sh status` after noon: `growth_dataset` should show **9 rows** for that day.

---

## Daily check-in (hotspot, a few minutes)

The Pi runs **offline** all day: logging, watering and the noon capture don't need the network. Once a day, turn on the hotspot so the Pi connects, then on the Mac (joined to the same hotspot):
```bash
./daily_checkin.sh
```
It waits for the Pi's clock to sync over the internet, shows the clock offset, shows the status, and backs up all data to `THESIS/_pi_data/`. Then you can turn the hotspot off again.

**Why the clock matters:** the Pi has **no battery clock**. If it reboots while offline (power blip), it restarts with the last hourly-saved time, so it can be behind until the next hotspot sync. That shifts the noon capture and the timestamps, and the day number too if it crosses midnight. `./system.sh status` shows `clock : NOT SYNCED since boot` when that happens, and the capture writes a WARNING in `cron.log`. **If you see it, connect the hotspot right away.**

Optional hardware fix: a **DS3231 RTC module** (cheap, I2C) keeps the time through reboots without internet.

---

## Clock buddy + power log (automatic)

The Pi and ESP32 keep each other's time while `pi-link` runs:
- **The Pi reboots without internet:** it asks the ESP32 for the time (the ESP32 didn't lose power) and sets its own clock. You'll see `Pi clock was not synced -- set from the ESP32` in `pi_link.log`.
- **The ESP32 restarts:** the Pi sends it the time immediately.
- **Both lose power:** neither knows the time until the hotspot sync, but the log still records **when** it happened.

Every unclean shutdown and every ESP32 restart is written to **`~/agrisentry_data/power_log.csv`**, also shown by `./system.sh status`:

| column | meaning |
|---|---|
| `down_since` | last heartbeat (written every minute) = when the Pi went down |
| `back_at`, `downtime_h` | when it came back, and for how long it was down |
| `esp_last_alive` | the ESP32's last saved time (every 10 min) before *it* went down |
| `note` | "Pi-only outage: the ESP32 kept running", "ESP32 restarted too (full power loss?)", or "ESP32 rebooted while the Pi stayed up" |

A normal `./system.sh stop` or reboot is **not** logged as an outage. This log is good evidence for the reliability deliverable (D7).

## UPS runtime test
```bash
./system.sh ups-test
```
(The Pi clock must be synced, i.e. hotspot on.) This starts **only** the logger (no noon capture) and records the start time. Unplug mains and leave it running. When power returns and the Pi boots, the power log gets a row whose note ends with **`UPS TEST: started …, last alive … -> lasted X.XX h`**. Check it with `./system.sh status` or `./daily_checkin.sh`.

---

## Everyday commands

| What you want | Command |
|---|---|
| Daily: sync clock + status + back up data | `./daily_checkin.sh` |
| Is everything running? Day number? Row counts? | `./system.sh status` |
| Start the system (logging + noon photo) | `./system.sh start` |
| Stop the system (testing mode) | `./system.sh stop` |
| Test sensors + camera, photo saved to Desktop → AgriSentry Bench Photos | `./bench_test.sh` |
| Same, but skip the photo | `./bench_test.sh --no-camera` |
| Same, plus click every relay | `./bench_test.sh --relays` |
| Test relays one at a time (interactive) | `./actuator_test.sh` |
| Measure each valve's flow rate | `./flow_test.sh` (see below) |
| Live camera view for arranging pots | `./live_feed.sh` (see below) |
| Build + flash the **system firmware** (`Dual_Archi_Firmware/src/main.cpp`) | `./flash_esp.sh` |
| Flash a different ESP32-S3 project instead (replaces the system firmware) | `./flash_esp.sh Test/TestBench` |
| Send code edits from the Mac to the Pi | `./sync_pi.sh push` |
| Copy the Pi's data (CSVs, logs) to the Mac | `./sync_pi.sh pull` (lands in `THESIS/_pi_data/`) |
| Archive all data and start empty CSVs | `./system.sh reset-data` (asks first) |
| Start a UPS runtime test (logger only) | `./system.sh ups-test` |
| Log into the Pi | `ssh crk@groupb.local` (or `ssh crk@<ip>`, see Troubleshooting) |

> `bench_test.sh` and `actuator_test.sh` **stop** the system so they can use the serial port.
> **Always run `./system.sh start` again afterwards** if you're deployed.

### On the Pi itself (after `ssh`)
```bash
~/thesis/tools/agrisentry.sh status     # same as ./system.sh on the Mac
~/thesis/tools/agrisentry.sh start
~/thesis/tools/agrisentry.sh stop
tail -f ~/thesis/pi_link.log            # live ESP32 messages (Ctrl+C to exit)
```

---

## What `./flash_esp.sh` flashes

- With no argument it builds and flashes **`Dual_Archi/Dual_Archi_Firmware/src/main.cpp`**, the real system firmware, using that folder's `platformio.ini`.
- The bench test and actuator test **don't need their own firmware**. They're Pi-side scripts that talk to that same system firmware.
- `./flash_esp.sh <folder>` flashes another PlatformIO project, for example `Test/TestBench`. It only accepts ESP32-S3 projects (the `nodemcu-32s` ones are for a different chip and are refused). Afterwards, run `./flash_esp.sh` to put the system firmware back.

---

## Day numbering

- Sowing date is **2026-10-06 = Day 1**. So Oct 12 = D7, Oct 13 = D8, and so on.
- It's stored in `Dual_Archi/sowing_date.txt` on the Pi. `./system.sh status` prints today's D.
- The cycle is **30 days: D1 to D30 (Oct 6 to Nov 4)**. **Harvest is D30 = Nov 4**, right after that day's noon capture. `capture_gpr.py` refuses to write outside D1–D30 (`CYCLE_DAYS = 30`).
- **Automated capture starts at D8 (Oct 13).** D1–D7 were hardware commissioning, so the dataset is D8–D30: **23 days × 9 pots = 207 rows**. `reliability_report.py` scores completeness against D8–D30.
- Any real manual data from Oct 6–12 uses the same numbering (Oct 6 = D1) and is kept **separate** from the training dataset, as supplementary data.

---

## Arranging the pots: live feed

```bash
./live_feed.sh              # 1 fps, opens http://<pi>:5000 in your browser
./live_feed.sh --fps 3       # smoother, but heavier on the Pi's power supply
./live_feed.sh --light      # capture light on while you align
```
Move each pot until its rim sits inside its green circle. **Ctrl+C** stops it. On the Pi directly: `cd ~/thesis && python3 live_feed.py`.

- Circles come from **`pot_rois.json`**, using the same math the GPR measurement uses.
- The camera uses the **exact same settings as the noon capture**: still mode, fixed focus, locked exposure and white balance (shared from `capture_gpr.open_locked_camera()`). What you line up is what gets measured.
- Only one program can use the camera at a time. **Stop the live feed before 12:00** and before running `./bench_test.sh`.

---

## Capture light (currently OFF)

The capture light is controlled by one setting at the top of `Dual_Archi/capture_gpr.py`:
```python
USE_CAPTURE_LIGHT = False   # True = light ON for every capture
```
- **Off since Oct 12.** Light + live camera rebooted the Pi once (suspected brownout), and noon daylight is enough. Captures run in daylight only.
- When it's `True`, every capture goes: light ON → 1.5 s → photo → light OFF. The light is sent as a self-expiring 20 s pulse.
- One-off override for a test, on the Pi: `python3 capture_gpr.py --no-write --no-sm --allow-any-day --light --debug-overlay /tmp/t.png`
- After changing it, run `./sync_pi.sh push`. **Pick one setting and keep it for the whole 35 days**, because switching mid-cycle changes the lighting in the GPR data.
- If you turn it on, check the exposure first (the 24 ms exposure was chosen without it): `cd ~/thesis && python3 cam_check.py --exposure-sweep`

---

## Actuators (ENABLED since Oct 12)

1. The switch is at the very top of `Dual_Archi/Dual_Archi_Firmware/src/main.cpp`, under **ACTUATOR MASTER SWITCH**. It's currently **`true`**: automatic watering, fans and the capture light are live. Set it to `false` and reflash to disable them all.
   ```cpp
   const bool ACTUATORS_ENABLED = true;
   ```
2. After changing it, flash:
   ```bash
   ./flash_esp.sh
   ```
   The boot lines should say `BOOT,actuators=ENABLED`.
3. Test each relay:
   ```bash
   ./actuator_test.sh
   ```
   | Type | Does |
   |---|---|
   | `3` | solenoid P-03 for 1 s |
   | `3 1500` | solenoid P-03 for 1.5 s |
   | `10` / `11` / `12` | pump / fans / light |
   | `w 4 2000` | real watering: P-04 valve opens, then the pump, for 2 s |
   | `m 1,2,10 3000` | **several at once**: P-01 + P-02 + pump together for 3 s (turned on 0.25 s apart, valves first; off in reverse, pump first) |
   | `all` | each relay in turn, press Enter between each |
   | `q` | quit |

   ⚠️ Don't run the pump (`10`) alone for long, because it pushes against closed valves. Use `w` instead.

   After **every** test the tool checks whether the ESP32 rebooted. If you see `!! ESP32 REBOOTED during the test`, the switching caused a power dip or spike (flyback diodes, supply current, grounding). That's a hardware problem, not code. Build up step by step: `m 1,10`, then `m 1,2,10`, then `m 1,2,3,10`, and so on.
4. Run `./system.sh start` again afterwards.

While `ACTUATORS_ENABLED = false`, relay commands answer `ACTUATORS_DISABLED` and nothing switches. Irrigation decisions still show up as `LOG,ACTUATORS_OFF,...` lines, so you can check the logic.

---

## Flow rate test

The firmware converts each watering dose (mL) into pump time using **`PUMP_FLOW_ML_PER_S`** (currently **18.0**, measured Oct 12: 90 mL in 5 s on all 9 valves) in `main.cpp`. If that number is wrong, every dose is wrong.

```bash
./flow_test.sh                          # all 9 valves, 5 s each
./flow_test.sh --pots 1,4,7 --runs 3    # chosen valves, 3 runs each (better average)
./flow_test.sh --seconds 10             # longer runs (max 15 s)
```
For each valve: put a measuring cup under the emitter → press Enter → valve opens, pump runs 5 s, then both stop → type the **mL collected** (`r` = redo, Enter = skip).

At the end it shows mL/s per valve, the average, how much the valves differ, and whether `PUMP_FLOW_ML_PER_S` needs changing. Results are saved on the Pi in `~/thesis/flow_calibration.csv` (copy them with `./sync_pi.sh pull`). To change the value: edit `main.cpp`, then run `./flash_esp.sh`.

Quick one-off without the script: `./actuator_test.sh`, then `w 1 5000` (valve P-01 + pump, 5 s).

---

## Where the data lives (on the Pi)

| File | What's in it | Written by |
|---|---|---|
| `~/thesis/growth_dataset.csv` | **Main dataset**: one row per pot per day (GPR + SM) | `capture_gpr.py`, noon cron |
| `~/agrisentry_data/sm_log.csv` | Soil moisture every 30 min | `pi-link` service |
| `~/agrisentry_data/irrigation_log.csv` | Every watering event | `pi-link` service |
| `~/agrisentry_data/error_log.csv` | Sensor faults, quarantines, etc. | `pi-link` service |
| `~/thesis/pi_link.log` | Raw ESP32 messages | `pi-link` service |
| `~/thesis/cron.log` | Output of each noon capture | cron |
| `~/agrisentry_data/archive_*/` | Old data, archived (never deleted) | `reset-data` |

`~/thesis` is a shortcut to `~/THESIS/Dual_Archi`.

**Back up the data regularly:**
```bash
./sync_pi.sh pull
```

---

## Bench photos when running on the Pi

`./bench_test.sh` works from **either** machine, and the photo always ends up on the **Mac** in Desktop → AgriSentry Bench Photos.

- **From the Mac:** works out of the box.
- **On the Pi** (after you `ssh` in): the Pi sends the photo back to the Mac you connected from. This needs a **one-time setup** on the Mac so it trusts the Pi's key:
  ```bash
  ssh -o HostKeyAlias=groupb.local crk@192.168.1.16 'cat ~/.ssh/id_ed25519.pub' >> ~/.ssh/authorized_keys
  ```
  Use the Pi's current IP; `arp -a | grep groupb` shows it. Remote Login is already on for this Mac. Afterwards the Pi can log into the Mac as you. To undo that, delete the line ending in `thesis-mac` from `~/.ssh/authorized_keys` on the Mac.
- If the Pi can't reach the Mac, the photo stays on the Pi at `/tmp/agrisentry_bench/bench_overlay.png`.

---

## Troubleshooting

**"Pi not found" / `groupb.local` doesn't work.** This happens on home Wi-Fi. The scripts look up the IP by themselves. If that fails, find the IP and pass it in:
```bash
arp -a | grep groupb
```
```bash
PI_HOST=192.168.1.16 ./system.sh status
```

**`./system.sh status` shows no `ACK,TIME`, or the ESP32 doesn't answer.** Run `./bench_test.sh --no-camera`. If PING fails, reflash with `./flash_esp.sh`, then `./system.sh start`.

**A pot's SM reads `NaN`.** The pot was quarantined after 3 out-of-range readings in a row (raw below 150 or above 4000, e.g. while a probe was unplugged). Quarantine is **saved in the ESP32's flash** and survives reboots and reflashing. `./bench_test.sh` marks those pots WARN with "QUARANTINED". Fix the probe, then clear it (on the Pi, with the system stopped):
```bash
python3 ~/thesis/pi_link.py --clear-faults
```

**Starting a new planting:** wipe what the ESP32 keeps in flash (irrigation counts, last-watered times, quarantines, germination mode back to ON). On the Pi, with the system stopped:
```bash
python3 ~/thesis/pi_link.py --reset-state
```
Done for the Oct 6 planting on Oct 12.

**Noon capture didn't write a row.** Check `tail ~/thesis/cron.log` on the Pi. It refuses to write the same day twice, and it refuses days outside D1–D35.

**Don't run `git pull` on the Pi.** Code reaches the Pi through `./sync_pi.sh push` (all the scripts do this for you). GitHub is just a backup of the Mac's copy.

---

## What was done (Oct 10–12)

- **SSH key login** from the Mac to the Pi, so no more passwords.
- **Old board:** found GPIO2 (MUX S0) interfering with the ESP32's UART TX, which caused the `0x00` garbage in the logs. **The new PCB doesn't have this problem**: PING/PONG works 10/10.
- **New PCB verified:** EN = BCM 23 (physical pin 16), BOOT = BCM 24 (physical pin 18), UART TX/RX, LED on GPIO21.
- **Firmware:**
  - actuator master switch moved to the top of `main.cpp` (currently **false**)
  - new commands: `GET_RAW` (raw sensor ADC), `INFO` (firmware state), `TEST_RELAY,<idx>,<ms>`
  - relay commands now refuse clearly when actuators are disabled
- **New scripts:** `bench_test.sh`, `flash_esp.sh`, `system.sh`, `actuator_test.sh`, `sync_pi.sh` on the Mac, plus helpers in `Dual_Archi/tools/` on the Pi.
- **Data reset for the new planting:** all CSVs are empty (headers only). The old data is archived in `~/agrisentry_data/archive_20261011_*`. Sowing date is set to 2026-10-06.
- **Cleanup:** unused files moved to `THESIS/_archive/2026-10-11/` on both machines, nothing deleted.
- **System is currently STOPPED** (testing mode). Run `./system.sh start` to deploy.
- **Oct 12:**
  - Actuators **enabled** (flyback diodes fixed).
  - New tests: `m` (several relays at once, with reboot detection) in the actuator tester, and `./flow_test.sh`.
  - Pump flow set to the measured **18 mL/s**.
  - Capture light wired into every photo, then switched OFF (`USE_CAPTURE_LIGHT = False`) after a suspected brownout. Daylight only for now.
  - Wiped the old irrigation counts and quarantines left in the ESP32's flash (`--reset-state`).
  - `./live_feed.sh` runs at 3 fps with the same camera settings as the real capture.
