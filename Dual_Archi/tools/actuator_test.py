#!/usr/bin/env python3
"""actuator_test.py -- interactive relay / actuator tester.

Pick a relay, pick how long, watch it switch. Every action needs a keypress;
nothing runs on its own.

  Relays:  1-9 solenoids P-01..P-09 | 10 pump | 11 fans | 12 light
  Water:   w <pot> <ms>  opens that pot's solenoid THEN the pump (real dose path)
  Multi:   m 1,2,10 <ms> several relays ON together (load / power-supply test)
  Cycle:   all           each relay in turn, Enter between each
  Quit:    q

Needs firmware built with ACTUATORS_ENABLED = true (top of main.cpp), then
./flash_esp.sh. With it false the ESP32 replies ERR,...,ACTUATORS_DISABLED and
nothing switches.

SAFETY: running the pump alone (10) pushes against closed valves. Keep it short,
or use "w" which opens a valve first.

After every action the ESP32's uptime is checked. If it went DOWN, the board
rebooted during the switching: a power problem (supply sag / inductive spike),
not a software one.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esp_link import EspLink, info_dict, stop_daemon  # noqa: E402

NAMES = [f"Solenoid P-0{i}" for i in range(1, 10)] + ["Pump", "Fans", "Light"]
MAX_MS = 10000


def menu():
    print("\n  #   relay")
    for i, n in enumerate(NAMES, 1):
        print(f"  {i:<3} {n}")
    print("  w <pot 1-9> <ms>   water test (valve + pump)")
    print("  m 1,2,10 <ms>      several relays ON at the same time, e.g. P-01 + P-02 + pump")
    print("  all                cycle every relay (Enter between each)")
    print("  q                  quit")


def uptime(esp):
    try:
        return int(info_dict(esp.ask("INFO", "INFO", 3)).get("uptime_s", -1))
    except ValueError:
        return -1


def watched(esp, cmd, expect, timeout):
    """Send an actuator command and report whether the ESP32 survived it."""
    before = uptime(esp)
    r = esp.ask(cmd, expect, timeout)
    print(f"  <- {r}" if r else "  <- no reply")
    time.sleep(0.3)
    after = uptime(esp)
    if after < 0:
        print("  !! ESP32 not answering after the test -- it may have crashed or browned out")
    elif before >= 0 and after < before:
        print(f"  !! ESP32 REBOOTED during the test (uptime {before}s -> {after}s).\n"
              "     Power problem: the 12V/5V supply sagged or an inductive spike reached the\n"
              "     ESP32. Check flyback diodes, supply current rating, and grounding.")
    else:
        print(f"  ok: ESP32 stayed up (uptime {after}s)")
    return bool(r) and r.startswith("ACK")


def pulse(esp, idx, ms):
    print(f"  -> {NAMES[idx]} ON for {ms} ms ...", flush=True)
    return watched(esp, f"TEST_RELAY,{idx},{ms}", "ACK,TEST_RELAY", ms / 1000 + 3)


def main():
    stop_daemon()
    with EspLink() as esp:
        esp.sync_time()
        info = info_dict(esp.ask("INFO", "INFO", 3))
        state = info.get("actuators", "UNKNOWN (old firmware?)")
        print(f"\nESP32 actuators: {state}")
        if state != "ENABLED":
            print("  Relays will NOT switch. To enable: set ACTUATORS_ENABLED = true at the top of\n"
                  "  Dual_Archi_Firmware/src/main.cpp, then run ./flash_esp.sh on the Mac.")
        menu()
        while True:
            try:
                cmd = input("\nactuator> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if cmd in ("q", "quit", "exit"):
                break
            if cmd in ("", "?", "h", "help"):
                menu()
                continue
            parts = cmd.split()
            try:
                if parts[0] == "all":
                    ms = int(parts[1]) if len(parts) > 1 else 1000
                    for idx in range(len(NAMES)):
                        input(f"  Enter to fire {NAMES[idx]} ({ms} ms), Ctrl-C to stop ")
                        pulse(esp, idx, min(ms, MAX_MS))
                elif parts[0] == "w":
                    pot, ms = int(parts[1]), int(parts[2]) if len(parts) > 2 else 2000
                    if not 1 <= pot <= 9:
                        raise ValueError
                    ms = min(ms, 15000)
                    print(f"  -> water P-0{pot}: valve, then pump, {ms} ms")
                    watched(esp, f"MANUAL_WATER,{pot - 1},{ms}", "ACK,MANUAL_WATER", ms / 1000 + 4)
                elif parts[0] == "m":
                    nums = sorted({int(n) for n in parts[1].split(",")})
                    if not nums or not all(1 <= n <= len(NAMES) for n in nums):
                        raise ValueError
                    ms = max(50, min(int(parts[2]) if len(parts) > 2 else 3000, MAX_MS))
                    print("  -> ON together for %d ms: %s" % (ms, ", ".join(NAMES[n - 1] for n in nums)))
                    if 10 in nums and not any(n <= 9 for n in nums):
                        print("     (pump with no valve open -- keep it short)")
                    idxs = ",".join(str(n - 1) for n in nums)
                    watched(esp, f"TEST_MULTI,{ms},{idxs}", "ACK,TEST_MULTI",
                            ms / 1000 + 0.25 * len(nums) + 4)
                else:
                    idx = int(parts[0]) - 1
                    if not 0 <= idx < len(NAMES):
                        raise ValueError
                    ms = int(parts[1]) if len(parts) > 1 else int(
                        input(f"  how long (ms, max {MAX_MS}) [1000]: ") or 1000)
                    pulse(esp, idx, max(50, min(ms, MAX_MS)))
            except (ValueError, IndexError):
                print("  ? try: 3   |   3 1500   |   w 4 2000   |   m 1,2,10 3000   |   all   |   q")
            except KeyboardInterrupt:
                print("\n  stopped")
    print("done. pi-link is still stopped; start the system with tools/agrisentry.sh start")


if __name__ == "__main__":
    main()
