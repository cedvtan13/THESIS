# Bench Test — Pi ↔ ESP32

Standalone PlatformIO project. Does **not** touch `Dual_Archi_Firmware`.

Proves three things, in this order. Do not skip ahead.

| # | Test | Command | Pass condition |
|---|------|---------|----------------|
| 1 | UART link | `pi_bench.py --ping` | 5/5 PONG |
| 2 | Moisture sensors | `pi_bench.py --sm` / `--uniform` | 9 plausible values, none stuck |
| 3 | Relays, **dry** | `pi_bench.py --sweep` | each index fires the valve it names |
| 4 | Relays, wet | `pi_bench.py --pulse <n> <ms>` | flow, no leaks |

## Flash it

```bash
pio run -e nodemcu-32s -t upload
```

Or in VS Code: **File → Open Folder →** this folder, then the ✓ (build) and → (upload)
buttons in the blue status bar. PlatformIO only recognises a folder as a project
if `platformio.ini` sits at its root — that is why this folder exists.

## Wiring

```
ESP32 GPIO17 (TX2)  ->  Pi pin 10 (RXD)
ESP32 GPIO16 (RX2)  <-  Pi pin  8 (TXD)
ESP32 GND           <-> Pi pin  6        mandatory
```

TX goes to RX. Swapping these is the most common reason nothing comes back.

Relay board: remove the JD-VCC/VCC jumper. JD-VCC ← 5 V, VCC ← 3.3 V, GND ← ESP32 GND.
Flyback diode (1N4007) across the pump and across each solenoid, banded end to +12 V.

## On the Pi

```bash
sudo systemctl stop pi-link      # it holds /dev/ttyAMA0 exclusively
python3 pi_bench.py --ping
sudo systemctl start pi-link     # RESTART IT -- it is the ESP32's clock source
```

If only `/dev/ttyS0` exists and not `/dev/ttyAMA0`, you are on the miniUART, whose
baud rate drifts with CPU frequency and will corrupt bytes. Add `dtoverlay=disable-bt`
to `/boot/firmware/config.txt` and reboot.

## Protocol

| Command | Reply |
|---|---|
| `PING` | `PONG` |
| `SM` | `SM,<p1>,…,<p9>` — percent of container capacity, `NaN` if out of range |
| `SM_RAW` | `SMRAW,<adc1>,…,<adc9>` |
| `UNIFORM[,n]` | `UNIF,<means…>,avg=,spread=,spreadpct=` |
| `STATUS` | `STAT,<10 relay states>,uptime=` |
| `RELAY,<0-9>,<0\|1>` | `EVT,RELAY,…` then `ACK,RELAY` |
| `PULSE,<1-9>,<ms>` | `EVT,PULSE,<idx>,<actual_ms>` |
| `ALLOFF` | `EVT,ALLOFF,commanded` |

Relay index **0 = pump**, 1–9 = solenoids P-01…P-09.

## Safety interlocks

- OFF is latched **before** `pinMode()`, so no relay clicks during the boot glitch.
- `MAX_ON_MS = 15000` — any relay auto-releases after 15 s.
- `LINK_TIMEOUT_MS = 30000` — Pi goes quiet with a relay on, everything drops.
- Pump refuses to run with every valve closed; one solenoid at a time.

## Two known hardware notes

**`RELAY_PINS` order is load-bearing.** Index *i* must be the valve feeding pot
P-0*i*. It is copied verbatim from `Dual_Archi_Firmware/src/main.cpp`, but the
physical wiring is the authority — `--sweep` is what verifies it. A wrong order
waters the wrong pot and the CSV records it as correct.

**`PUMP_PIN` and `LED_INDICATOR_PIN` are both GPIO2** in the production firmware's
NodeMCU block (main.cpp lines 28 and 38). Relays are active LOW, so writing the
LED low energises the pump. Harmless today; a pump that runs itself the moment
anyone blinks that LED as a status code. Not fixed here — this sketch touches no LED.
