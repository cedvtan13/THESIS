#!/usr/bin/env python3
"""flash_esp.py <dir> -- flash <dir>/{bootloader,partitions,firmware}.bin to the
ESP32-S3 over UART0, using the Pi's GPIO to drive the strapping pins:

    BCM 23 (physical 16) -> ESP32 EN    (reset)
    BCM 24 (physical 18) -> ESP32 BOOT  (GPIO0)

Then resets into run mode and prints the boot output so you can see the new
firmware come up. pi-link is stopped for the flash and restarted afterwards
only if it was running before.

Usually called by ./flash_esp.sh on the Mac (build -> copy -> flash).
"""
import os
import subprocess
import sys
import time

import RPi.GPIO as GPIO
import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esp_link import PORT, stop_daemon  # noqa: E402

EN, BOOT = 23, 24
ESPTOOL = os.path.expanduser("~/.local/bin/esptool")


def main():
    d = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/fw_main")
    images = [("0x0", "bootloader.bin"), ("0x8000", "partitions.bin"), ("0x10000", "firmware.bin")]
    for _, name in images:
        p = os.path.join(d, name)
        if not os.path.isfile(p):
            sys.exit(f"missing {p}")
        print(f"  {name:16s} {os.path.getsize(p):8d} bytes  {time.ctime(os.path.getmtime(p))}")

    was_running = stop_daemon()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(EN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(BOOT, GPIO.OUT, initial=GPIO.HIGH)

    print("[1/3] entering ROM bootloader (BOOT low, pulse EN)")
    GPIO.output(BOOT, GPIO.LOW); time.sleep(0.1)
    GPIO.output(EN, GPIO.LOW); time.sleep(0.3)
    GPIO.output(EN, GPIO.HIGH); time.sleep(0.3)

    print("[2/3] flashing")
    cmd = [ESPTOOL, "--chip", "esp32s3", "--port", PORT, "--baud", "115200",
           "--before", "no-reset", "--after", "no-reset",
           "write-flash", "--flash-size", "4MB", "-z"]
    for off, name in images:
        cmd += [off, os.path.join(d, name)]
    try:
        rc = subprocess.run(cmd).returncode
    finally:
        GPIO.output(BOOT, GPIO.HIGH)   # always release BOOT, even on failure
        time.sleep(0.05)

    print("[3/3] reset into run mode -- boot output:")
    with serial.Serial(PORT, 115200, timeout=0.1) as s:
        s.reset_input_buffer()
        GPIO.output(EN, GPIO.LOW); time.sleep(0.2); GPIO.output(EN, GPIO.HIGH)
        t0 = time.time()
        while time.time() - t0 < 2.5:
            line = s.readline().decode(errors="replace").rstrip()
            if line.startswith("BOOT"):
                print(f"  {line}")
    # No GPIO.cleanup(): leave EN/BOOT driven HIGH so the ESP32 isn't left floating.

    if was_running:
        subprocess.run(["sudo", "-n", "systemctl", "start", "pi-link"])
        print("pi-link restarted")
    print("\nFLASH OK" if rc == 0 else "\nFLASH FAILED (esptool error above)")
    sys.exit(rc)


if __name__ == "__main__":
    main()
