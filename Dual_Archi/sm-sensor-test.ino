/*
  sm_sensor_test.ino -- bench test + calibration logger for the 9 capacitive
  soil moisture sensors.  Group B thesis rig.

  Answers four different questions, in the order you should ask them:

    1. Does every sensor respond at all?                 -> S / C
    2. Do the nine sensors AGREE with each other?        -> U   <- the big one
    3. How noisy is a single sensor?                     -> N
    4. What raw value corresponds to a known water
       content, so we can build a real calibration?      -> L

  WHY (2) MATTERS MOST FOR YOUR THESIS
  ------------------------------------
  Your experiment compares pots against each other. If sensor 3 reads 12% when
  sensor 7 reads 20% in the SAME soil, then "Group A at 30-40%" and "Group C at
  70-80%" are not on a common scale, and the treatment separation you report is
  partly sensor spread. This is the test nobody runs and everybody should.

  ADC CHANNEL WARNING
  -------------------
  A classic ESP32 (NodeMCU-32S) has only 8 ADC1 channels and most dev boards
  break out 6 (GPIO 32,33,34,35,36,39). ADC2 cannot be used while Wi-Fi is on.
  So NINE sensors do NOT fit directly on a NodeMCU-32S -- you need an external
  ADC (ADS1115) or a 16-channel mux (CD74HC4067), or test in two batches.
  The ESP32-S3 has 10 usable ADC1 channels (GPIO1-10), which is why the final
  board is an S3. Set PINS below to whatever you actually have wired.

  WIRING
    sensor VCC -> 3.3V   (NOT 5V -- the analog output would exceed the ADC)
    sensor GND -> GND
    sensor AOUT-> one of the PINS below
  Power all nine from the same rail. A sagging supply shifts every reading.

  SERIAL: 115200 baud, Newline line ending.
*/

#include <Arduino.h>

// ---- set these to the pins you actually wired -----------------------------
// classic ESP32 (NodeMCU-32S), ADC1 only:
const int PINS[] = {36, 39, 32, 33, 34, 35};
// ESP32-S3 (final board) -- comment the line above, uncomment this:
// const int PINS[] = {1, 2, 3, 4, 5, 6, 7, 8, 9};

const int NCH = sizeof(PINS) / sizeof(PINS[0]);

const int   SAMPLES   = 64;      // per reading, median-filtered
const int   ADC_BITS  = 12;      // ESP32 default: 0..4095

// ---------------------------------------------------------------------------
int cmpInt(const void *a, const void *b) { return (*(int *)a - *(int *)b); }

// Median of SAMPLES reads. Median, not mean: it rejects the occasional wild
// ADC sample without being dragged by it.
int readRaw(int pin) {
  static int buf[SAMPLES];
  for (int i = 0; i < SAMPLES; i++) { buf[i] = analogRead(pin); delayMicroseconds(200); }
  qsort(buf, SAMPLES, sizeof(int), cmpInt);
  return buf[SAMPLES / 2];
}

// The ESP32's raw ADC is noticeably non-linear. analogReadMilliVolts() applies
// the chip's factory calibration and is much closer to the truth -- log BOTH so
// you can decide later which one your calibration curve should be built on.
uint32_t readMv(int pin) {
  uint32_t acc = 0;
  for (int i = 0; i < 16; i++) { acc += analogReadMilliVolts(pin); delayMicroseconds(200); }
  return acc / 16;
}

void scanOnce(bool header) {
  if (header) {
    Serial.print("     ");
    for (int i = 0; i < NCH; i++) { Serial.printf("  S%d(G%02d)", i + 1, PINS[i]); }
    Serial.println();
  }
  Serial.print("raw ");
  for (int i = 0; i < NCH; i++) Serial.printf("%9d", readRaw(PINS[i]));
  Serial.println();
  Serial.print("mV  ");
  for (int i = 0; i < NCH; i++) Serial.printf("%9u", readMv(PINS[i]));
  Serial.println();
}

// --- (2) the uniformity test ----------------------------------------------
void uniformity(int reps) {
  Serial.println();
  Serial.println("=== UNIFORMITY TEST ===");
  Serial.println("Put ALL sensors in the SAME medium, same depth, and wait 60 s");
  Serial.println("for them to settle before trusting this.");
  Serial.println();

  float mean[NCH], sd[NCH];
  for (int c = 0; c < NCH; c++) {
    long sum = 0; long sq = 0;
    for (int r = 0; r < reps; r++) { int v = readRaw(PINS[c]); sum += v; sq += (long)v * v; delay(20); }
    mean[c] = (float)sum / reps;
    float var = (float)sq / reps - mean[c] * mean[c];
    sd[c] = var > 0 ? sqrt(var) : 0;
  }

  float lo = mean[0], hi = mean[0], tot = 0;
  for (int c = 0; c < NCH; c++) { lo = min(lo, mean[c]); hi = max(hi, mean[c]); tot += mean[c]; }
  float avg = tot / NCH;

  Serial.println("sensor   pin    mean raw     sd    deviation from group mean");
  for (int c = 0; c < NCH; c++) {
    float dev = 100.0 * (mean[c] - avg) / avg;
    Serial.printf("  S%-5d G%-5d %8.1f %6.1f   %+7.2f%%  %s\n",
                  c + 1, PINS[c], mean[c], sd[c], dev,
                  fabs(dev) > 5.0 ? "<-- OUTLIER" : "");
  }
  Serial.println();
  Serial.printf("group mean %.1f   spread %.0f counts (%.2f%% of mean)\n",
                avg, hi - lo, 100.0 * (hi - lo) / avg);
  Serial.println();
  Serial.println("READ THIS AS:  spread under ~2%% is good. Over ~5%% and your");
  Serial.println("pots are not on a common scale -- each sensor needs its OWN");
  Serial.println("calibration curve, not one shared curve for all nine.");
  Serial.println();
}

// --- (3) noise on one channel ---------------------------------------------
void noiseTest(int ch, int secs) {
  if (ch < 1 || ch > NCH) { Serial.println("bad channel"); return; }
  int pin = PINS[ch - 1];
  Serial.printf("=== NOISE TEST on S%d (GPIO%d) for %d s ===\n", ch, pin, secs);
  unsigned long t0 = millis();
  long n = 0, sum = 0; long sq = 0; int lo = 9999, hi = -1;
  while (millis() - t0 < (unsigned long)secs * 1000) {
    int v = readRaw(pin);
    sum += v; sq += (long)v * v; lo = min(lo, v); hi = max(hi, v); n++;
    delay(100);
  }
  float m = (float)sum / n;
  float var = (float)sq / n - m * m;
  Serial.printf("n=%ld  mean=%.1f  sd=%.2f  min=%d  max=%d  peak-to-peak=%d\n",
                n, m, var > 0 ? sqrt(var) : 0, lo, hi, hi - lo);
  Serial.println("peak-to-peak over ~30 counts in still soil = check your wiring,");
  Serial.println("shared ground, and that nothing is switching a relay nearby.");
}

// --- (4) calibration point logger -----------------------------------------
// Prints one CSV row you paste straight into your calibration spreadsheet.
void logPoint(String label) {
  Serial.print("CAL,");
  Serial.print(label);
  for (int c = 0; c < NCH; c++) { Serial.print(","); Serial.print(readRaw(PINS[c])); }
  for (int c = 0; c < NCH; c++) { Serial.print(","); Serial.print(readMv(PINS[c])); }
  Serial.println();
}

void printCalHeader() {
  Serial.print("CAL,label");
  for (int c = 0; c < NCH; c++) Serial.printf(",S%d_raw", c + 1);
  for (int c = 0; c < NCH; c++) Serial.printf(",S%d_mV", c + 1);
  Serial.println();
}

// ---------------------------------------------------------------------------
bool continuous = false;
String buf;

void help() {
  Serial.println();
  Serial.println("S            scan once");
  Serial.println("C            continuous scan (any key stops)");
  Serial.println("U            uniformity test -- all sensors in the SAME medium");
  Serial.println("N <ch> <s>   noise test on one channel for <s> seconds");
  Serial.println("H            print the calibration CSV header");
  Serial.println("L <label>    log one calibration row, e.g.  L gravimetric_18.4pct");
  Serial.println("?            this help");
  Serial.println();
}

void handle(String line) {
  line.trim();
  if (!line.length()) return;
  char c = toupper(line.charAt(0));
  if      (c == 'S') scanOnce(true);
  else if (c == 'C') { continuous = true; Serial.println("continuous -- send anything to stop"); scanOnce(true); }
  else if (c == 'U') uniformity(32);
  else if (c == 'H') printCalHeader();
  else if (c == 'L') logPoint(line.substring(1).length() ? line.substring(1) : " (unlabelled)");
  else if (c == 'N') {
    String a = line.substring(1); a.trim();
    int sp = a.indexOf(' ');
    int ch   = (sp > 0 ? a.substring(0, sp) : a).toInt();
    int secs = (sp > 0 ? a.substring(sp + 1).toInt() : 30);
    noiseTest(ch, secs ? secs : 30);
  }
  else help();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  analogReadResolution(ADC_BITS);
  for (int i = 0; i < NCH; i++) analogSetPinAttenuation(PINS[i], ADC_11db);  // full 0-3.3V
  Serial.println();
  Serial.println("=== Group B soil moisture sensor bench test ===");
  Serial.printf("%d channels:", NCH);
  for (int i = 0; i < NCH; i++) Serial.printf(" GPIO%d", PINS[i]);
  Serial.println();
  Serial.println("Sensors on 3.3V. All on the same rail. Wait 60 s after moving");
  Serial.println("a probe before believing the number.");
  help();
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (continuous) { continuous = false; Serial.println("stopped."); buf = ""; while (Serial.available()) Serial.read(); return; }
    if (ch == '\n' || ch == '\r') { if (buf.length()) { handle(buf); buf = ""; } }
    else { buf += ch; if (buf.length() > 48) buf = ""; }
  }
  if (continuous) { scanOnce(false); delay(500); }
}
