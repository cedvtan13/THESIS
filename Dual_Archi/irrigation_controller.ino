/* ===========================================================================
 * ESP32-S3 Baseline Telemetry & Irrigation Controller
 * ---------------------------------------------------------------------------
 * Thesis : Computer Vision-Based Growth Monitoring and Yield Prediction for
 *          Pechay Under Differential Soil Moisture Treatments in a Greenhouse
 * Group  : Adag, Godinez, Tan  (USC Dept. of Computer Engineering, 2026)
 * Board  : ESP32-S3 (Tools > Board > "ESP32S3 Dev Module")
 * Rev    : v4 -- ESP32-S3 + CD74HC4067 multiplexer + 8ch/2ch relay modules
 *          v4 changes: rollover-safe clock, quarantine no longer reports
 *          stale moisture, GET_SM answers from cache so it cannot time out
 *          mid-irrigation, quarantine persisted to NVS, CLEAR_FAULTS added.
 *
 * ROLE
 * ---------------------------------------------------------------------------
 * Runs on the ESP32-S3 ONLY. Per Section III and Fig. 4 / Fig. 6, the
 * ESP32-S3 is the "Baseline Telemetry & Irrigation Layer" and owns every
 * irrigation decision. The Raspberry Pi Zero 2W runs only the cron vision
 * pipeline and touches no irrigation hardware. If the Pi dies, watering
 * continues; if the ESP32 dies, watering stops. That asymmetry is deliberate.
 *
 * Responsibilities
 *   1. Read 9 capacitive sensors through ONE ADC pin via a CD74HC4067 mux.
 *   2. Enforce the three treatment bands of Section III.A.3:
 *        Group A (P-01..P-03) Low      30-40 %
 *        Group B (P-04..P-06) Optimal  50-60 %
 *        Group C (P-07..P-09) High     70-80 %
 *   3. Drive 9 solenoid valves + 1 shared pump via two relay modules.
 *   4. Stream SM snapshots and irrigation events to the Pi over UART1.
 *      This is the data path Appendix G line 14 assumes ("Fetch localized
 *      Volumetric Water Content (SM) from ESP32 baseline log").
 *   5. Detect sensor faults and quarantine bad pots  -> Deliverable 7.
 *   6. Hold per-pot state in NVS so a brownout cannot double-water
 *      -> Section III.G.1.
 *
 * Output maps to Table I:
 *   EVT -> Deliverable 1   SM -> Deliverable 5   ERR -> Deliverable 7
 *
 * WHY DOSE-AND-WAIT, NOT WATER-UNTIL-TARGET
 * ---------------------------------------------------------------------------
 * Aala et al. (2022) measured that soil needs roughly two hours to
 * redistribute before a reading is trustworthy; Zamora et al. (2025) carried
 * that forward as a 2-hour interval. A probe polled DURING watering
 * under-reports, so any "open the valve until the sensor reads target" loop
 * overshoots badly. This firmware computes a millilitre dose from the
 * measured deficit, delivers it open-loop, then locks the pot out for
 * STABILIZATION_MS.
 *
 * THREE CONSTANTS THAT MUST BE MEASURED FIRST
 *   [1] dryADC[] / wetADC[]   two-point calibration, Section III.E.1
 *   [2] ML_PER_PERCENT        see note at the constant
 *   [3] PUMP_FLOW_ML_PER_S    see warning at the constant
 * Until these are real numbers the firmware will run and water incorrectly.
 * ========================================================================= */

#include <Preferences.h>

/* ---------------------------------------------------------------------------
 * PIN MAP -- ESP32-S3. Must match the wiring table exactly.
 *
 * Avoided on the S3: GPIO 0/3/45/46 (strapping), 19/20 (USB D-/D+),
 * 26-32 (SPI flash), 33-37 (octal PSRAM on N8R8/N16R8 parts),
 * 43/44 (UART0 console), 48 (onboard RGB LED).
 *
 * The mux SIG line MUST sit on ADC1 (GPIO 1-10). ADC2 is shared with the
 * radio and cannot be read while Wi-Fi is up -- the same limitation
 * Section III cites as the reason for choosing the S3.
 * ------------------------------------------------------------------------- */
const int NUM_PODS = 9;

// --- CD74HC4067 16-channel analog multiplexer ---
const int MUX_SIG    = 4;                  // ADC1_CH3, analog input
const int MUX_SEL[4] = {5, 6, 7, 15};      // S0, S1, S2, S3
// MUX EN -> GND (permanently enabled).  MUX VCC -> 3V3.
// Sensors occupy channels C0..C8 = pots P-01..P-09.  C9..C15 spare.

// --- Relay control (both modules are ACTIVE-LOW) ---
// 8-channel module IN1..IN8 -> pots P-01..P-08
// 2-channel module IN1      -> pot  P-09
// 2-channel module IN2      -> shared pump
const int solenoidPins[NUM_PODS] = {16, 21, 38, 39, 40, 41, 42, 8, 9};
const int PUMP_PIN = 10;

// --- UART1 to the Raspberry Pi Zero 2W ---
//   ESP32 GPIO17 (TX) -> Pi GPIO15 / physical pin 10 (RXD)
//   ESP32 GPIO18 (RX) <- Pi GPIO14 / physical pin  8 (TXD)
//   GND <-> Pi pin 6.  Both are 3.3 V logic: no level shifter, but the
//   common ground is mandatory.
const int PI_UART_TX = 17;
const int PI_UART_RX = 18;
HardwareSerial PiLink(1);

// Both the 8-channel and 2-channel modules in use switch on a LOW signal.
// Verify with a multimeter before connecting anything to water.
const bool RELAY_ACTIVE_LOW = true;

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
 * GERMINATION WINDOW (Section III.A, uniform-germination insertion)
 * ---------------------------------------------------------------------------
 * All nine pots are held at a uniform moisture level from sowing until
 * emergence; the three differential bands are enforced only from the
 * completion of emergence onward. Set GERMINATION_MODE true at sowing and
 * send "BANDS_ON" once every pot has emerged.
 * ------------------------------------------------------------------------- */
bool  germinationMode        = true;
const float GERM_LOWER_BOUND = 50.0f;   // uniform band during germination
const float GERM_UPPER_BOUND = 60.0f;

/* ---------------------------------------------------------------------------
 * SENSOR CALIBRATION -- PLACEHOLDERS. REPLACE AFTER BENCH CALIBRATION.
 * Capacitive probes read a HIGHER raw ADC value when the soil is DRIER.
 * ------------------------------------------------------------------------- */
int dryADC[NUM_PODS] = {3000, 3000, 3000, 3000, 3000, 3000, 3000, 3000, 3000};
int wetADC[NUM_PODS] = {1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200};

// Raw counts outside this window mean an open circuit, a shorted probe, a
// detached sensor, or a mux channel that is not switching.
const int ADC_FAULT_LOW  = 150;
const int ADC_FAULT_HIGH = 4000;

/* ---------------------------------------------------------------------------
 * HYDRAULIC CONSTANTS -- BOTH ARE PLACEHOLDERS. MEASURE THEM.
 * ------------------------------------------------------------------------- */

// Millilitres needed to raise one pot by one sensor-percent.
//
// IMPORTANT: because calibration is two-point (bone-dry = 0, saturated = 100),
// this "%" is a RELATIVE SATURATION INDEX, not true volumetric water content.
// You therefore cannot derive this from pot geometry -- 1 % of a 3.0 L pot is
// NOT 30 mL. Zamora et al. measured 23.92 mL per 1 % for an 8000 g container
// (their Section 3.6.2); scaled to the 3.0 L pots of Section III.B this is
// roughly 10 mL. Replicate their drying-and-weighing procedure on one of your
// own pots and replace this number.
const float ML_PER_PERCENT = 10.0f;

// Flow through ONE open solenoid, measured at the emitter.
//
// WARNING: do NOT reuse Zamora et al.'s ~1 mL/s figure. Their system was
// GRAVITY-FED from an elevated container with no pump. Appendix D of the
// current manuscript specifies a 12 V diaphragm pump, so flow will be one to
// two orders of magnitude higher. 20 mL/s is a stand-in; measure yours into a
// beaker (Stage 5 of the test plan).
const float PUMP_FLOW_ML_PER_S = 20.0f;

const float MAX_DOSE_ML = 120.0f;   // hard ceiling per single event

/* ---------------------------------------------------------------------------
 * TIMING
 * ------------------------------------------------------------------------- */
const unsigned long SAMPLE_INTERVAL_MS    = 15UL * 60UL * 1000UL;        // 15 min
const unsigned long SM_REPORT_INTERVAL_MS = 30UL * 60UL * 1000UL;        // 30 min
const unsigned long STABILIZATION_MS      = 2UL * 60UL * 60UL * 1000UL;  //  2 h
const unsigned long MAX_PULSE_MS          = 30000UL;   // backstop, see note
const int  ADC_SAMPLES            = 9;   // median filter window
const int  MAX_CONSECUTIVE_FAULTS = 3;   // strikes before quarantine

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
// "TIME,<unix_epoch>"; we hold the offset so the 2 h lockout survives a reboot.
unsigned long epochAtBoot = 0;
bool          timeSynced  = false;

/* millis() wraps at ~49.7 days. The grow-out plus bench testing can approach
 * that, and a wrap would make the 2 h lockout arithmetic underflow and permit
 * an immediate re-water. Track the wrap explicitly. */
uint64_t millis64() {
  static uint32_t low32 = 0, high32 = 0;
  uint32_t now32 = millis();
  if (now32 < low32) high32++;          // wrapped
  low32 = now32;
  return ((uint64_t)high32 << 32) | low32;
}

unsigned long nowEpoch() { return epochAtBoot + (unsigned long)(millis64() / 1000ULL); }

// True while a valve is open. GET_SM reports this so the Pi can tell that a
// reading was taken next to an active irrigation event.
volatile bool irrigating = false;

void drainPiLink();   // forward decl: used inside irrigatePod()

/* ---------------------------------------------------------------------------
 * RELAY HELPERS
 * ------------------------------------------------------------------------- */
inline void relayOn(int pin)  { digitalWrite(pin, RELAY_ACTIVE_LOW ? LOW  : HIGH); }
inline void relayOff(int pin) { digitalWrite(pin, RELAY_ACTIVE_LOW ? HIGH : LOW ); }

/* ---------------------------------------------------------------------------
 * REPORTING -- the Pi timestamps these and appends them to CSV
 * ------------------------------------------------------------------------- */
void emit(const String& line) {
  PiLink.println(line);
  Serial.println(line);          // USB console, for bench work
}

void reportError(const char* code, const String& detail) {
  emit("ERR," + String(nowEpoch()) + "," + code + "," + detail);
}

/* ---------------------------------------------------------------------------
 * MULTIPLEXER READ
 * ---------------------------------------------------------------------------
 * Sets the 4 select lines to the binary channel address, waits for the
 * analog line to settle, then reads. The settle delay matters: without it
 * you read the tail of the previous channel.
 * ------------------------------------------------------------------------- */
int readMuxRaw(int channel) {
  for (int i = 0; i < 4; i++) {
    digitalWrite(MUX_SEL[i], (channel >> i) & 0x01);
  }
  delayMicroseconds(50);
  return analogRead(MUX_SIG);
}

int readMuxMedian(int channel) {
  int s[ADC_SAMPLES];
  for (int i = 0; i < ADC_SAMPLES; i++) {
    s[i] = readMuxRaw(channel);
    delay(2);
  }
  for (int i = 1; i < ADC_SAMPLES; i++) {          // insertion sort
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[ADC_SAMPLES / 2];
}

/* Returns percent, or -1.0 on fault. */
float readMoisturePercent(int pod) {
  int raw = readMuxMedian(pod);                    // channel == pod index

  if (raw < ADC_FAULT_LOW || raw > ADC_FAULT_HIGH) {
    consecutiveFaults[pod]++;
    reportError("SENSOR_RANGE", "P-0" + String(pod + 1) + ";raw=" + String(raw));
    if (consecutiveFaults[pod] >= MAX_CONSECUTIVE_FAULTS && !podQuarantined[pod]) {
      podQuarantined[pod] = true;
      // Clear the cached value. Without this the pot keeps reporting its last
      // good reading forever and a dead sensor silently writes plausible
      // numbers into the SM column of the dataset.
      lastVWC[pod] = -1.0f;
      prefs.putBool(("p" + String(pod) + "q").c_str(), true);
      reportError("POD_QUARANTINE", "P-0" + String(pod + 1) + ";irrigation_suspended");
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
 * ACTIVE BAND -- uniform during germination, differential afterwards
 * ------------------------------------------------------------------------- */
void activeBand(int pod, float &lower, float &upper) {
  if (germinationMode) { lower = GERM_LOWER_BOUND; upper = GERM_UPPER_BOUND; }
  else                 { lower = podConfig[pod].lowerBound;
                         upper = podConfig[pod].upperBound; }
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
  germinationMode = prefs.getBool("germ", true);
  for (int i = 0; i < NUM_PODS; i++) {
    String k = "p" + String(i);
    lastIrrigationEpoch[i] = prefs.getULong((k + "t").c_str(), 0);
    irrigationCount[i]     = prefs.getUInt ((k + "n").c_str(), 0);
    consecutiveFaults[i]   = 0;
    // Quarantine survives a reboot. A physically dead sensor must not quietly
    // return to service every time the board resets; clear it deliberately
    // with CLEAR_FAULTS once the probe has actually been repaired.
    podQuarantined[i]      = prefs.getBool((k + "q").c_str(), false);
    lastVWC[i]             = -1.0f;
  }
}

/* ---------------------------------------------------------------------------
 * IRRIGATION -- one pot at a time. Valve opens first, pump stops first.
 * ------------------------------------------------------------------------- */
void irrigatePod(int pod, float vwcBefore) {
  float lower, upper;
  activeBand(pod, lower, upper);

  float target  = (lower + upper) / 2.0f;
  float deficit = target - vwcBefore;
  if (deficit <= 0.0f) return;

  float doseMl = deficit * ML_PER_PERCENT;
  if (doseMl > MAX_DOSE_ML) doseMl = MAX_DOSE_ML;

  unsigned long pulseMs = (unsigned long)((doseMl / PUMP_FLOW_ML_PER_S) * 1000.0f);
  if (pulseMs > MAX_PULSE_MS) {
    pulseMs = MAX_PULSE_MS;
    reportError("PULSE_CLAMPED", "P-0" + String(pod + 1));
  }

  // Valve before pump, so the pump never runs against a closed line.
  irrigating = true;
  relayOn(solenoidPins[pod]);
  delay(250);
  relayOn(PUMP_PIN);

  // Keep draining the UART while the valve is open. The pulse blocks the main
  // loop, and without this the Pi's bytes would sit unread until it finished
  // -- long enough for the noon GET_SM to time out. Commands are buffered
  // here and executed after the valve closes, never during watering.
  unsigned long t0 = millis();
  while (millis() - t0 < pulseMs) {
    drainPiLink();
    delay(20);
  }

  // Pump before valve on the way down, for the same reason.
  relayOff(PUMP_PIN);
  delay(250);
  relayOff(solenoidPins[pod]);
  irrigating = false;

  irrigationCount[pod]++;
  lastIrrigationEpoch[pod] = nowEpoch();
  saveState(pod);

  emit("EVT," + String(nowEpoch()) +
       ",P-0" + String(pod + 1) +
       "," + (germinationMode ? "GERM_UNIFORM" : groupName(podConfig[pod].group)) +
       "," + String(vwcBefore, 1) +
       "," + String(target, 1) +
       "," + String(doseMl, 1) +
       "," + String(pulseMs) +
       "," + String(irrigationCount[pod]) +
       ",DOSED");
}

/* ---------------------------------------------------------------------------
 * SM SNAPSHOT -- the SM column of the 315-row dataset (Deliverable 5)
 * ------------------------------------------------------------------------- */
void reportSM() {
  // Field count is fixed at 11 (SM + epoch + 9 pots) because pi_link.py
  // validates on it. Quarantined or faulted pots emit NaN, never a stale value.
  String line = "SM," + String(nowEpoch());
  for (int i = 0; i < NUM_PODS; i++) {
    line += "," + (lastVWC[i] < 0 ? String("NaN") : String(lastVWC[i], 1));
  }
  emit(line);
}

/* ---------------------------------------------------------------------------
 * COMMANDS FROM THE PI
 *   TIME,<unix_epoch>  clock handshake, sent by the Pi on boot and hourly
 *   GET_SM             called at 12:00 to pair SM with that day's GPR
 *   PING               liveness check for the reliability summary
 *   STATUS             dump per-pot config and counters
 *   BANDS_ON           end germination mode, enforce differential bands
 *   BANDS_OFF          return to uniform germination band
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
    // Answer from the most recent scheduled sample rather than forcing a fresh
    // read. Three reasons: it returns instantly so it cannot time out while the
    // loop is busy; it never samples a pot that was just watered, which is the
    // whole point of dose-and-wait; and the cache is at most SAMPLE_INTERVAL_MS
    // (15 min) old, which is well inside the soil's response time.
    reportSM();
  }
  else if (cmd == "GET_SM_FRESH") {
    // Bench/diagnostic use only. Do not call this during a grow-out: it reads
    // the probes on demand, including pots inside their stabilisation window.
    if (irrigating) {
      reportError("BUSY", "irrigation_in_progress");
    } else {
      for (int i = 0; i < NUM_PODS; i++) {
        if (!podQuarantined[i]) lastVWC[i] = readMoisturePercent(i);
      }
      reportSM();
    }
  }
  else if (cmd == "CLEAR_FAULTS") {
    for (int i = 0; i < NUM_PODS; i++) {
      podQuarantined[i]    = false;
      consecutiveFaults[i] = 0;
      prefs.putBool(("p" + String(i) + "q").c_str(), false);
    }
    emit("ACK,CLEAR_FAULTS," + String(nowEpoch()));
  }
  else if (cmd == "PING") {
    emit("PONG," + String(nowEpoch()) + "," + String(millis() / 1000UL));
  }
  else if (cmd == "BANDS_ON") {
    germinationMode = false;
    prefs.putBool("germ", false);
    emit("ACK,BANDS_ON," + String(nowEpoch()));
  }
  else if (cmd == "BANDS_OFF") {
    germinationMode = true;
    prefs.putBool("germ", true);
    emit("ACK,BANDS_OFF," + String(nowEpoch()));
  }
  else if (cmd == "STATUS") {
    for (int i = 0; i < NUM_PODS; i++) {
      float lo, hi; activeBand(i, lo, hi);
      emit("STAT," + String(nowEpoch()) +
           ",P-0" + String(i + 1) +
           "," + (germinationMode ? "GERM_UNIFORM" : groupName(podConfig[i].group)) +
           "," + String(lo, 0) + "," + String(hi, 0) +
           "," + (lastVWC[i] < 0 ? String("NaN") : String(lastVWC[i], 1)) +
           "," + String(irrigationCount[i]) +
           "," + String(lastIrrigationEpoch[i]) +
           "," + (podQuarantined[i] ? "QUARANTINED" : "OK") +
           "," + (irrigating ? "IRRIGATING" : "IDLE"));
    }
  }
  else {
    reportError("UNKNOWN_CMD", cmd);
  }
}

// Pending commands, filled by drainPiLink() and executed by pollPiLink().
// Depth 4 is ample: the Pi sends at most TIME + GET_SM in a burst.
#define CMD_QUEUE_DEPTH 4
String cmdQueue[CMD_QUEUE_DEPTH];
int    cmdQueueLen = 0;

void queueCommand(const String& c) {
  if (c.length() == 0) return;
  if (cmdQueueLen < CMD_QUEUE_DEPTH) cmdQueue[cmdQueueLen++] = c;
  // Silently dropping past depth is correct here: the Pi retries, and we must
  // never block inside an irrigation pulse.
}

/* Read bytes off both links into the queue WITHOUT executing anything.
 * Safe to call from inside an irrigation pulse. */
void drainPiLink() {
  static String buf, usbBuf;
  while (PiLink.available()) {
    char c = (char)PiLink.read();
    if (c == '\n') { queueCommand(buf); buf = ""; }
    else if (c != '\r' && buf.length() < 96) { buf += c; }
  }
  // The same commands are accepted over USB so the firmware can be bench
  // tested from the Arduino Serial Monitor with no Pi attached.
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') { queueCommand(usbBuf); usbBuf = ""; }
    else if (c != '\r' && usbBuf.length() < 96) { usbBuf += c; }
  }
}

void pollPiLink() {
  drainPiLink();
  for (int i = 0; i < cmdQueueLen; i++) handleCommand(cmdQueue[i]);
  cmdQueueLen = 0;
}

/* ---------------------------------------------------------------------------
 * SETUP
 * ------------------------------------------------------------------------- */
void setup() {
  Serial.begin(115200);
  PiLink.begin(115200, SERIAL_8N1, PI_UART_RX, PI_UART_TX);
  delay(500);

  // Drive every relay pin to its OFF level BEFORE switching it to an output.
  // Doing it the other way round makes all ten relays click on at reset.
  for (int i = 0; i < NUM_PODS; i++) {
    digitalWrite(solenoidPins[i], RELAY_ACTIVE_LOW ? HIGH : LOW);
    pinMode(solenoidPins[i], OUTPUT);
    relayOff(solenoidPins[i]);
  }
  digitalWrite(PUMP_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(PUMP_PIN, OUTPUT);
  relayOff(PUMP_PIN);

  for (int i = 0; i < 4; i++) {
    pinMode(MUX_SEL[i], OUTPUT);
    digitalWrite(MUX_SEL[i], LOW);
  }

  // 12-bit resolution, 11 dB attenuation -> ~0-3.1 V range, matching the
  // capacitive sensor's 0-3.0 V output swing.
  analogReadResolution(12);
  pinMode(MUX_SIG, INPUT);
  analogSetPinAttenuation(MUX_SIG, ADC_11db);

  prefs.begin("irrigation", false);
  loadState();

  emit("BOOT," + String(millis()) + ",ESP32S3_IRRIGATION,v4,pods=" + String(NUM_PODS));
  emit(String("BOOT,germination_mode=") + (germinationMode ? "ON" : "OFF"));
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
      if (vwc < 0) continue;                    // faulted this pass

      // No irrigation until the Pi has supplied wall-clock time: an unsynced
      // clock makes the lockout arithmetic meaningless and risks
      // double-watering after a brownout. If the Pi is down for an extended
      // period, water by hand and record it in the deviation log defined
      // under Manual Intervention Constraints in Section I.G.
      if (!timeSynced) continue;

      unsigned long sinceLast = nowEpoch() - lastIrrigationEpoch[i];
      if (lastIrrigationEpoch[i] != 0 &&
          sinceLast < (STABILIZATION_MS / 1000UL)) continue;

      float lo, hi; activeBand(i, lo, hi);

      if (vwc < lo) {
        irrigatePod(i, vwc);
      } else if (vwc > hi) {
        // Water cannot be removed. Flag the excursion so it appears in the
        // reliability summary instead of silently biasing the SM column.
        reportError("ABOVE_BAND", "P-0" + String(i + 1) + ";vwc=" + String(vwc, 1));
      }

      delay(200);
    }
  }

  if (now - lastReportMs >= SM_REPORT_INTERVAL_MS) {
    lastReportMs = now;
    reportSM();
  }

  delay(100);
}
