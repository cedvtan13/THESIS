#!/usr/bin/env python3
"""
pi_bench.py -- Raspberry Pi side of the bench test. Talks to bench_test.ino.

RUN THESE IN ORDER. Do not skip ahead -- each one assumes the previous passed.

  1. LINK           python3 pi_bench.py --ping
  2. SENSORS        python3 pi_bench.py --sm
                    python3 pi_bench.py --uniform        <- all 9 in ONE bucket
  3. RELAYS DRY     python3 pi_bench.py --sweep          <- NO water, NO 12 V
  4. RELAYS WET     python3 pi_bench.py --pulse 1 2000   <- one pot at a time

  interactive:      python3 pi_bench.py --shell
  live sensors:     python3 pi_bench.py --monitor

BEFORE YOU START
  The pi-link daemon owns /dev/ttyAMA0. Stop it first:
      sudo systemctl stop pi-link
  ...and remember that stopping it also stops the ESP32's clock source, so
  restart it when you are done:
      sudo systemctl start pi-link
"""

import argparse
import os
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("pyserial missing:  sudo apt install python3-serial")

BAUD = 115200


def default_port():
    """/dev/ttyAMA0 only exists once dtoverlay=disable-bt is in config.txt.
    Without it /dev/serial0 is the miniUART, whose baud drifts with the CPU
    clock and corrupts bytes under load -- fine to bench with, not fine to
    collect data with."""
    env = os.environ.get("AGRISENTRY_PORT")
    if env:
        return env
    if os.path.exists("/dev/ttyAMA0"):
        return "/dev/ttyAMA0"
    if os.path.exists("/dev/serial0"):
        print("[warn] /dev/ttyAMA0 missing -- using /dev/serial0 (miniUART).\n"
              "       Add 'dtoverlay=disable-bt' to /boot/firmware/config.txt and reboot.",
              file=sys.stderr)
        return "/dev/serial0"
    sys.exit("no serial port found. Is the UART enabled? (raspi-config -> Interface -> Serial)")


def open_link(port):
    try:
        ser = serial.Serial(port, BAUD, timeout=2, exclusive=True)
    except serial.SerialException as e:
        msg = str(e)
        if "Permission" in msg:
            sys.exit(f"{port}: permission denied. Run:  sudo usermod -aG dialout $USER  then log out and back in.")
        if "busy" in msg.lower() or "exclusive" in msg.lower():
            sys.exit(f"{port} is already open -- almost certainly the pi-link daemon.\n"
                     f"  sudo systemctl stop pi-link\n"
                     f"  ...and 'start' it again when you finish.")
        sys.exit(f"could not open {port}: {e}")
    time.sleep(0.3)
    ser.reset_input_buffer()
    return ser


def send(ser, cmd, expect=None, timeout=6.0, quiet=False):
    """Send one line, collect replies until `expect` arrives or we time out."""
    ser.reset_input_buffer()
    ser.write((cmd + "\n").encode())
    t0 = time.time()
    lines = []
    while time.time() - t0 < timeout:
        raw = ser.readline().decode(errors="replace").strip()
        if not raw:
            continue
        lines.append(raw)
        if not quiet:
            print(f"  < {raw}")
        if expect is None or raw.startswith(expect):
            return lines, time.time() - t0
    return lines, None


def no_reply_help():
    print("""
NO REPLY. Work through these in order:

  1. Is the ESP32 powered and running bench_test.ino? Watch its USB console --
     you should see  BOOT,bench_test,...  at reset.
  2. TX/RX swapped? This is the usual one. ESP32 TX must go to Pi RXD
     (GPIO15 / physical pin 10); ESP32 RX to Pi TXD (GPIO14 / pin 8).
  3. Common ground? ESP32 GND to Pi pin 6. Not optional -- without it the
     link "works" intermittently and looks like a software bug.
  4. Serial console still enabled on the Pi? It fights you for the port:
       sudo raspi-config nonint do_serial_cons 1
  5. Wrong port -- try:  AGRISENTRY_PORT=/dev/serial0 python3 pi_bench.py --ping
""")


# ---------------------------------------------------------------- commands --
def cmd_ping(ser, n=5):
    print(f"PING x{n}")
    ok = 0
    times = []
    for i in range(n):
        lines, dt = send(ser, "PING", expect="PONG", timeout=3, quiet=True)
        if dt is not None:
            ok += 1
            times.append(dt * 1000)
            print(f"  {i+1}: PONG in {dt*1000:.1f} ms")
        else:
            print(f"  {i+1}: no reply" + (f"  (got: {lines})" if lines else ""))
        time.sleep(0.2)
    print()
    if ok == 0:
        print("LINK DOWN — 0/%d replied." % n)
        no_reply_help()
        return False
    print(f"LINK OK — {ok}/{n} replied, mean {sum(times)/len(times):.1f} ms")
    if ok < n:
        print("  ⚠ dropped replies means a marginal link. Check grounding and\n"
              "    that you are on /dev/ttyAMA0, not the miniUART.")
    return True


def cmd_sm(ser, raw=False):
    lines, dt = send(ser, "SM_RAW" if raw else "SM",
                     expect="SMRAW" if raw else "SM", timeout=8, quiet=True)
    if dt is None:
        print("no SM reply"); no_reply_help(); return
    vals = lines[-1].split(",")[1:]
    label = "raw ADC" if raw else "% of container capacity"
    print(f"\n  pot     {label}")
    for i, v in enumerate(vals[:9]):
        flag = "  <-- FAULT" if v == "NaN" else ""
        print(f"  P-0{i+1}   {v:>10}{flag}")
    print()


def cmd_uniform(ser, reps=16):
    print("\nUNIFORMITY — all nine probes must be in the SAME medium, same depth.")
    print("Wait 60 s after placing them before you trust this.\n")
    lines, dt = send(ser, f"UNIFORM,{reps}", expect="UNIF", timeout=30, quiet=True)
    if dt is None:
        print("no reply"); return
    parts = lines[-1].split(",")
    means = [float(x) for x in parts[1:10]]
    meta = dict(p.split("=") for p in parts[10:] if "=" in p)
    avg = float(meta.get("avg", sum(means) / 9))
    print("  pot     mean raw    deviation")
    for i, m in enumerate(means):
        dev = 100.0 * (m - avg) / avg
        mark = "  <-- OUTLIER" if abs(dev) > 5 else ""
        print(f"  P-0{i+1}   {m:>9.1f}   {dev:+7.2f}%{mark}")
    print(f"\n  group mean {avg:.1f}   spread {meta.get('spread','?')} counts "
          f"({meta.get('spreadpct','?')}%)")
    sp = float(meta.get("spreadpct", 99))
    if sp < 2:
        print("  ✅ under 2% — one shared constant pair is defensible.")
    elif sp < 5:
        print("  ⚠ 2-5% — borderline. Per-sensor constants would be safer.")
    else:
        print("  ❌ over 5% — your nine pots are NOT on a common scale.\n"
              "     Each sensor needs its own dryADC/wetADC, or the treatment\n"
              "     separation you report is partly sensor spread.")
    print()


def cmd_sweep(ser, on_ms=800):
    print("""
RELAY SWEEP — first pass must be DRY.
  Disconnect the 12 V supply and the water. You are listening for clicks
  and watching the board LEDs, nothing else.
""")
    if input("12 V and water disconnected? type YES: ").strip() != "YES":
        print("aborted."); return

    names = ["PUMP"] + [f"SOLENOID P-0{i}" for i in range(1, 10)]
    results = {}
    for idx, name in enumerate(names):
        # the pump is interlocked against running with no valve open, so open
        # valve 1 first when testing it
        if idx == 0:
            send(ser, "RELAY,1,1", expect="EVT,RELAY", timeout=3, quiet=True)
        input(f"\n  [{idx}] {name} — press Enter to switch ON")
        send(ser, f"RELAY,{idx},1", expect=None, timeout=3, quiet=True)
        time.sleep(on_ms / 1000.0)
        send(ser, f"RELAY,{idx},0", expect=None, timeout=3, quiet=True)
        if idx == 0:
            send(ser, "RELAY,1,0", expect=None, timeout=3, quiet=True)
        ans = input(f"      did you hear TWO clicks (on then off)? [y/n] ").strip().lower()
        results[name] = ans.startswith("y")

    print("\n  RESULTS")
    bad = []
    for name, ok in results.items():
        print(f"    {name:<18} {'OK' if ok else 'FAILED'}")
        if not ok:
            bad.append(name)
    if bad:
        print(f"\n  {len(bad)} channel(s) failed. Check, in this order:")
        print("    * relay coils need 5 V — pull the JD-VCC/VCC jumper,")
        print("      JD-VCC<-5V, VCC<-3.3V. 3.3 V alone will not pull them in.")
        print("    * the GPIO in RELAY_PINS[] matches the wire you actually ran")
        print("    * that GPIO can drive output (not 34-39 on a classic ESP32)")
    else:
        print("\n  ✅ all channels switch. Now repeat with 12 V connected but")
        print("     still NO water, then with water one pot at a time.")
    send(ser, "ALLOFF", expect=None, timeout=3, quiet=True)
    print()


def cmd_pulse(ser, idx, ms):
    print(f"\nPULSE solenoid {idx} for {ms} ms (valve opens, pump runs, both close)")
    lines, dt = send(ser, f"PULSE,{idx},{ms}", expect="EVT,PULSE", timeout=ms / 1000.0 + 10)
    if dt is None:
        print("  no completion event — check the ERR lines above.")
    print()


def cmd_monitor(ser, period=3.0):
    print("live sensors — Ctrl-C to stop\n")
    hdr = "   " + "".join(f"  P-0{i+1}" for i in range(9))
    try:
        n = 0
        while True:
            if n % 20 == 0:
                print(hdr)
            lines, dt = send(ser, "SM", expect="SM", timeout=8, quiet=True)
            if dt is None:
                print("   (no reply)")
            else:
                vals = lines[-1].split(",")[1:10]
                print("   " + "".join(f"{v:>6}" for v in vals))
            n += 1
            time.sleep(period)
    except KeyboardInterrupt:
        print("\nstopped.")


def cmd_shell(ser):
    print("interactive. Type a command, or 'q' to quit. 'ALLOFF' is your panic button.\n")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ("q", "quit", "exit"):
            break
        if not line:
            continue
        send(ser, line, expect=None, timeout=4)
    send(ser, "ALLOFF", expect=None, timeout=3, quiet=True)


# ------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser(description="Group B bench test driver")
    ap.add_argument("--port", default=None)
    ap.add_argument("--ping", action="store_true")
    ap.add_argument("--sm", action="store_true")
    ap.add_argument("--sm-raw", action="store_true")
    ap.add_argument("--uniform", nargs="?", type=int, const=16)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--relay", nargs=2, metavar=("IDX", "ON"))
    ap.add_argument("--pulse", nargs=2, type=int, metavar=("IDX", "MS"))
    ap.add_argument("--monitor", action="store_true")
    ap.add_argument("--shell", action="store_true")
    args = ap.parse_args()

    port = args.port or default_port()
    print(f"[pi_bench] {port} @ {BAUD}")
    ser = open_link(port)

    try:
        if args.ping:      cmd_ping(ser)
        elif args.sm:      cmd_sm(ser, False)
        elif args.sm_raw:  cmd_sm(ser, True)
        elif args.uniform is not None: cmd_uniform(ser, args.uniform)
        elif args.sweep:   cmd_sweep(ser)
        elif args.relay:   send(ser, f"RELAY,{args.relay[0]},"
                                     f"{1 if args.relay[1].lower() in ('1','on','true') else 0}")
        elif args.pulse:   cmd_pulse(ser, args.pulse[0], args.pulse[1])
        elif args.monitor: cmd_monitor(ser)
        elif args.shell:   cmd_shell(ser)
        else:
            ap.print_help()
            print("\nStart with:  python3 pi_bench.py --ping")
    finally:
        try:
            ser.write(b"ALLOFF\n")      # never leave a relay on
            time.sleep(0.2)
        except Exception:
            pass
        ser.close()


if __name__ == "__main__":
    main()
