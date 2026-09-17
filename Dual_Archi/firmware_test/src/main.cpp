#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP3XX.h>
#include <time.h>
#include <sys/time.h>

// --- PINOUT DEFINITIONS (ESP32-S3 Custom PCB) ---
const int MUX_SIG    = 1;                 // ADC1_CH0 (Mux COM)
const int MUX_SEL[4] = {2, 3, 4, 5};      // S0, S1, S2, S3

const int NUM_PODS = 9;
const int solenoidPins[NUM_PODS] = {6, 7, 8, 9, 10, 11, 12, 13, 14}; // Solenoids P-01 to P-09 (12V)
const int PUMP_PIN      = 15;             // Water pump (12V)
const int FAN_RELAY_PIN = 16;             // Dual intake/exhaust fans (5V)

const int BMP_SDA = 41;
const int BMP_SCL = 40;                   // Redefine to 14 if physical trace routes to 14

const int LED_PIN     = 21;
const int PROG_BTN    = 38;

const bool RELAY_ACTIVE_LOW = true;

// --- TWO-POINT SENSOR CALIBRATION ARRAYS ---
// Capacitive probes output HIGHER raw ADC counts when dry, LOWER when wet.
// Update individual pod values if you calibrated each probe separately.
int dryADC[NUM_PODS] = {3500, 3500, 3500, 3500, 3500, 3500, 3500, 3500, 3500};
int wetADC[NUM_PODS] = {1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500, 1130};

// AP Credentials (WPA2 passwords MUST be >= 8 characters)
const char* AP_SSID = "ESP32S3-Diagnostics";
const char* AP_PASS = "12345678";

// Timezone Settings: Asia/Manila (UTC+8, no DST)
const char* TIMEZONE_ENV = "PST-8";

// --- PERSISTENT RTC TIME TRACKING ---
RTC_DATA_ATTR unsigned long lastSavedEpoch = 0;
RTC_DATA_ATTR bool          rtcWasSynced   = false;

bool   timeSynced  = false;
String piStatus    = "No Ping Executed";
String relayStatus = "Idle";

WebServer server(80);
Adafruit_BMP3XX bmp;

bool  bmpFound     = false;
float currentTemp  = 0.0;
float currentPress = 0.0;

inline void relayWrite(int pin, bool on) {
  if (RELAY_ACTIVE_LOW) digitalWrite(pin, on ? LOW : HIGH);
  else digitalWrite(pin, on ? HIGH : LOW);
}

void applyEpoch(unsigned long epoch) {
  struct timeval tv;
  tv.tv_sec = epoch;
  tv.tv_usec = 0;
  settimeofday(&tv, NULL);

  timeSynced     = true;
  rtcWasSynced   = true;
  lastSavedEpoch = epoch;
}

unsigned long getNowEpoch() {
  time_t now;
  time(&now);
  return (unsigned long)now;
}

String getLocalTimeString() {
  if (!timeSynced && !rtcWasSynced) {
    return "Uptime: " + String(millis() / 1000) + "s (Unsynced)";
  }
  time_t now = getNowEpoch();
  struct tm timeinfo;
  localtime_r(&now, &timeinfo);

  char buf[64];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S (UTC+8)", &timeinfo);
  return String(buf);
}

// Switches MUX channel and performs 7-sample median filter for electrical stability
int readMuxMedian(int channel) {
  for (int i = 0; i < 4; i++) {
    digitalWrite(MUX_SEL[i], (channel >> i) & 0x01);
  }
  delayMicroseconds(60);

  int s[7];
  for (int i = 0; i < 7; i++) {
    s[i] = analogRead(MUX_SIG);
    delay(1);
  }

  // Insertion sort for median extraction
  for (int i = 1; i < 7; i++) {
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[3];
}

// Converts raw ADC to 0-100% relative field capacity using calibrated endpoints
float rawToPercent(int pod, int raw) {
  int span = dryADC[pod] - wetADC[pod];
  if (span == 0) return 0.0f;
  
  float pct = (float)(dryADC[pod] - raw) / (float)span * 100.0f;
  return constrain(pct, 0.0f, 100.0f);
}

void handleRoot() {
  String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>";
  html += "<title>ESP32-S3 Hardware Portal</title>";
  html += "<style>body{font-family:sans-serif;background:#111;color:#eee;padding:12px;margin:0;}";
  html += ".card{background:#1e1e1e;border:1px solid #333;border-radius:6px;padding:12px;margin-bottom:12px;}";
  html += "h2{color:#4CAF50;margin-top:0;font-size:18px;} table{width:100%;border-collapse:collapse;}";
  html += "th,td{border:1px solid #333;padding:6px;text-align:center;font-size:13px;} th{background:#2a2a2a;}";
  html += ".btn{background:#4CAF50;color:#fff;border:none;padding:8px 12px;border-radius:4px;cursor:pointer;font-weight:bold;margin:2px;}";
  html += ".btn-blue{background:#2196F3;} .btn-danger{background:#d32f2f;} .grid{display:flex;flex-wrap:wrap;gap:6px;}";
  html += "</style></head><body>";

  html += "<div class='card'>";
  html += "<h2>System & Time Status</h2>";
  html += "<p><b>Timezone (Asia/Manila):</b> " + getLocalTimeString() + "</p>";
  html += "<p><b>Clock Source:</b> " + String(timeSynced ? "<span style='color:#0f0;'>Synced (RTC Running)</span>" : "<span style='color:#ff9800;'>Restored from RTC memory</span>") + "</p>";
  html += "<p><b>RPi UART Link:</b> " + piStatus + "</p>";
  html += "<p><b>Relay Action:</b> " + relayStatus + "</p>";

  html += "<div style='display:flex;gap:6px;margin-top:8px;'>";
  html += "<form action='/pingPi' method='POST' style='display:inline;'><button class='btn'>Ping RPi</button></form>";
  html += "<button class='btn btn-blue' onclick='syncBrowserTime()'>Sync Browser Time</button>";
  html += "</div></div>";

  html += "<div class='card'>";
  html += "<h2>BMP388 Enclosure Climate</h2>";
  if (bmpFound) {
    html += "<p>Temperature: <b>" + String(currentTemp, 1) + " &deg;C</b></p>";
    html += "<p>Barometric Pressure: <b>" + String(currentPress, 1) + " hPa</b></p>";
  } else {
    html += "<p style='color:#f44336;'>Sensor Offline (Check 3.3V Rail & I2C lines)</p>";
  }
  html += "</div>";

  html += "<div class='card'>";
  html += "<h2>9-Pod Soil Moisture (Calibrated)</h2><table>";
  html += "<tr><th>Pot</th><th>ADC Raw (12-bit)</th><th>Calibrated Moisture</th><th>Baseline (Dry / Wet)</th></tr>";
  for (int i = 0; i < NUM_PODS; i++) {
    int raw = readMuxMedian(i);
    float pct = rawToPercent(i, raw);
    html += "<tr><td>P-0" + String(i + 1) + "</td><td>" + String(raw) + "</td>";
    html += "<td><b>" + String(pct, 1) + "%</b></td>";
    html += "<td style='color:#888;'>" + String(dryADC[i]) + " / " + String(wetADC[i]) + "</td></tr>";
  }
  html += "</table></div>";

  html += "<div class='card'>";
  html += "<h2>Manual Relay Test (2-Second Pulse)</h2><div class='grid'>";
  for (int i = 0; i < NUM_PODS; i++) {
    html += "<form action='/pulseRelay' method='POST' style='display:inline;'>";
    html += "<input type='hidden' name='ch' value='" + String(i) + "'>";
    html += "<button class='btn'>Solenoid " + String(i + 1) + "</button></form>";
  }
  html += "<form action='/pulseRelay' method='POST' style='display:inline;'>";
  html += "<input type='hidden' name='ch' value='pump'>";
  html += "<button class='btn btn-danger'>12V Pump</button></form>";
  html += "<form action='/pulseRelay' method='POST' style='display:inline;'>";
  html += "<input type='hidden' name='ch' value='fan'>";
  html += "<button class='btn'>5V Fans</button></form>";
  html += "</div></div>";

  html += "<script>";
  html += "function syncBrowserTime(){";
  html += "  var epoch = Math.floor(Date.now() / 1000);";
  html += "  var form = document.createElement('form');";
  html += "  form.method = 'POST'; form.action = '/setTime';";
  html += "  var input = document.createElement('input');";
  html += "  input.type = 'hidden'; input.name = 'epoch'; input.value = epoch;";
  html += "  form.appendChild(input); document.body.appendChild(form); form.submit();";
  html += "}";
  html += "</script>";

  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleSetTime() {
  if (server.hasArg("epoch")) {
    unsigned long epoch = strtoul(server.arg("epoch").c_str(), NULL, 10);
    if (epoch > 1700000000UL) {
      applyEpoch(epoch);
    }
  }
  server.sendHeader("Location", "/");
  server.send(303);
}

void handlePingPi() {
  while (Serial.available()) Serial.read();
  Serial.println("PING");
  
  unsigned long start = millis();
  bool gotAck = false;
  String resp = "";
  while (millis() - start < 1500) {
    if (Serial.available()) {
      resp = Serial.readStringUntil('\n');
      resp.trim();
      gotAck = true;
      break;
    }
  }

  if (gotAck) piStatus = "<span style='color:#0f0;'>Online | Response: " + resp + "</span>";
  else piStatus = "<span style='color:#f44336;'>Timeout (No response on UART0)</span>";

  server.sendHeader("Location", "/");
  server.send(303);
}

void handlePulseRelay() {
  if (server.hasArg("ch")) {
    String ch = server.arg("ch");
    int targetPin = -1;
    String name = "";

    if (ch == "pump") { targetPin = PUMP_PIN; name = "Water Pump (12V)"; }
    else if (ch == "fan") { targetPin = FAN_RELAY_PIN; name = "Cooling Fans (5V)"; }
    else {
      int idx = ch.toInt();
      if (idx >= 0 && idx < NUM_PODS) { targetPin = solenoidPins[idx]; name = "Solenoid " + String(idx + 1); }
    }

    if (targetPin != -1) {
      relayWrite(targetPin, true);
      delay(2000);
      relayWrite(targetPin, false);
      relayStatus = name + " pulsed for 2s";
    }
  }
  server.sendHeader("Location", "/");
  server.send(303);
}

void checkUartCommands() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("TIME,")) {
      unsigned long e = strtoul(cmd.substring(5).c_str(), NULL, 10);
      if (e > 1700000000UL) {
        applyEpoch(e);
        Serial.println("ACK,TIME," + String(getNowEpoch()));
      }
    } else if (cmd == "PING") {
      Serial.println("PONG," + String(getNowEpoch()));
    } else if (cmd == "GET_SM") {
      // Formatted SM snapshot per Deliverable 5 specs
      String line = "SM," + String(getNowEpoch());
      for (int i = 0; i < NUM_PODS; i++) {
        int raw = readMuxMedian(i);
        line += "," + String(rawToPercent(i, raw), 1);
      }
      Serial.println(line);
    }
  }
}

void setup() {
  // Uses physical UART0 on custom PCB (U0TXD GPIO 43 / U0RXD GPIO 44)
  Serial.begin(115200, SERIAL_8N1, 44, 43);

  setenv("TZ", TIMEZONE_ENV, 1);
  tzset();

  if (rtcWasSynced && lastSavedEpoch > 1700000000UL) {
    applyEpoch(lastSavedEpoch);
  }

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  pinMode(PROG_BTN, INPUT_PULLUP);

  // Initialize relays safely to OFF state before declaring output modes
  for (int i = 0; i < NUM_PODS; i++) {
    digitalWrite(solenoidPins[i], RELAY_ACTIVE_LOW ? HIGH : LOW);
    pinMode(solenoidPins[i], OUTPUT);
    relayWrite(solenoidPins[i], false);
  }
  digitalWrite(PUMP_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(PUMP_PIN, OUTPUT);
  relayWrite(PUMP_PIN, false);

  digitalWrite(FAN_RELAY_PIN, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(FAN_RELAY_PIN, OUTPUT);
  relayWrite(FAN_RELAY_PIN, false);

  for (int i = 0; i < 4; i++) {
    pinMode(MUX_SEL[i], OUTPUT);
    digitalWrite(MUX_SEL[i], LOW);
  }

  analogReadResolution(12);
  pinMode(MUX_SIG, INPUT);
  analogSetPinAttenuation(MUX_SIG, ADC_11db);

  Wire.begin(BMP_SDA, BMP_SCL);
  if (bmp.begin_I2C(0x76, &Wire)) {
    bmpFound = true;
    bmp.setTemperatureOversampling(BMP3_OVERSAMPLING_8X);
    bmp.setPressureOversampling(BMP3_OVERSAMPLING_4X);
  }

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);

  server.on("/", HTTP_GET, handleRoot);
  server.on("/setTime", HTTP_POST, handleSetTime);
  server.on("/pingPi", HTTP_POST, handlePingPi);
  server.on("/pulseRelay", HTTP_POST, handlePulseRelay);
  server.begin();

  digitalWrite(LED_PIN, HIGH);
}

void loop() {
  server.handleClient();
  checkUartCommands();

  static unsigned long lastRtcSave = 0;
  if (millis() - lastRtcSave >= 10000) {
    lastRtcSave = millis();
    if (timeSynced) {
      lastSavedEpoch = getNowEpoch();
    }
  }

  static unsigned long lastBmpCheck = 0;
  if (bmpFound && (millis() - lastBmpCheck >= 2000)) {
    lastBmpCheck = millis();
    if (bmp.performReading()) {
      currentTemp = bmp.temperature;
      currentPress = bmp.pressure / 100.0F;
    }
  }
}