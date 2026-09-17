#!/usr/bin/env python3
import time
import subprocess
import RPi.GPIO as GPIO

PIN_EN   = 23  # ESP32-S3 EN (Reset)
PIN_BOOT = 24  # ESP32-S3 BOOT (GPIO 0)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_EN, GPIO.OUT)
GPIO.setup(PIN_BOOT, GPIO.OUT)

print("[1/3] Putting ESP32-S3 into ROM Bootloader Mode...")
GPIO.output(PIN_BOOT, GPIO.LOW)
time.sleep(0.1)
GPIO.output(PIN_EN, GPIO.LOW)
time.sleep(0.2)
GPIO.output(PIN_EN, GPIO.HIGH)
time.sleep(0.2)
GPIO.output(PIN_BOOT, GPIO.HIGH)
time.sleep(0.1)

print("[2/3] Writing complete flash image to ESP32-S3...")
cmd = [
    "esptool",
    "--chip", "esp32s3",
    "--port", "/dev/serial0",
    "--baud", "115200",
    "--before", "no-reset",
    "--after", "no-reset",
    "write-flash", "-z",
    "0x0", "/home/crk/bootloader.bin",
    "0x8000", "/home/crk/partitions.bin",
    "0x10000", "/home/crk/firmware.bin"
]

res = subprocess.run(cmd)

print("[3/3] Resetting ESP32-S3 into Normal Run Mode...")
GPIO.output(PIN_BOOT, GPIO.HIGH)
GPIO.output(PIN_EN, GPIO.LOW)
time.sleep(0.2)
GPIO.output(PIN_EN, GPIO.HIGH)
GPIO.cleanup()

if res.returncode == 0:
    print("\nFirmware flashed successfully!")
else:
    print("\nFlashing failed.")
