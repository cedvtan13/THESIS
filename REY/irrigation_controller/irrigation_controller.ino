/* ===========================================================================
 * ESP32-S3 Baseline Telemetry & Irrigation Controller
 * ---------------------------------------------------------------------------
 * Thesis : Computer Vision-Based Growth Monitoring and Yield Prediction for
 *          Pechay Under Differential Soil Moisture Treatments in a Greenhouse
 * Group  : Adag, Godinez, Tan  (USC Dept. of Computer Engineering, 2026)
 * Rev    : v2 -- re-checked against the 01 July 2026 endorsed manuscript
 *
 * SCOPE OF THIS FIRMWARE
 * ---------------------------------------------------------------------------
 * Runs on the ESP32-S3 ONLY. Per Section III and Fig. 4 / Fig. 6, the
 * ESP32-S3 is the "Baseline Telemetry & Irrigation Layer". The Raspberry Pi
 * Zero 2W runs only the cron vision pipeline and does not touch irrigation
 * hardware.
 *
 * Responsibilities:
 *   1. Poll 9 conformal-coated capacitive soil moisture sensors (1 per pot).
 *   2. Enforce the three treatment bands of Section III.A.3:
 *        Group A (P-01..P-03) Low      30-40 %
 *        Group B (P-04..P-06) Optimal  50-60 %
 *        Group C (P-07..P-09) High     70-80 %
 *   3. Drive 9 solenoid valves (1:1 per pot) plus the shared 12 V diaphragm
 *      pump, through the external driver stage shown in Appendix B, Fig. 7.
 *   4. Stream irrigation events and SM snapshots to the Raspberry Pi over
 *      UART. This is the data path Appendix G line 14 assumes ("Fetch
 *      localized Volumetric Water Content (SM) from ESP32 baseline log") and
 *      Appendix C step 7 draws, but which no section of the manuscript
 *      currently specifies a medium for. UART was chosen because it adds no
 *      BOM item and no network dependency.
 *   5. Detect sensor faults and report them -> Deliverable 7.
 *   6. Hold per-pot irrigation state in NVS so a brownout cannot cause
 *      double-watering -> Section III.G.1.
 *
 * Output maps onto the deliverables of Table I:
 *   EVT lines -> Deliverable 1 ("irrigation log (CSV) with timestamps,
 *                Pot ID, VWC, and pulse durations")
 *   SM  lines -> Deliverable 5 (SM column of the 315-row dataset)
 *   ERR lines -> Deliverable 7 (error log, reliability summary)
 *
 * WHY DOSE-AND-WAIT RATHER THAN WATER-UNTIL-TARGET
 * ---------------------------------------------------------------------------
 * Aala et al. (2022) measured that soil moisture needs roughly two hours to
 * redistribute before a reading is trustworthy, and Zamora et al. (2025)
 * carried that forward as a 2-hour interval between irrigation decisions. A
 * probe polled during watering therefore under-reports, and any "open the
 * valve until the sensor reaches the target" loop overshoots badly. This
 * firmware instead computes a millilitre dose from the measured deficit,
 * delivers it open-loop, and then locks that pot out for STABILIZATION_MS.
 *
 * NOTE FOR THE MANUSCRIPT: the current revision does not state a polling
 * interval or a stabilization window anywhere in Section III. Both constants
 * below are engineering choices that need to be written into the methodology
 * (or changed here to match whatever the methodology ends up saying).
 *
 * THREE CONSTANTS THAT MUST BE MEASURED BEFORE DEPLOYMENT
 * ---------------------------------------------------------------------------
 *  [1] dryADC[] / wetADC[] -- two-point calibration per sensor, Section III.E.1.
 *  [2] ML_PER_PERCENT      -- see the derivation note at that constant.
 *  [3] PUMP_FLOW_ML_PER_S  -- see the warning at that constant.
 *
 * Build target: Arduino IDE -> Tools -> Board -> "ESP32S3 Dev Module".
 * ("Arduino" is the C++ framework and toolchain, not a board.)
 * ========================================================================= */

#include <Preferences.h>

/* ---------------------------------------------------------------------------
 * PIN MAP -- must match the wiring schematic exactly.
 *
 * Avoided on ESP32-S3: GPIO 0/3/45/46 (strapping), 19/20 (USB D-/D+),
 * 26-32 (SPI flash), 33-37 (octal PSRAM), 43/44 (UART0 console), 48 (RGB LED
 * on most DevKitC-1 boards).
 *
 * Moisture sensors MUST sit on ADC1 (GPIO 1-10). ADC2 is shared with the
 * radio -- this is the same limitation Section III cites as the reason for
 * choosing the S3 over the original ESP32.
 * ------------------------------------------------------------------------- */
const int NUM_PODS = 9;

const int moistureSensorPins[NUM_PODS] = { 1,  2,  3,  4,  5,  6,  7,  8,  9};
const int solenoidPins[NUM_PODS]       = {11, 12, 13, 14, 15, 16, 21, 38, 39};
const int PUMP_PIN = 40;

// UART1 to the Raspberry Pi Zero 2W. Both boards are 3.3 V logic, so no level
// shifter is needed, but they MUST share a common ground.
//   ESP32 GPIO17 (TX) -> Pi GPIO15 / physical pin 10 (RXD)
//   ESP32 GPIO18 (RX) <- Pi GPIO14 / physical pin  8 (TXD)
const int PI_UART_TX = 17;
const int PI_UART_RX = 18;
HardwareSerial PiLink(1);

// Appendix B, Fig. 7 shows a "Relay Board / Solenoid Driver" block between
// the ESP32 GPIOs and the valves. Set this to true if that board switches on
// a LOW signal, which is the case for most inexpensive relay modules. Verify
// with a multimeter before connecting anything to water.
const bool RELAY_ACTIVE_LOW = false;

/* ---------------------------------------------------------------------------
 * TREATMENT GROUPS (Section III.A.3)
 * ------------------------------------------------------------------------- */
enum TreatmentGroup { GROUP_LOW = 0, GROUP_OPTIMAL = 1, GROUP_HIGH = 2 };

struct PodConfig {
  TreatmentGroup group;
  float lowerBound;   // irrigate when the reading falls below this
  float upperBound;   // top of the treatment band
};

PodConfig podConfig[NUM_PODS] = {
  {GROUP_LOW,     30.0f, 40.0f},   // P-01
  {GROUP_LOW,     30.0f, 40.0f},   // P-02
  {GROUP_LOW,     30.0f, 40.0f},   // P-03
  {GROUP_OPTIMAL, 50.0f, 60.0f},   // P-04
  {GROUP_OPTIMAL, 50.0f, 60.0f},   // P-05
  {GROUP_OPTIMAL, 50.0f, 60.0f},   // P-06
  {GROUP_HIGH,    70.0f, 80.0f},   // P-07
  {GROUP_HIGH,    70.0f, 80.0f},   // P-08
  {GROUP_HIGH,    70.0f, 80.0f}    // P-09
};

const char* groupName(TreatmentGroup g) {
  switch (g) {
    case GROUP_LOW:     return "A_Low";
    case GROUP_OPTIMAL: return "B_Optimal";
    default:            return "C_High";
  }
}

/* ---------------------------------------------------------------------------
 * SENSOR CALIBRATION -- PLACEHOLDERS. REPLACE AFTER BENCH CALIBRATION.
 * Capacitive probes read a HIGHER raw ADC value when the soil is DRIER.
 * ------------------------------------------------------------------------- */
int dryADC[NUM_PODS] = {3000, 3000, 3000, 3000, 3000, 3000, 3000, 3000, 3000};
int wetADC[NUM_PODS] = {1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200};

// Raw counts outside this window mean an open circuit, a shorted probe, or a
// detached sensor -- not a real soil condition.
const int ADC_FAULT_LOW  = 150;
const int ADC_FAULT_HIGH = 4000;

/* ---------------------------------------------------------------------------
 * HYDRAULIC CONSTANTS -- BOTH ARE PLACEHOLDERS. MEASURE THEM.
 * ------------------------------------------------------------------------- */

// Millilitres needed to raise one pot by one sensor-percent.
//
// IMPORTANT: because calibration is two-point (bone-dry = 0, saturated = 100),
// the "%" here is a relative saturation index, NOT true volumetric water
// content. You therefore cannot derive this from pot geometry -- 1 % of a
// 3.0 L pot is not 30 mL.
//
// Starting estimate: Zamora et al. measured 23.92 mL per 1 % for an 8000 g
// container (their Section 3.6.2). Section III.B of the current manuscript
// specifies 3.0 L pots, which at a plausible bulk density for the DA loam /
// compost / carbonized rice husk mix is roughly a third of that mass -- hence
// ~10 mL. The substrate composition differs from theirs, so replicate their
// drying-and-weighing procedure on one of your own pots and replace this.
const float ML_PER_PERCENT      = 10.0f;

// Flow through one open solenoid, measured at the emitter.
//
// WARNING: do NOT reuse Zamora et al.'s ~1 mL/s figure (their Table 3.1).
// Their system was GRAVITY-FED from an elevated 5-gallon container with no
// pump. The current manuscript's Appendix D specifies a 12 V diaphragm pump,
// so flow will be one to two orders of magnitude higher. 20 mL/s is a rough
// stand-in for a small diaphragm pump; measure yours into a beaker.
const float PUMP_FLOW_ML_PER_S  = 20.0f;

const float MAX_DOSE_ML         = 120.0f;  // hard ceiling per single event

/* ---------------------------------------------------------------------------
 * TIMING -- not currently specified in the manuscript; see header note.
 * ------------------------------------------------------------------------- */
const unsigned long SAMPLE_INTERVAL_MS    = 15UL * 60UL * 1000UL;  // 15 min
const unsigned long SM_REPORT_INTERVAL_MS = 30UL * 60UL * 1000UL;  // 30 min
const unsigned long STABILIZATION_MS      =  2UL * 60UL * 60UL * 1000UL; // 2 h

// Backstop against a badly wrong PUMP_FLOW_ML_PER_S. At the placeholder flow
// rate a maximum dose takes about 6 seconds, so 30 s is generous. Tighten it
// once the real flow rate is known.
const unsigned long MAX_PULSE_MS       = 30000UL;
const int  ADC_SAMPLES                 = 9;    // median filter window
const int  MAX_CONSECUTIVE_FAULTS      = 3;    // before a pot is quarantined

/* ---------------------------------------------------------------------------
 * RUNTIME STATE
 * ------------------------------------------------------------------------- */
Preferences prefs;

float         lastVWC[NUM_PODS];
unsigned long lastIrrigationEpoch[NUM_PODS];
uint32_t      irrigationCount[NUM_PODS];
int           consecutiveFaults[NUM_PODS];
bool          podQuarantined[NUM_PODS];

unsigned long lastSampleMs = 0;
unsigned long lastReportMs = 0;

// Wall-clock is owned by the Pi, which is always-on. It sends
// "TIME,<unix_epoch>"; we hold the offset so lockouts survive a reboot.
unsigned long epochAtBoot = 0;
bool          timeSynced  = false;

unsigned long nowEpoch() {
  return epochAtBoot + (millis() / 1000UL);
}

/* ---------------------------------------------------------------------------
 * DRIVER HELPERS
 * ------------------------------------------------------------------------- */
inline void driverOn(int pin)  { digitalWrite(pin, RELAY_ACTIVE_LOW ? LOW  : HIGH); }
inline void driverOff(int pin) { digitalWrite(pin, RELAY_ACTIVE_LOW ? HIGH : LOW ); }

/* ---------------------------------------------------------------------------
 * UART REPORTING -- the Pi timestamps and appends these to CSV.
 * ------------------------------------------------------------------------- */
void emit(const String& line) {
  PiLink.println(line);
  Serial.println(line);        // USB console, for bench debugging
}

void reportError(const char* code, const String& detail) {
  emit("ERR," + String(nowEpoch()) + "," + code + "," + detail);
}

/* ---------------------------------------------------------------------------
 * SENSOR READ -- median of N samples, with fault detection.
 * Returns -1.0 on fault.
 * ------------------------------------------------------------------------- */
int readRawMedian(int pin) {
  int s[ADC_SAMPLES];
  for (int i = 0; i < ADC_SAMPLES; i++) {
    s[i] = analogRead(pin);
    delay(5);
  }
  for (int i = 1; i < ADC_SAMPLES; i++) {       // insertion sort
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[ADC_SAMPLES / 2];
}

float readMoisturePercent(int pod) {
  int raw = readRawMedian(moistureSensorPins[pod]);

  if (raw < ADC_FAULT_LOW || raw > ADC_FAULT_HIGH) {
    consecutiveFaults[pod]++;
    reportError("SENSOR_RANGE",
                "P-0" + String(pod + 1) + ";raw=" + String(raw));
    if (consecutiveFaults[pod] >= MAX_CONSECUTIVE_FAULTS && !podQuarantined[pod]) {
      podQuarantined[pod] = true;
      reportError("POD_QUARANTINE",
                  "P-0" + String(pod + 1) + ";irrigation_suspended");
    }
    return -1.0f;
  }

  consecutiveFaults[pod] = 0;

  int span = dryADC[pod] - wetADC[pod];
  if (span == 0) {
    reportError("CAL_INVALID", "P-0" + String(pod + 1) + ";dry==wet");
    return -1.0f;
  }

  float pct = (float)(dryADC[pod] - raw) / (float)span * 100.0f;
  return constrain(pct, 0.0f, 100.0f);
}

/* ---------------------------------------------------------------------------
 * NVS PERSISTENCE (Section III.G.1)
 * ------------------------------------------------------------------------- */
void saveState(int pod) {
  String k = "p" + String(pod);
  prefs.putULong((k + "t").c_str(), lastIrrigationEpoch[pod]);
  prefs.putUInt ((k + "n").c_str(), irrigationCount[pod]);
}

void loadState() {
  for (int i = 0; i < NUM_PODS; i++) {
    String k = "p" + String(i);
    lastIrrigationEpoch[i] = prefs.getULong((k + "t").c_str(), 0);
    irrigationCount[i]     = prefs.getUInt ((k + "n").c_str(), 0);
    consecutiveFaults[i]   = 0;
    podQuarantined[i]      = false;
    lastVWC[i]             = -1.0f;
  }
}

/* ---------------------------------------------------------------------------
 * IRRIGATION -- one pot at a time, valve first, pump second.
 * ------------------------------------------------------------------------- */
void irrigatePod(int pod, float vwcBefore) {
  float target  = (podConfig[pod].lowerBound + podConfig[pod].upperBound) / 2.0f;
  float deficit = target - vwcBefore;
  if (deficit <= 0.0f) return;

  float doseMl = deficit * ML_PER_PERCENT;
  if (doseMl > MAX_DOSE_ML) doseMl = MAX_DOSE_ML;

  unsigned long pulseMs = (unsigned long)((doseMl / PUMP_FLOW_ML_PER_S) * 1000.0f);
  if (pulseMs > MAX_PULSE_MS) {
    pulseMs = MAX_PULSE_MS;
    reportError("PULSE_CLAMPED", "P-0" + String(pod + 1));
  }

  // Valve opens before the pump so the pump never runs against a closed line.
  driverOn(solenoidPins[pod]);
  delay(250);
  driverOn(PUMP_PIN);

  unsigned long t0 = millis();
  while (millis() - t0 < pulseMs) {
    delay(20);
  }

  // Pump stops before the valve closes, for the same reason.
  driverOff(PUMP_PIN);
  delay(250);
  driverOff(solenoidPins[pod]);

  irrigationCount[pod]++;
  lastIrrigationEpoch[pod] = nowEpoch();
  saveState(pod);

  emit("EVT," + String(nowEpoch()) +
       ",P-0" + String(pod + 1) +
       "," + groupName(podConfig[pod].group) +
       "," + String(vwcBefore, 1) +
       "," + String(target, 1) +
       "," + String(doseMl, 1) +
       "," + String(pulseMs) +
       "," + String(irrigationCount[pod]) +
       ",DOSED");
}

/* ---------------------------------------------------------------------------
 * SM SNAPSHOT -- the SM column of the 315-row training dataset.
 * ------------------------------------------------------------------------- */
void reportSM() {
  String line = "SM," + String(nowEpoch());
  for (int i = 0; i < NUM_PODS; i++) {
    line += "," + (lastVWC[i] < 0 ? String("NaN") : String(lastVWC[i], 1));
  }
  emit(line);
}

/* ---------------------------------------------------------------------------
 * COMMANDS FROM THE PI
 *   TIME,<unix_epoch>  -- clock handshake, sent by the Pi on its boot
 *   GET_SM             -- called at 12:00 to pair SM with that day's GPR
 *   PING               -- liveness check for the reliability summary
 *   STATUS             -- dump per-pot config and counters
 * ------------------------------------------------------------------------- */
void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.startsWith("TIME,")) {
    unsigned long e = strtoul(cmd.substring(5).c_str(), NULL, 10);
    if (e > 1700000000UL) {                       // sanity: after Nov 2023
      epochAtBoot = e - (millis() / 1000UL);
      timeSynced  = true;
      emit("ACK,TIME," + String(nowEpoch()));
    } else {
      reportError("TIME_INVALID", cmd);
    }
  }
  else if (cmd == "GET_SM") {
    for (int i = 0; i < NUM_PODS; i++) {
      if (!podQuarantined[i]) lastVWC[i] = readMoisturePercent(i);
    }
    reportSM();
  }
  else if (cmd == "PING") {
    emit("PONG," + String(nowEpoch()) + "," + String(millis() / 1000UL));
  }
  else if (cmd == "STATUS") {
    for (int i = 0; i < NUM_PODS; i++) {
      emit("STAT," + String(nowEpoch()) +
           ",P-0" + String(i + 1) +
           "," + groupName(podConfig[i].group) +
           "," + String(podConfig[i].lowerBound, 0) +
           "," + String(podConfig[i].upperBound, 0) +
           "," + (lastVWC[i] < 0 ? String("NaN") : String(lastVWC[i], 1)) +
           "," + String(irrigationCount[i]) +
           "," + String(lastIrrigationEpoch[i]) +
           "," + (podQuarantined[i] ? "QUARANTINED" : "OK"));
    }
  }
  else {
    reportError("UNKNOWN_CMD", cmd);
  }
}

void pollPiLink() {
  static String buf;
  while (PiLink.available()) {
    char c = (char)PiLink.read();
    if (c == '\n') { handleCommand(buf); buf = ""; }
    else if (c != '\r' && buf.length() < 96) { buf += c; }
  }

  // The same commands are accepted over the USB console, so the firmware can
  // be bench-tested from the Arduino Serial Monitor with no Pi attached --
  // type e.g. "TIME,1767225600" and press Enter.
  static String usbBuf;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') { handleCommand(usbBuf); usbBuf = ""; }
    else if (c != '\r' && usbBuf.length() < 96) { usbBuf += c; }
  }
}

/* ---------------------------------------------------------------------------
 * SETUP
 * ------------------------------------------------------------------------- */
void setup() {
  Serial.begin(115200);
  PiLink.begin(115200, SERIAL_8N1, PI_UART_RX, PI_UART_TX);
  delay(500);

  // Actuators OFF first, before anything else can glitch them.
  for (int i = 0; i < NUM_PODS; i++) {
    pinMode(solenoidPins[i], OUTPUT);
    driverOff(solenoidPins[i]);
  }
  pinMode(PUMP_PIN, OUTPUT);
  driverOff(PUMP_PIN);

  // 12-bit resolution, 11 dB attenuation -> roughly 0-3.1 V input range, which
  // matches the capacitive sensor's 0-3.0 V output swing.
  analogReadResolution(12);
  for (int i = 0; i < NUM_PODS; i++) {
    pinMode(moistureSensorPins[i], INPUT);
    analogSetPinAttenuation(moistureSensorPins[i], ADC_11db);
  }

  prefs.begin("irrigation", false);
  loadState();

  emit("BOOT," + String(millis()) + ",ESP32S3_IRRIGATION,v2,pods=" + String(NUM_PODS));
  emit("BOOT,awaiting TIME sync from Pi");
}

/* ---------------------------------------------------------------------------
 * MAIN LOOP
 * ------------------------------------------------------------------------- */
void loop() {
  pollPiLink();

  unsigned long now = millis();

  if (now - lastSampleMs >= SAMPLE_INTERVAL_MS || lastSampleMs == 0) {
    lastSampleMs = now;

    for (int i = 0; i < NUM_PODS; i++) {
      if (podQuarantined[i]) continue;

      float vwc = readMoisturePercent(i);
      lastVWC[i] = vwc;
      if (vwc < 0) continue;                       // faulted this pass

      // No irrigation until the Pi has supplied wall-clock time. An unsynced
      // clock makes the lockout arithmetic meaningless and risks double-
      // watering after a brownout. See the team briefing: if the Pi is down
      // for an extended period, water manually and record it in the deviation
      // log defined under Manual Intervention Constraints in Section I.G.
      if (!timeSynced) continue;

      unsigned long sinceLast = nowEpoch() - lastIrrigationEpoch[i];
      if (lastIrrigationEpoch[i] != 0 &&
          sinceLast < (STABILIZATION_MS / 1000UL)) {
        continue;
      }

      if (vwc < podConfig[i].lowerBound) {
        irrigatePod(i, vwc);
      }
      else if (vwc > podConfig[i].upperBound) {
        // Water cannot be removed; flag it so the excursion appears in the
        // reliability summary instead of silently biasing the SM column.
        reportError("ABOVE_BAND",
                    "P-0" + String(i + 1) + ";vwc=" + String(vwc, 1));
      }

      delay(200);                                  // stagger reads
    }
  }

  if (now - lastReportMs >= SM_REPORT_INTERVAL_MS) {
    lastReportMs = now;
    reportSM();
  }

  delay(100);
}
