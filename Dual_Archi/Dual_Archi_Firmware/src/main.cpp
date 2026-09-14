/* ===========================================================================
 * Dual-Target Baseline Telemetry & Irrigation Controller
 * ---------------------------------------------------------------------------
 * Target A: NodeMCU-32S (ESP-WROOM-32 38-Pin)
 * Target B: Custom PCB (ESP32-S3-WROOM-1)
 * ========================================================================= */

// Comment out this line to compile for your custom ESP32-S3 PCB!
#define USE_NODEMCU32S

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP3XX.h>
#include <Preferences.h>

const int NUM_PODS = 9;

/* ---------------------------------------------------------------------------
 * PIN DEFINITIONS & HARDWARE ROUTING
 * ------------------------------------------------------------------------- */
#ifdef USE_NODEMCU32S
  // --- Bench Testing: NodeMCU-32S (38-Pin ESP-WROOM-32) ---
  const int MUX_SIG    = 34;                // ADC1_CH6
  const int MUX_SEL[4] = {18, 19, 4, 5};    // S0, S1, S2, S3

  const int solenoidPins[NUM_PODS] = {32, 33, 25, 26, 27, 14, 13, 15, 23};
  const int PUMP_PIN      = 2;              // Relay 10: 12V Water Pump
  const int FAN_RELAY_PIN = 12;             // Relay 11: 5V Dual Pi Cooling Fans

  const int BMP_SDA = 21;
  const int BMP_SCL = 22;

  const int PI_UART_TX = 17;                // TX2 -> Pi Pin 10 (RXD)
  const int PI_UART_RX = 16;                // RX2 <- Pi Pin 8 (TXD)
  #define PiLink Serial2

  const int LED_INDICATOR_PIN = 2;          // Onboard LED
  const int PROG_BUTTON_PIN   = 0;          // Boot button

#else
  // --- Production: ESP32-S3 Custom PCB ---
  const int MUX_SIG    = 1;                 // ADC1_CH0 (PCB: io1)
  const int MUX_SEL[4] = {2, 3, 4, 5};      // S0->io2, S1->io3, S2->io4, S3->io5

  // Relays: io6 all the way to io16 (11 Relays total)
  // Relays 1-9: Solenoids P-01 to P-09
  const int solenoidPins[NUM_PODS] = {6, 7, 8, 9, 10, 11, 12, 13, 14};
  const int PUMP_PIN      = 15;             // Relay 10: 12V Water Pump (PCB: io15)
  const int FAN_RELAY_PIN = 16;             // Relay 11: 5V Pi Cooling Fans (PCB: io16)

  // BMP388 I2C Interface
  const int BMP_SDA = 41;                   // PCB: io41
  const int BMP_SCL = 40;                   // PCB: io40

  // Raspberry Pi UART Interface
  const int PI_UART_TX = 17;                // TX -> Pi Pin 10 (RXD)
  const int PI_UART_RX = 18;                // RX <- Pi Pin 8 (TXD)
  HardwareSerial PiLink(1);

  const int LED_INDICATOR_PIN = 21;         // PCB: io21
  const int PROG_BUTTON_PIN   = 38;         // PCB: io38
#endif

const bool RELAY_ACTIVE_LOW = true;

/* ---------------------------------------------------------------------------
 * TREATMENT GROUPS & GERMINATION LOGIC
 * ------------------------------------------------------------------------- */
enum TreatmentGroup { GROUP_LOW = 0, GROUP_OPTIMAL = 1, GROUP_HIGH = 2 };

struct PodConfig {
  TreatmentGroup group;
  float lowerBound;
  float upperBound;
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

bool  germinationMode        = true;
const float GERM_LOWER_BOUND = 50.0f;
const float GERM_UPPER_BOUND = 60.0f;

/* ---------------------------------------------------------------------------
 * CALIBRATION CONSTANTS//
 * ------------------------------------------------------------------------- */
int dryADC[NUM_PODS] = {2553, 2553, 2553, 2553, 2553, 2553, 2553, 2553, 2553};
int wetADC[NUM_PODS] = {1130, 1130, 1130, 1130, 1130, 1130, 1130, 1130, 1130};

const int ADC_FAULT_LOW  = 150;
const int ADC_FAULT_HIGH = 4000;

const float ML_PER_PERCENT     = 3.18f;     // Based on 318 mL total field capacity
const float PUMP_FLOW_ML_PER_S = 20.0f;     // Measured at 200 mL / 10 sec
const float MAX_DOSE_ML        = 100.0f;    // Capped at ~30% of total capacity

/* ---------------------------------------------------------------------------
 * ENCLOSURE THERMAL REGULATION (BMP388)
 * ------------------------------------------------------------------------- */
Adafruit_BMP3XX bmp;
bool  bmpAvailable      = false;
float currentTemp       = 0.0f;
float currentPressure   = 0.0f;
const float FAN_ON_TEMP = 35.0f;
const float FAN_OFF_TEMP= 32.0f;

/* ---------------------------------------------------------------------------
 * TIMING CONSTANTS
 * ------------------------------------------------------------------------- */
const unsigned long SAMPLE_INTERVAL_MS    = 15UL * 60UL * 1000UL;
const unsigned long SM_REPORT_INTERVAL_MS = 30UL * 60UL * 1000UL;
const unsigned long BMP_POLL_INTERVAL_MS  = 5UL * 1000UL;
const unsigned long STABILIZATION_MS      = 2UL * 60UL * 60UL * 1000UL;
const unsigned long MAX_PULSE_MS          = 30000UL;
const int  ADC_SAMPLES                    = 9;
const int  MAX_CONSECUTIVE_FAULTS         = 3;

Preferences prefs;

float         lastVWC[NUM_PODS];
unsigned long lastIrrigationEpoch[NUM_PODS];
uint32_t      irrigationCount[NUM_PODS];
int           consecutiveFaults[NUM_PODS];
bool          podQuarantined[NUM_PODS];

unsigned long lastSampleMs = 0;
unsigned long lastReportMs = 0;
unsigned long lastBmpMs    = 0;

unsigned long epochAtBoot = 0;
bool          timeSynced  = false;
volatile bool irrigating  = false;

void drainPiLink();

uint64_t millis64() {
  static uint32_t low32 = 0, high32 = 0;
  uint32_t now32 = millis();
  if (now32 < low32) high32++;
  low32 = now32;
  return ((uint64_t)high32 << 32) | low32;
}

unsigned long nowEpoch() { 
  return epochAtBoot + (unsigned long)(millis64() / 1000ULL); 
}

inline void relayOn(int pin)  { digitalWrite(pin, RELAY_ACTIVE_LOW ? LOW  : HIGH); }
inline void relayOff(int pin) { digitalWrite(pin, RELAY_ACTIVE_LOW ? HIGH : LOW ); }

void emit(const String& line) {
  PiLink.println(line);
  Serial.println(line);
}

void reportError(const char* code, const String& detail) {
  emit("ERR," + String(nowEpoch()) + "," + code + "," + detail);
}

void checkEnclosureThermal() {
  if (!bmpAvailable) return;
  if (!bmp.performReading()) {
    reportError("BMP_READ_FAIL", "I2C read failure");
    return;
  }
  currentTemp = bmp.temperature;
  currentPressure = bmp.pressure / 100.0F;

  if (currentTemp >= FAN_ON_TEMP) {
    relayOn(FAN_RELAY_PIN);
  } else if (currentTemp <= FAN_OFF_TEMP) {
    relayOff(FAN_RELAY_PIN);
  }
}

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
  for (int i = 1; i < ADC_SAMPLES; i++) {
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[ADC_SAMPLES / 2];
}

float readMoisturePercent(int pod) {
  int raw = readMuxMedian(pod);

  if (raw < ADC_FAULT_LOW || raw > ADC_FAULT_HIGH) {
    consecutiveFaults[pod]++;
    reportError("SENSOR_RANGE", "P-0" + String(pod + 1) + ";raw=" + String(raw));
    if (consecutiveFaults[pod] >= MAX_CONSECUTIVE_FAULTS && !podQuarantined[pod]) {
      podQuarantined[pod] = true;
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

void activeBand(int pod, float &lower, float &upper) {
  if (germinationMode) { lower = GERM_LOWER_BOUND; upper = GERM_UPPER_BOUND; }
  else                 { lower = podConfig[pod].lowerBound;
                         upper = podConfig[pod].upperBound; }
}

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
    podQuarantined[i]      = prefs.getBool((k + "q").c_str(), false);
    lastVWC[i]             = -1.0f;
  }
}

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

  irrigating = true;
  relayOn(solenoidPins[pod]);
  delay(250);
  relayOn(PUMP_PIN);

  unsigned long t0 = millis();
  while (millis() - t0 < pulseMs) {
    drainPiLink();
    delay(20);
  }

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

void reportSM() {
  String line = "SM," + String(nowEpoch());
  for (int i = 0; i < NUM_PODS; i++) {
    line += "," + (lastVWC[i] < 0 ? String("NaN") : String(lastVWC[i], 1));
  }
  emit(line);
}

void reportThermal() {
  emit("CLIM," + String(nowEpoch()) + "," + String(currentTemp, 1) + "," + String(currentPressure, 1));
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.startsWith("TIME,")) {
    unsigned long e = strtoul(cmd.substring(5).c_str(), NULL, 10);
    if (e > 1700000000UL) {
      epochAtBoot = e - (millis() / 1000UL);
      timeSynced  = true;
      emit("ACK,TIME," + String(nowEpoch()));
    } else {
      reportError("TIME_INVALID", cmd);
    }
  }
  else if (cmd == "GET_SM") {
    reportSM();
  }
  else if (cmd == "GET_CLIM") {
    reportThermal();
  }
  else if (cmd == "GET_SM_FRESH") {
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
    reportThermal();
  }
  else {
    reportError("UNKNOWN_CMD", cmd);
  }
}

#define CMD_QUEUE_DEPTH 4
String cmdQueue[CMD_QUEUE_DEPTH];
int    cmdQueueLen = 0;

void queueCommand(const String& c) {
  if (c.length() == 0) return;
  if (cmdQueueLen < CMD_QUEUE_DEPTH) cmdQueue[cmdQueueLen++] = c;
}

void drainPiLink() {
  static String buf, usbBuf;
  while (PiLink.available()) {
    char c = (char)PiLink.read();
    if (c == '\n') { queueCommand(buf); buf = ""; }
    else if (c != '\r' && buf.length() < 96) { buf += c; }
  }
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

void setup() {
  Serial.begin(115200);

  #ifdef USE_NODEMCU32S
    PiLink.begin(115200, SERIAL_8N1, PI_UART_RX, PI_UART_TX);
  #else
    PiLink.begin(115200, SERIAL_8N1, PI_UART_RX, PI_UART_TX);
  #endif

  delay(200);

  // Status LED & Programmable Button
  pinMode(LED_INDICATOR_PIN, OUTPUT);
  digitalWrite(LED_INDICATOR_PIN, LOW);
  pinMode(PROG_BUTTON_PIN, INPUT_PULLUP);

  // Relays: Initialize safe OFF state before enabling pin outputs
  for (int i = 0; i < NUM_PODS; i++) {
    digitalWrite(solenoidPins[i], RELAY_ACTIVE_LOW ? HIGH : LOW);
    pinMode(solenoidPins[i], OUTPUT);
    relayOff(solenoidPins[i]);
  }
  
  digitalWrite(PUMP_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(PUMP_PIN, OUTPUT);
  relayOff(PUMP_PIN);

  digitalWrite(FAN_RELAY_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(FAN_RELAY_PIN, OUTPUT);
  relayOff(FAN_RELAY_PIN);

  // MUX Select Lines
  for (int i = 0; i < 4; i++) {
    pinMode(MUX_SEL[i], OUTPUT);
    digitalWrite(MUX_SEL[i], LOW);
  }

  // ADC Setup
  analogReadResolution(12);
  pinMode(MUX_SIG, INPUT);
  #ifndef USE_NODEMCU32S
    analogSetPinAttenuation(MUX_SIG, ADC_11db);
  #endif

  // I2C BMP388
  Wire.begin(BMP_SDA, BMP_SCL);
  if (bmp.begin_I2C(0x76, &Wire)) {
    bmpAvailable = true;
    bmp.setTemperatureOversampling(BMP3_OVERSAMPLING_8X);
    bmp.setPressureOversampling(BMP3_OVERSAMPLING_4X);
    bmp.setIIRFilterCoeff(BMP3_IIR_FILTER_COEFF_3);
    bmp.setOutputDataRate(BMP3_ODR_50_HZ);
  } else {
    bmpAvailable = false;
  }

  prefs.begin("irrigation", false);
  loadState();

  #ifdef USE_NODEMCU32S
    emit("BOOT," + String(millis()) + ",NODEMCU32S_IRRIGATION,v4_compat,pods=" + String(NUM_PODS));
  #else
    emit("BOOT," + String(millis()) + ",ESP32S3_PCB_IRRIGATION,v4,pods=" + String(NUM_PODS));
  #endif

  emit(String("BOOT,bmp388=") + (bmpAvailable ? "ONLINE" : "OFFLINE"));
  emit(String("BOOT,germination_mode=") + (germinationMode ? "ON" : "OFF"));
  emit("BOOT,awaiting TIME sync from Pi");

  // Visual indication that boot is complete
  digitalWrite(LED_INDICATOR_PIN, HIGH);
}

void loop() {
  pollPiLink();

  unsigned long now = millis();

  if (now - lastBmpMs >= BMP_POLL_INTERVAL_MS || lastBmpMs == 0) {
    lastBmpMs = now;
    checkEnclosureThermal();
  }

  if (now - lastSampleMs >= SAMPLE_INTERVAL_MS || lastSampleMs == 0) {
    lastSampleMs = now;

    for (int i = 0; i < NUM_PODS; i++) {
      if (podQuarantined[i]) continue;

      float vwc = readMoisturePercent(i);
      lastVWC[i] = vwc;
      if (vwc < 0) continue;

      if (!timeSynced) continue;

      unsigned long sinceLast = nowEpoch() - lastIrrigationEpoch[i];
      if (lastIrrigationEpoch[i] != 0 &&
          sinceLast < (STABILIZATION_MS / 1000UL)) continue;

      float lo, hi; activeBand(i, lo, hi);

      if (vwc < lo) {
        irrigatePod(i, vwc);
      } else if (vwc > hi) {
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