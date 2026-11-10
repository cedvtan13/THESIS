// ph4502c.ino -- soil-slurry pH with a PH-4502C board on an Arduino Uno.
//
// Use a separate Arduino Uno, NOT the experiment's ESP32 (its ADC is 3.3 V and
// the board must not be disturbed during the run).
//
// Wiring (PH-4502C pin -> Uno):
//   V+ -> 5V      G -> GND      Po -> A0      (To and Do are not used)
//
// Serial Monitor: 9600 baud, line ending "Newline".
// The sketch prints a reading every 2 s. Type a command and press Enter:
//   7   save the current voltage as the pH 7.00 point (probe in pH 7 buffer)
//   4   save the current voltage as the pH 4.00 point (probe in pH 4 buffer)
//   s   show the calibration and slope
//   c   clear the calibration
// The calibration is kept in EEPROM, so it survives unplugging. Still
// re-calibrate at the start of every measuring session.
//
// Procedure per session:
//   1. Rinse probe with distilled water, blot (don't rub) with tissue.
//   2. Put it in pH 7.00 buffer, wait until the volts stop changing (~1 min), type 7.
//   3. Rinse, put it in pH 4.00 buffer, wait until stable, type 4.
//   4. Type s: the slope should be roughly 0.15-0.19 V per pH. Much lower means
//      a tired or dry probe; redo the calibration or soak the probe.
//   5. Measure samples (rinse between each). Wait for a stable reading, write it down.
//   6. At the end, check pH 7.00 buffer again: within +-0.1 means no drift.

#include <EEPROM.h>

const int PH_PIN = A0;
const float VREF = 5.0;          // Uno ADC reference (powered from USB)
const int N = 30;                // samples per reading
const int TRIM = 5;              // drop this many lowest and highest samples
const uint16_t MAGIC = 0x4502;   // marks a saved calibration

struct Cal {
  uint16_t magic;
  float v7;                      // volts in pH 7.00 buffer
  float v4;                      // volts in pH 4.00 buffer
};
Cal cal;

float readVolts() {
  int buf[N];
  for (int i = 0; i < N; i++) {
    buf[i] = analogRead(PH_PIN);
    delay(20);
  }
  for (int i = 1; i < N; i++) {  // insertion sort
    int k = buf[i];
    int j = i - 1;
    while (j >= 0 && buf[j] > k) { buf[j + 1] = buf[j]; j--; }
    buf[j + 1] = k;
  }
  long sum = 0;
  for (int i = TRIM; i < N - TRIM; i++) sum += buf[i];
  return (sum / (float)(N - 2 * TRIM)) * VREF / 1023.0;
}

bool hasPoint(float v) { return !isnan(v); }

bool calibrated() {
  return cal.magic == MAGIC && hasPoint(cal.v7) && hasPoint(cal.v4)
         && fabs(cal.v4 - cal.v7) > 0.05;
}

float slopeVperPH() { return (cal.v4 - cal.v7) / 3.0; }

float toPH(float v) { return 7.0 - (v - cal.v7) / slopeVperPH(); }

void saveCal() {
  cal.magic = MAGIC;
  EEPROM.put(0, cal);
}

void showCal() {
  Serial.print(F("pH 7 point: "));
  if (hasPoint(cal.v7)) { Serial.print(cal.v7, 3); Serial.println(F(" V")); }
  else Serial.println(F("not set"));
  Serial.print(F("pH 4 point: "));
  if (hasPoint(cal.v4)) { Serial.print(cal.v4, 3); Serial.println(F(" V")); }
  else Serial.println(F("not set"));
  if (calibrated()) {
    Serial.print(F("slope: "));
    Serial.print(slopeVperPH(), 3);
    Serial.println(F(" V per pH (expect about 0.15-0.19)"));
  }
}

void setup() {
  Serial.begin(9600);
  EEPROM.get(0, cal);
  if (cal.magic != MAGIC) { cal.v7 = NAN; cal.v4 = NAN; }
  Serial.println(F("PH-4502C ready. Commands: 7, 4, s, c"));
  showCal();
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "7" || cmd == "4") {
      float v = readVolts();
      if (cmd == "7") cal.v7 = v; else cal.v4 = v;
      saveCal();
      Serial.print(F("saved pH ")); Serial.print(cmd);
      Serial.print(F(".00 point = ")); Serial.print(v, 3); Serial.println(F(" V"));
      showCal();
    } else if (cmd == "s") {
      showCal();
    } else if (cmd == "c") {
      cal.v7 = NAN; cal.v4 = NAN;
      saveCal();
      Serial.println(F("calibration cleared"));
    }
  }

  float v = readVolts();
  Serial.print(F("V = ")); Serial.print(v, 3);
  if (calibrated()) {
    Serial.print(F("   pH = ")); Serial.print(toPH(v), 2);
  } else {
    Serial.print(F("   (not calibrated: type 7 in pH 7 buffer, then 4 in pH 4 buffer)"));
  }
  Serial.println();
  delay(2000);
}
