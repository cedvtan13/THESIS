#!/usr/bin/env python3
"""bench_check.py -- one-shot health check of the whole rig. Writes NO CSV data.

  1. ESP32 link        PING / PONG, firmware INFO
  2. BMP388            enclosure temperature / pressure
  3. Soil moisture     raw ADC + calibrated % per pot, with a verdict
  4. Relays            (only with --relays) clicks each relay briefly
  5. Camera            real capture through capture_gpr.py's own ROI + HSV
                       masking (--no-write --no-sm), saved as an overlay PNG

The pi-link service is stopped and LEFT stopped (testing mode). Start the
system again with tools/agrisentry.sh start.

Usually run from the Mac via ./bench_test.sh, which also copies the overlay
image back to the laptop and opens it.
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esp_link import EspLink, info_dict, stop_daemon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DUAL = os.path.dirname(HERE)

# Must match the firmware (main.cpp)
ADC_FAULT_LOW, ADC_FAULT_HIGH = 150, 4000
DRY_ADC, WET_ADC = 2483, 1120
RELAY_NAMES = [f"P-0{i}" for i in range(1, 10)] + ["PUMP", "FANS", "LIGHT"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    mark = "PASS" if ok else ("WARN" if ok is None else "FAIL")
    print(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))


def sensor_verdict(raw):
    if raw < ADC_FAULT_LOW:
        return False, "below fault floor: disconnected / shorted?"
    if raw > ADC_FAULT_HIGH:
        return False, "above fault ceiling: open circuit / no power?"
    if raw < WET_ADC - 150:
        return None, "wetter than wet calibration (probe in water, or floating input?)"
    if raw > DRY_ADC + 150:
        return None, "drier than dry calibration (probe in air?)"
    return True, "in calibrated range"


def main():
    ap = argparse.ArgumentParser(description="AgriSentry bench check")
    ap.add_argument("--relays", action="store_true",
                    help="also click every relay (needs ACTUATORS_ENABLED=true firmware)")
    ap.add_argument("--relay-ms", type=int, default=500)
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--out", default="/tmp/agrisentry_bench",
                    help="where the overlay image goes")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    stop_daemon()

    print("\n== 1. ESP32 link")
    try:
        esp = EspLink()
    except Exception as exc:
        check("serial port", False, str(exc))
        return finish()
    with esp:
        pongs = sum(1 for _ in range(5) if (esp.ask("PING", "PONG", 2) or "").startswith("PONG"))
        check("PING/PONG", pongs == 5, f"{pongs}/5 replies")
        esp.sync_time()
        info = info_dict(esp.ask("INFO", "INFO", 3))
        if info:
            print(f"         firmware: {info}")
        else:
            check("INFO", None, "no reply (older firmware? reflash with ./flash_esp.sh)")

        print("\n== 2. BMP388 enclosure sensor")
        if info.get("bmp388") == "ONLINE":
            clim = esp.ask("GET_CLIM", "CLIM", 3)
            p = (clim or "").split(",")
            check("BMP388", len(p) == 4, f"{p[2]} C, {p[3]} hPa" if len(p) == 4 else clim)
        else:
            check("BMP388", False, "OFFLINE (not detected at I2C 0x76 on SDA41/SCL40)")

        print("\n== 3. Soil moisture sensors")
        raw = esp.ask("GET_RAW", "RAW", 8)
        sm = esp.ask("GET_SM_FRESH", "SM", 15)
        if raw and raw.startswith("RAW"):
            raws = [int(v) for v in raw.split(",")[2:]]
            pcts = sm.split(",")[2:] if sm and sm.startswith("SM") else ["?"] * 9
            print("         pot    raw ADC   moisture")
            for i, (r, pct) in enumerate(zip(raws, pcts)):
                ok, why = sensor_verdict(r)
                check(f"P-0{i + 1}   {r:5d}   {pct:>6}%", ok, why)
            if len(set(raws)) == 1 or max(raws) - min(raws) < 20:
                print("         note: all pots read nearly the same -- typical of the MUX "
                      "with no probes plugged in")
        else:
            check("GET_RAW", False, raw or "no reply (reflash firmware with ./flash_esp.sh)")

        print("\n== 4. Relays")
        if not args.relays:
            print("  [SKIP] pass --relays to click each relay "
                  "(or use ./actuator_test.sh for one at a time)")
        elif info.get("actuators") != "ENABLED":
            check("relays", False, "firmware has ACTUATORS_ENABLED = false -- nothing will switch")
        else:
            for idx, name in enumerate(RELAY_NAMES):
                r = esp.ask(f"TEST_RELAY,{idx},{args.relay_ms}", "ACK,TEST_RELAY",
                            args.relay_ms / 1000 + 3)
                check(f"relay {name}", bool(r) and r.startswith("ACK"),
                      "listen for the click" if r and r.startswith("ACK") else r)
                time.sleep(0.3)

    print("\n== 5. Camera + ROI masking")
    if args.no_camera:
        print("  [SKIP] --no-camera")
    else:
        png = os.path.join(args.out, "bench_overlay.png")
        r = subprocess.run([sys.executable, os.path.join(DUAL, "capture_gpr.py"),
                            "--no-write", "--no-sm", "--allow-any-day",
                            "--debug-overlay", png],
                           capture_output=True, text=True, timeout=120,
                           env={**os.environ, "LIBCAMERA_LOG_LEVELS": "*:ERROR"})
        print("\n".join("         " + l for l in (r.stdout + r.stderr).strip().splitlines()))
        check("camera capture + overlay", r.returncode == 0 and os.path.exists(png), png)

    return finish()


def finish():
    fails = [n for n, ok in results if ok is False]
    warns = [n for n, ok in results if ok is None]
    print(f"\n== SUMMARY: {len(results) - len(fails) - len(warns)} pass, "
          f"{len(warns)} warn, {len(fails)} fail")
    print("   pi-link service is STOPPED (testing mode). "
          "Start the system with: tools/agrisentry.sh start")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
