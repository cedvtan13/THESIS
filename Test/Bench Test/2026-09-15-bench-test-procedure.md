# Bench Test Procedure — Pi ↔ ESP32 ↔ Sensors ↔ Relays

Group B thesis rig · NodeMCU-32S + Raspberry Pi · 15 September 2026

**The rule for the whole document: build it up in stages and prove each stage before adding the next.**
Everything connected at once means a failure has ten possible causes. One at a time means it has one.

---

# PHASE 0 — Before you plug anything in

## 0.1 What you need on the bench

| Item | Note |
|---|---|
| NodeMCU-32S | the classic ESP32, not the S3 |
| Micro-USB cable | **must be a data cable.** A charge-only cable shows no COM port — a very common hour-waster |
| Laptop with VS Code + PlatformIO | already installed |
| CD74HC4067 mux + 9 capacitive sensors | not connected yet |
| 10-ch relay board (8 + 2) | not connected yet |
| Raspberry Pi, powered, on the same network | not connected yet |
| 3 × female-female jumpers | for the Pi link, later |

Nothing but the USB cable goes in during Phase 1.

## 0.2 Confirm Windows sees the board

Plug the ESP32 into USB. Open **Device Manager** → **Ports (COM & LPT)**.

You should see one of:

- `Silicon Labs CP210x USB to UART Bridge (COM#)` — most NodeMCU-32S boards
- `USB-SERIAL CH340 (COM#)` — cheaper clones

**Nothing appears, or a yellow `!` under Other devices?** The driver is missing:

- CP210x → search "Silicon Labs CP210x VCP driver", install, replug
- CH340 → search "CH340 driver windows", install, replug

**Still nothing after the driver?** Swap the USB cable before anything else. Roughly half of "dead board" reports are a charge-only cable.

Write down the COM number. You won't usually need it — PlatformIO auto-detects — but it's the first thing to check if upload fails.

## 0.3 Confirm PlatformIO sees it

VS Code → **Terminal → New Terminal**:

```powershell
pio device list
```

Expect something like:

```
COM5
----
Hardware ID: USB VID:PID=10C4:EA60 SER=0001 LOCATION=1-2
Description: Silicon Labs CP210x USB to UART Bridge (COM5)
```

If `pio` isn't recognised, use **PlatformIO Core CLI** from the PIO Home sidebar instead of the plain terminal — it sets up the path.

## 0.4 Open the project

**File → Open Folder →** `THESIS\Test\Bench Test`

Not `THESIS`, not `Test` — the folder that has `platformio.ini` directly inside it. That file is the *only* thing that makes a folder a PlatformIO project, which is why "Pick a folder" rejected the bare `.ino` earlier.

Within a few seconds the blue status bar at the bottom shows ✓ (build), → (upload) and 🔌 (monitor). On first open PlatformIO downloads the ESP32 toolchain — a few minutes, once.

## 0.5 Read one line before flashing

Open `src\main.cpp`, find:

```cpp
int RELAY_PINS[10] = {2, 32, 33, 25, 26, 27, 14, 13, 15, 23};
```

Index 0 is the pump, 1–9 are solenoids P-01…P-09. This is copied from `Dual_Archi_Firmware/src/main.cpp`, **but your physical wiring is the authority.** Phase 4 is what verifies it. If they disagree, the rig waters the wrong pot and the CSV records it as correct — silent, unrecoverable contamination of the treatment groups.

---

# PHASE 1 — Flash the ESP32, USB only

**Connected: USB only.** No relay board, no mux, no Pi, no 12 V.

> **Why the relay board must be off for this.** GPIO2 is your pump relay *and* an ESP32 strapping pin. During upload, esptool pulls GPIO0 low to enter download mode, and in that state GPIO2 must also read low. A relay board's opto-isolator input pulls GPIO2 toward its supply rail. That can defeat auto-upload and give you a `Failed to connect` that looks like a broken board. Flash bare, add hardware after.

## 1.1 Build

Click ✓, or:

```powershell
pio run -e nodemcu-32s
```

Expect `SUCCESS` and a RAM/Flash summary. Build errors are mine — paste them and I'll fix.

## 1.2 Upload

Click →, or:

```powershell
pio run -e nodemcu-32s -t upload
```

Watch for:

```
Connecting........
Chip is ESP32-D0WD-V3 (revision v3.1)
Writing at 0x00010000... (100 %)
Hash of data verified.
Leaving... Hard resetting via RTS pin...
```

### If it hangs on `Connecting........_____`

1. **Hold the BOOT button** while it says `Connecting`, release when `Chip is ESP32...` appears. Many clones lack the auto-reset transistor.
2. **Lower the speed.** In `platformio.ini`, change `upload_speed = 921600` to `460800`, then `115200`. Some CH340 clones won't do 921600.
3. **Close the serial monitor.** Only one program can hold a COM port. `pio device monitor` still running is the usual culprit.

## 1.3 Talk to it over USB — the most valuable step here

```powershell
pio device monitor -e nodemcu-32s
```

Press the **EN/RST** button. You should see:

```
BOOT,bench_test,relays=10,pods=9
commands: PING | SM | SM_RAW | UNIFORM[,n] | STATUS |
          RELAY,<0-9>,<0|1> | PULSE,<1-9>,<ms> | ALLOFF
relay 0 = pump, 1..9 = solenoid P-01..P-09
```

Now type `PING` and press Enter. Reply: `PONG`.

Then `STATUS`. Reply: `STAT,0,0,0,0,0,0,0,0,0,0,uptime=<n>` — ten zeros, every relay off.

**This splits your debugging in half.** `PONG` over USB proves the firmware runs, the protocol parses, and the board is good. Any failure after this point is wiring, not code.

Exit the monitor with **Ctrl+C**. Leave it closed — it holds the COM port.

### ✅ Phase 1 passes when: `PONG` and ten zeros over USB.

---

# PHASE 2 — Add the sensors

**Power off the ESP32 first.** Unplug USB. Never rewire a live board.

## 2.1 Mux wiring

| CD74HC4067 | ESP32 |
|---|---|
| SIG | GPIO34 |
| S0 | GPIO18 |
| S1 | GPIO19 |
| S2 | GPIO4 |
| S3 | GPIO5 |
| EN | GND |
| VCC | 3.3 V |
| GND | GND |

Sensors → mux channels C0…C8, in pot order: **C0 = P-01 … C8 = P-09.**

## 2.2 Sensor power — read this one

**Capacitive soil moisture sensors go on 3.3 V, not 5 V.** On 5 V their analog output can exceed 3.3 V and you slowly damage the ESP32's ADC. All nine share one rail; a sagging supply shifts every reading at once and looks exactly like real soil drying.

GPIO34 is input-only and has no internal pull-up. That's correct for an ADC input, and it's why the mux SIG line lives there.

## 2.3 Test

Plug USB back in, open the monitor, type:

```
SM_RAW
```

Expect nine numbers, roughly 1100–2600 in air-to-wet range:

```
SMRAW,2540,2551,2498,2560,2533,2547,2512,2549,2538
```

Then `SM` for percent of container capacity.

**Read the results:**

| Symptom | Meaning |
|---|---|
| A channel reads `0` or `4095` | that sensor or its mux channel is disconnected |
| All nine identical to the digit | SIG is reading one sensor — check S0–S3 wiring |
| Wild jumping | floating input, or no common ground |
| `NaN` in `SM` | outside the 150–4000 fault window; check `SM_RAW` for the raw value |

Sanity check: hold one probe in air, note the value, dip it in a glass of water (**to the line only — not past it**), note it again. It should drop by several hundred counts. Do this for each sensor to confirm the channel order matches the pot order.

### ✅ Phase 2 passes when: nine distinct plausible values, each responding to water.

---

# PHASE 3 — Add the relay board, DRY

**Power off. 12 V supply disconnected. No water in any line.**

## 3.1 Relay board power — the mistake everyone makes

The SONGLE SRD-05VDC-SL-C coils need **5 V**. The ESP32 outputs 3.3 V logic.

1. **Remove the JD-VCC/VCC jumper.**
2. `JD-VCC` ← **5 V** (coil supply)
3. `VCC` ← **3.3 V** (opto-isolator logic supply)
4. `GND` ← ESP32 GND

Skip this and the relays either don't pull in at all, or click weakly and chatter. That's the single most common cause of a channel "failing" the sweep.

Flyback diode (1N4007) across the pump and across each solenoid, **banded end to +12 V**. These are inductive loads; without diodes the switch-off spike degrades the relay contacts and can reset the ESP32.

## 3.2 Boot check — do this before anything else

Plug in USB. Does the `BOOT,bench_test,...` banner still appear?

GPIO2 (pump) and GPIO15 (P-08) are both strapping pins and now have a relay board hanging off them. **If the board no longer boots, that is why** — tell me and we'll move the pump to a free GPIO.

Also: no relay should click at power-up. The firmware latches OFF *before* `pinMode()` specifically to prevent that. A click at boot means something is wired to a pin the sketch doesn't control.

## 3.3 Sweep from USB

You can do the whole dry sweep from the serial monitor before the Pi is involved:

```
RELAY,1,1
RELAY,1,0
RELAY,2,1
RELAY,2,0
```

…through index 9. For each: **listen for a click, watch the board LED, and confirm the valve that responds is the one you expect.** Write down what actually moves.

The pump (index 0) is interlocked — it refuses to run with every valve closed. To test it:

```
RELAY,1,1
RELAY,0,1
RELAY,0,0
RELAY,1,0
```

Panic button at any time: `ALLOFF`.

### ✅ Phase 3 passes when: all ten click, and the index matches the physical valve.

If index and valve disagree, don't rewire — **tell me the actual mapping** and I'll correct `RELAY_PINS[]`. Rewiring to match wrong software is how you end up with a rig nobody can service.

---

# PHASE 4 — Connect the Raspberry Pi

**Power off the ESP32. Power off the Pi.**

## 4.1 Three wires

| ESP32 | | Pi (physical pin) |
|---|---|---|
| GPIO17 (TX2) | → | pin 10 (RXD / GPIO15) |
| GPIO16 (RX2) | ← | pin 8 (TXD / GPIO14) |
| GND | ↔ | pin 6 (GND) |

**TX goes to RX.** Both are 3.3 V logic — no level shifter, and do not put one in.

**The ground wire is not optional.** Without it the link half-works: mostly fine, occasional corrupted bytes, and it presents as a software bug you'll chase for hours.

## 4.2 Pi prep

SSH in:

```bash
ssh ced@groupb.local
```

### Is the UART actually a UART?

```bash
ls -l /dev/ttyAMA0 /dev/serial0
```

`/dev/ttyAMA0` is the real PL011 hardware UART. `/dev/ttyS0` is the miniUART, whose baud rate drifts with CPU frequency and corrupts bytes under load. Fine for a bench ping, **not** fine for 35 days of data.

If `ttyAMA0` is missing:

```bash
sudo nano /boot/firmware/config.txt
# add:  dtoverlay=disable-bt
sudo reboot
```

### Is the login console fighting you for the port?

```bash
sudo raspi-config nonint do_serial_cons 1
```

That disables the serial *console* while leaving the serial *hardware* enabled. If it's on, the Pi prints login prompts at your ESP32 and eats its replies.

### Permissions

```bash
groups            # look for 'dialout'
sudo usermod -aG dialout $USER   # if missing, then log out and back in
```

### pyserial

```bash
python3 -c "import serial; print(serial.__version__)"
sudo apt install python3-serial    # if that failed
```

## 4.3 Copy the driver over

From your laptop, in `THESIS\Test\Bench Test`:

```powershell
scp pi_bench.py ced@groupb.local:~/thesis/
```

## 4.4 Free the port

```bash
sudo systemctl stop pi-link
```

`pi-link` opens `/dev/ttyAMA0` exclusively; `pi_bench.py` will refuse to start while it holds it (and will tell you so).

> ⚠️ **Restart it when you finish.** `pi-link` is the ESP32's clock source — the production firmware waits for a `TIME` sync from the Pi. Leaving it stopped means the controller has no idea what time it is.

## 4.5 PING

```bash
cd ~/thesis
python3 pi_bench.py --ping
```

Expected:

```
[pi_bench] /dev/ttyAMA0 @ 115200
PING x5
  1: PONG in 12.4 ms
  2: PONG in 11.8 ms
  3: PONG in 12.1 ms
  4: PONG in 11.9 ms
  5: PONG in 12.3 ms

LINK OK — 5/5 replied, mean 12.1 ms
```

**5/5 or it hasn't passed.** 4/5 is a marginal link, and a marginal link means dropped irrigation commands at 2 a.m. with nobody watching. The script flags this itself.

If 0/5, it prints a numbered checklist. Work it in order — #2 (TX/RX swapped) and #3 (no common ground) are the answer the large majority of the time.

### ✅ Phase 4 passes when: 5/5 PONG.

---

# PHASE 5 — Full test sequence from the Pi

Only now, with the link proven:

```bash
python3 pi_bench.py --sm          # nine values, sanity check
python3 pi_bench.py --sm-raw      # raw ADC behind them
python3 pi_bench.py --uniform     # ALL NINE PROBES IN ONE BUCKET
python3 pi_bench.py --sweep       # dry relay walk, interactive
```

## About `--uniform`

Put all nine probes in the **same** bucket of wet soil, same depth, and **wait 60 seconds** before running it. This is the test that decides whether your nine pots are on a common scale:

| Spread | Verdict |
|---|---|
| < 2 % | ✅ one shared `dryADC`/`wetADC` pair is defensible |
| 2–5 % | ⚠️ borderline — per-sensor constants safer |
| > 5 % | ❌ the nine pots are **not** on a common scale |

All nine currently share `dryADC = 2553` / `wetADC = 1130`. If the spread is over 5 %, part of the treatment separation you report is sensor spread, not soil moisture — and that's a panel question you do not want asked cold.

## Wet test, last

12 V connected, water connected, **one pot at a time**, bucket under the emitter:

```bash
python3 pi_bench.py --pulse 1 2000
```

Valve opens → 250 ms → pump runs 2 s → pump stops → 250 ms → valve closes. Catch the output in a measuring cylinder; that gives you `PUMP_FLOW_ML_PER_S`, which is currently the **unverified estimate of 20.0 mL/s** in your firmware.

## When you're done

```bash
sudo systemctl start pi-link
```

---

# Quick reference

| Symptom | First thing to check |
|---|---|
| No COM port | USB cable is charge-only; then driver |
| `Failed to connect` on upload | hold BOOT; then drop `upload_speed`; then close the monitor |
| Board won't boot with relays attached | GPIO2 / GPIO15 strapping pins |
| A relay won't click | JD-VCC jumper not removed |
| SM all identical | S0–S3 mux select wiring |
| SM reads 0 or 4095 | that channel is disconnected |
| 0/5 PONG | TX/RX swapped, or no common ground |
| Intermittent PONG | no common ground, or miniUART instead of ttyAMA0 |
| `port is busy` | `sudo systemctl stop pi-link` |
| `Permission denied` | `sudo usermod -aG dialout $USER`, re-login |

**Panic button, anywhere:** `ALLOFF` in the monitor, or Ctrl-C in `pi_bench.py` — it sends `ALLOFF` on the way out.

**Three interlocks running whether you ask or not:** any relay on longer than 15 s shuts itself off; the Pi going quiet for 30 s with a relay on kills everything; the pump refuses to run against a closed line.
