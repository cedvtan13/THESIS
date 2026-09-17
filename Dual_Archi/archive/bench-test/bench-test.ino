  /*
  bench_test.ino -- ESP32 bench test firmware for Group B.
  Talks to the Pi over UART using the same line/CSV protocol family as the
  production firmware, so what you prove here transfers.

  TESTS, in the order you should run them:
    1. PING/PONG      -- is the UART link alive at all?
    2. SM / UNIFORM   -- do the nine moisture sensors read, and do they agree?
    3. RELAY / PULSE  -- does each solenoid and the pump actually switch?

  SAFETY -- this drives 12 V into pots of soil. Four interlocks:
    * Boot-safe init: the OFF level is latched BEFORE pinMode(), so a relay
      cannot click on during the power-up glitch.
    * Per-relay auto-off: anything left on longer than MAX_ON_MS shuts itself
      off and reports it. A crashed Pi cannot flood a pot.
    * Link watchdog: if the Pi goes quiet for LINK_TIMEOUT_MS while any relay
      is on, everything shuts off.
    * One solenoid at a time, and the pump refuses to run with every valve
      closed (never pump against a closed line).

  WIRING -- RELAY_PINS below is taken from Dual_Archi_Firmware/src/main.cpp.
    Relays are ACTIVE LOW (SONGLE opto boards).

  !! PIN CONFLICT IN THE PRODUCTION FIRMWARE -- not introduced here.
     In the USE_NODEMCU32S block of main.cpp:
         PUMP_PIN          = 2;    (line 28)
         LED_INDICATOR_PIN = 2;    (line 38)
     Same pin. Relays are active LOW, so main.cpp line 438
         digitalWrite(LED_INDICATOR_PIN, LOW);
     energises the PUMP RELAY, and line 495
         digitalWrite(LED_INDICATOR_PIN, HIGH);
     releases it. Today the window between them is only the solenoid pinMode
     loop, so the pump barely twitches -- but the moment anyone uses that LED
     to blink a status code, it becomes a pump that runs itself.
     Fix in main.cpp: give the NodeMCU build LED_INDICATOR_PIN = -1 (or any
     free pin) and guard every digitalWrite to it. This sketch does not touch
     an LED at all, so the bench test is unaffected either way.
    Remove the JD-VCC/VCC jumper: JD-VCC<-5V, VCC<-3.3V, GND<-ESP32 GND.
    Flyback diode (1N4007) across the pump AND across each solenoid,
    banded end to +12V.

  UART to the Pi:
    ESP32 TX -> Pi GPIO15 / physical pin 10 (RXD)
    ESP32 RX <- Pi GPIO14 / physical pin  8 (TXD)
    GND <-> Pi pin 6   -- mandatory
*/

#include <Arduino.h>

// ---------------------------------------------------------------- board ----
#define USE_NODEMCU32S            // comment out when the ESP32-S3 arrives

#ifdef USE_NODEMCU32S
  const int UART_TX = 17;                    // UART2
  const int UART_RX = 16;
  const int MUX_SIG    = 34;                 // ADC1_CH6
  const int MUX_SEL[4] = {18, 19, 4, 5};     // S0..S3
  // index 0 = pump, 1..9 = solenoid for P-01..P-09.
  // Copied VERBATIM from Dual_Archi_Firmware/src/main.cpp lines 27-28:
  //   solenoidPins[9] = {32, 33, 25, 26, 27, 14, 13, 15, 23};
  //   PUMP_PIN        = 2;
  // The solenoid ORDER is load-bearing: index i must be the valve that feeds
  // pot P-0(i). Reshuffling it waters the wrong pot and silently destroys the
  // treatment assignment. Verify against the physical wiring with --sweep.
  //
  // GPIO12 is NOT in this list. It is FAN_RELAY_PIN (main.cpp line 29) and is
  // also a strapping pin (MTDI: held high at boot sets flash to 1.8 V and the
  // board may not start). Leave it out of the relay walk.
  //
  // GPIO2 (pump) is ALSO declared as LED_INDICATOR_PIN in main.cpp line 38 --
  // see the note in the header. It is a strapping pin too. Confirm the ESP32
  // still boots with the relay board powered before trusting any of this.
  int RELAY_PINS[10] = {2, 32, 33, 25, 26, 27, 14, 13, 15, 23};
#else
  const int UART_TX = 17;
  const int UART_RX = 18;
  const int MUX_SIG    = 1;
  const int MUX_SEL[4] = {2, 3, 4, 5};
  // From main.cpp lines 48-49: solenoidPins = {6..14}, PUMP_PIN = 15.
  int RELAY_PINS[10] = {15, 6, 7, 8, 9, 10, 11, 12, 13, 14};
#endif

const bool RELAY_ACTIVE_LOW = true;
const int  NUM_PODS   = 9;
const int  NUM_RELAYS = 10;          // 0 = pump, 1..9 = solenoids

// ---- calibration: your measured endpoints ---------------------------------
// dryADC = oven-dried soil (theta_v = 0). wetADC = wetted + drained 8 h
// (= container capacity, NOT 100 % VWC). So this reports PERCENT OF CONTAINER
// CAPACITY. Multiply by CC/100 offline to get true VWC.
int dryADC[NUM_PODS] = {2553, 2553, 2553, 2553, 2553, 2553, 2553, 2553, 2553};
int wetADC[NUM_PODS] = {1130, 1130, 1130, 1130, 1130, 1130, 1130, 1130, 1130};

const int ADC_FAULT_LOW  = 150;
const int ADC_FAULT_HIGH = 4000;
const int ADC_SAMPLES    = 9;

// ---- safety limits --------------------------------------------------------
const unsigned long MAX_ON_MS       = 15000;   // any relay, hard ceiling
const unsigned long LINK_TIMEOUT_MS = 30000;   // Pi silent this long -> all off
const unsigned long VALVE_LEAD_MS   = 250;     // valve opens before pump
const unsigned long VALVE_LAG_MS    = 250;     // valve closes after pump

HardwareSerial PiLink(2);

bool          relayState[NUM_RELAYS] = {false};
unsigned long relayOnAt[NUM_RELAYS]  = {0};
unsigned long lastRx = 0;

// ---------------------------------------------------------------- helpers --
inline void drive(int pin, bool on) {
  digitalWrite(pin, (on == RELAY_ACTIVE_LOW) ? LOW : HIGH);
}

void emit(const String &s) { PiLink.println(s); Serial.println(s); }
void ackk(const String &s) { emit("ACK," + s); }
void err(const String &code, const String &detail) { emit("ERR," + code + "," + detail); }

// Latch OFF into the output register BEFORE the pin becomes an output. If you
// call pinMode() first the pin drives LOW for a few microseconds, which on an
// active-low board is a relay click -- and with water connected, a flood.
void safeInit(int pin) {
  drive(pin, false);
  pinMode(pin, OUTPUT);
  drive(pin, false);
}

void allOff(const char *why) {
  for (int i = 0; i < NUM_RELAYS; i++) { drive(RELAY_PINS[i], false); relayState[i] = false; }
  emit(String("EVT,ALLOFF,") + why);
}

int openSolenoid() {                     // index of the one open valve, or -1
  for (int i = 1; i < NUM_RELAYS; i++) if (relayState[i]) return i;
  return -1;
}

bool setRelay(int idx, bool on) {
  if (idx < 0 || idx >= NUM_RELAYS) { err("BAD_INDEX", String(idx)); return false; }

  if (on && idx == 0 && openSolenoid() < 0) {
    err("PUMP_BLOCKED", "no solenoid open -- would pump against a closed line");
    return false;
  }
  if (on && idx > 0) {
    int other = openSolenoid();
    if (other > 0 && other != idx) {
      err("VALVE_BUSY", "P-0" + String(other) + " already open");
      return false;
    }
  }
  if (!on && idx > 0 && relayState[0]) {
    err("PUMP_RUNNING", "close the pump before the valve");
    return false;
  }

  drive(RELAY_PINS[idx], on);
  relayState[idx] = on;
  if (on) relayOnAt[idx] = millis();
  emit("EVT,RELAY," + String(idx) + "," + (on ? "ON" : "OFF"));
  return true;
}

// ------------------------------------------------------------------- ADC ---
int readMux(int ch) {
  for (int i = 0; i < 4; i++) digitalWrite(MUX_SEL[i], (ch >> i) & 0x01);
  delayMicroseconds(50);
  int s[ADC_SAMPLES];
  for (int i = 0; i < ADC_SAMPLES; i++) { s[i] = analogRead(MUX_SIG); delay(2); }
  for (int i = 1; i < ADC_SAMPLES; i++) {        // insertion sort -> median
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[ADC_SAMPLES / 2];
}

float pctOfCC(int pod, int raw) {
  int span = dryADC[pod] - wetADC[pod];
  if (span == 0) return -1.0f;
  return constrain((float)(dryADC[pod] - raw) / span * 100.0f, 0.0f, 100.0f);
}

void reportSM(bool raw) {
  String line = raw ? "SMRAW" : "SM";
  for (int i = 0; i < NUM_PODS; i++) {
    int v = readMux(i);
    if (raw) { line += "," + String(v); continue; }
    if (v < ADC_FAULT_LOW || v > ADC_FAULT_HIGH) line += ",NaN";
    else line += "," + String(pctOfCC(i, v), 1);
  }
  emit(line);
}

// All nine in the SAME medium -> do they agree? This is the test that decides
// whether one constant pair is enough or each sensor needs its own.
void uniformity(int reps) {
  float mean[NUM_PODS];
  for (int c = 0; c < NUM_PODS; c++) {
    long sum = 0;
    for (int r = 0; r < reps; r++) { sum += readMux(c); delay(10); }
    mean[c] = (float)sum / reps;
  }
  float lo = mean[0], hi = mean[0], tot = 0;
  for (int c = 0; c < NUM_PODS; c++) { lo = min(lo, mean[c]); hi = max(hi, mean[c]); tot += mean[c]; }
  float avg = tot / NUM_PODS;

  String line = "UNIF";
  for (int c = 0; c < NUM_PODS; c++) line += "," + String(mean[c], 1);
  line += ",avg=" + String(avg, 1);
  line += ",spread=" + String(hi - lo, 0);
  line += ",spreadpct=" + String(100.0 * (hi - lo) / avg, 2);
  emit(line);
}

// --------------------------------------------------------------- commands --
void doPulse(int idx, unsigned long ms) {
  if (idx < 1 || idx > 9) { err("BAD_INDEX", "pulse wants a solenoid 1..9"); return; }
  if (ms == 0 || ms > MAX_ON_MS) { err("BAD_MS", String(ms)); return; }
  if (openSolenoid() > 0)        { err("VALVE_BUSY", "close it first"); return; }

  setRelay(idx, true);
  delay(VALVE_LEAD_MS);
  setRelay(0, true);
  unsigned long t0 = millis();
  while (millis() - t0 < ms) delay(5);
  setRelay(0, false);
  delay(VALVE_LAG_MS);
  setRelay(idx, false);
  emit("EVT,PULSE," + String(idx) + "," + String(millis() - t0));
}

void handle(String cmd) {
  cmd.trim();
  if (!cmd.length()) return;
  lastRx = millis();

  if (cmd == "PING")            { emit("PONG"); }
  else if (cmd == "SM")         { reportSM(false); }
  else if (cmd == "SM_RAW")     { reportSM(true); }
  else if (cmd.startsWith("UNIFORM")) {
    int n = 16; int c = cmd.indexOf(',');
    if (c > 0) n = constrain(cmd.substring(c + 1).toInt(), 4, 64);
    uniformity(n);
  }
  else if (cmd == "ALLOFF")     { allOff("commanded"); ackk("ALLOFF"); }
  else if (cmd == "STATUS") {
    String s = "STAT";
    for (int i = 0; i < NUM_RELAYS; i++) s += "," + String(relayState[i] ? 1 : 0);
    s += ",uptime=" + String(millis() / 1000);
    emit(s);
  }
  else if (cmd.startsWith("RELAY,")) {
    int a = cmd.indexOf(',');
    int b = cmd.indexOf(',', a + 1);
    if (b < 0) { err("BAD_CMD", "RELAY,<idx>,<0|1>"); return; }
    int idx = cmd.substring(a + 1, b).toInt();
    bool on = cmd.substring(b + 1).toInt() != 0;
    if (setRelay(idx, on)) ackk("RELAY");
  }
  else if (cmd.startsWith("PULSE,")) {
    int a = cmd.indexOf(',');
    int b = cmd.indexOf(',', a + 1);
    if (b < 0) { err("BAD_CMD", "PULSE,<idx>,<ms>"); return; }
    doPulse(cmd.substring(a + 1, b).toInt(), cmd.substring(b + 1).toInt());
  }
  else err("UNKNOWN", cmd);
}

// ------------------------------------------------------------------ main ---
String buf;

void setup() {
  for (int i = 0; i < NUM_RELAYS; i++) safeInit(RELAY_PINS[i]);   // FIRST
  for (int i = 0; i < 4; i++) { pinMode(MUX_SEL[i], OUTPUT); digitalWrite(MUX_SEL[i], LOW); }

  Serial.begin(115200);
  PiLink.begin(115200, SERIAL_8N1, UART_RX, UART_TX);
  analogReadResolution(12);
  analogSetPinAttenuation(MUX_SIG, ADC_11db);
  delay(300);

  lastRx = millis();
  emit("BOOT,bench_test,relays=" + String(NUM_RELAYS) + ",pods=" + String(NUM_PODS));
  Serial.println("commands: PING | SM | SM_RAW | UNIFORM[,n] | STATUS |");
  Serial.println("          RELAY,<0-9>,<0|1> | PULSE,<1-9>,<ms> | ALLOFF");
  Serial.println("relay 0 = pump, 1..9 = solenoid P-01..P-09");
}

void loop() {
  // commands may arrive from the Pi OR the USB console
  while (PiLink.available()) {
    char c = PiLink.read();
    if (c == '\n' || c == '\r') { if (buf.length()) { handle(buf); buf = ""; } }
    else { buf += c; if (buf.length() > 64) buf = ""; }
  }
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (buf.length()) { handle(buf); buf = ""; } }
    else { buf += c; if (buf.length() > 64) buf = ""; }
  }

  unsigned long now = millis();
  bool anyOn = false;

  for (int i = 0; i < NUM_RELAYS; i++) {
    if (!relayState[i]) continue;
    anyOn = true;
    if (now - relayOnAt[i] > MAX_ON_MS) {
      drive(RELAY_PINS[i], false);
      relayState[i] = false;
      err("AUTO_OFF", "relay " + String(i) + " exceeded " + String(MAX_ON_MS) + " ms");
    }
  }

  if (anyOn && (now - lastRx > LINK_TIMEOUT_MS)) allOff("link_timeout");

  delay(5);
}
