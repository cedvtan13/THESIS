import time
import RPi.GPIO as GPIO

PIN_EN   = 23  # Connected to ESP32 EN / RST
PIN_BOOT = 24  # Connected to ESP32 GPIO 0

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_BOOT, GPIO.OUT)
GPIO.setup(PIN_EN, GPIO.OUT)

# Pulse ESP32 into ROM bootloader mode
GPIO.output(PIN_BOOT, GPIO.LOW)
time.sleep(0.1)
GPIO.output(PIN_EN, GPIO.LOW)
time.sleep(0.2)
GPIO.output(PIN_EN, GPIO.HIGH)
time.sleep(0.2)
GPIO.output(PIN_BOOT, GPIO.HIGH)

GPIO.cleanup()
print("ESP32 is now in bootloader mode.")
