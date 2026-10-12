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

## Everyday commands

| What you want | Command |
|---|---|
| Is everything running? Day number? Row counts? | `./system.sh status` |
| Start the system (logging + noon photo) | `./system.sh start` |
| Stop the system (testing mode) | `./system.sh stop` |
| Test sensors + camera, photo saved to Desktop → AgriSentry Bench Photos | `./bench_test.sh` |
| Same, but skip the photo | `./bench_test.sh --no-camera` |
| Same, plus click every relay | `./bench_test.sh --relays` |
| Test relays one at a time (interactive) | `./actuator_test.sh` |
| Build + flash the **system firmware** (`Dual_Archi_Firmware/src/main.cpp`) | `./flash_esp.sh` |
| Flash a different ESP32-S3 project instead (replaces the system firmware) | `./flash_esp.sh Test/TestBench` |
| Send code edits from the Mac to the Pi | `./sync_pi.sh push` |
| Copy the Pi's data (CSVs, logs) to the Mac | `./sync_pi.sh pull` (lands in `THESIS/_pi_data/`) |
| Archive all data and start empty CSVs | `./system.sh reset-data` (asks first) |
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
- The 35-day cycle runs **D1 to D35** (Oct 6 to Nov 9). `capture_gpr.py` refuses to write outside that range.
- Manual data from Oct 6–12 uses the same numbering (Oct 6 = D1). Send it over and it'll be merged into `growth_dataset.csv`.

---

## Capture light

Every capture (the noon cron job **and** `./bench_test.sh`) now does: **light ON → wait 1.5 s → photo → light OFF**. The light is sent as a 20 s pulse, so the ESP32 switches it off by itself even if the script crashes. If the light fails to turn on, `cron.log` says `WARNING: capture light did NOT switch on`.

⚠️ The camera exposure (24 ms, gain 1.0) was set **without** the light. Before D1 data matters, check the photos aren't overexposed. On the Pi:
```bash
cd ~/thesis && python3 cam_check.py --exposure-sweep
```
Then set the exposure you pick in `capture_gpr.py` (`ExposureTime`) and push with `./sync_pi.sh push`.

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

## What was done (Oct 10–11)

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
