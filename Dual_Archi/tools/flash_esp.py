#!/usr/bin/env python3
import time
import subprocess
import RPi.GPIO as GPIO

PIN_BOOT = 24  # ESP32 GPIO 0
PIN_EN   = 23  # ESP32 EN

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_BOOT, GPIO.OUT)
GPIO.setup(PIN_EN, GPIO.OUT)

print("[1/3] Setting ESP32 to Bootloader Mode...")
GPIO.output(PIN_BOOT, GPIO.LOW)
time.sleep(0.1)
GPIO.output(PIN_EN, GPIO.LOW)
time.sleep(0.2)
GPIO.output(PIN_EN, GPIO.HIGH)
time.sleep(0.3)
GPIO.output(PIN_BOOT, GPIO.HIGH)

print("[2/3] Flashing firmware.bin...")
cmd = [
    "esptool",
    "--chip", "esp32s3",
    "--port", "/dev/serial0",
    "--baud", "115200",
    "--before", "no_reset",
    "--after", "no_reset",
    "write_flash", "-z", "0x10000", "/home/crk/firmware.bin"
]

res = subprocess.run(cmd)

print("[3/3] Resetting ESP32 into Run Mode...")
GPIO.output(PIN_BOOT, GPIO.HIGH)
GPIO.output(PIN_EN, GPIO.LOW)
time.sleep(0.2)
GPIO.output(PIN_EN, GPIO.HIGH)
GPIO.cleanup()

if res.returncode == 0:
    print("\nFirmware flashed successfully!")
else:
    print("\nFlashing failed.")
