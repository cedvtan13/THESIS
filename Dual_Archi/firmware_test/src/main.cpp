#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

// --- PINOUT DEFINITIONS (ESP32-S3 Custom PCB) ---
const int MUX_SIG    = 1;                 // ADC1_CH0 (Mux Common Analog Pin)
const int MUX_SEL[4] = {2, 3, 4, 5};      // S0, S1, S2, S3 binary address lines

const int NUM_PODS = 9;

// --- TWO-POINT SENSOR CALIBRATION (3.28V VCC) ---
// dryADC: 2483 (bone-dry soil), wetADC: 1255 (saturated field capacity)
int dryADC[NUM_PODS] = {2483, 2483, 2483, 2483, 2483, 2483, 2483, 2483, 2483};
int wetADC[NUM_PODS] = {1255, 1255, 1255, 1255, 1255, 1255, 1255, 1255, 1255};

// Wi-Fi Access Point Credentials
const char* AP_SSID = "ESP32S3-Diagnostics";
const char* AP_PASS = "12345678";

WebServer server(80);

// Switches MUX channel and takes a 7-sample median filter
int readMuxMedian(int channel) {
  for (int i = 0; i < 4; i++) {
    digitalWrite(MUX_SEL[i], (channel >> i) & 0x01);
  }
  delayMicroseconds(80);

  int s[7];
  for (int i = 0; i < 7; i++) {
    s[i] = analogRead(MUX_SIG);
    delay(1);
  }

  for (int i = 1; i < 7; i++) {
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[3];
}

// Maps raw ADC counts to 0-100% relative soil moisture
float rawToPercent(int pod, int raw) {
  int span = dryADC[pod] - wetADC[pod];
  if (span == 0) return 0.0f;
  float pct = (float)(dryADC[pod] - raw) / (float)span * 100.0f;
  return constrain(pct, 0.0f, 100.0f);
}

// Returns JSON payload for asynchronous client requests
void handleApiMoisture() {
  String json = "{\"pots\":[";
  for (int i = 0; i < NUM_PODS; i++) {
    int raw = readMuxMedian(i);
    float pct = rawToPercent(i, raw);
    if (i > 0) json += ",";
    json += "{\"id\":" + String(i + 1) + 
            ",\"raw\":" + String(raw) + 
            ",\"moisture\":" + String(pct, 1) + "}";
  }
  json += "]}";
  server.send(200, "application/json", json);
}

// Main live web portal interface
void handleRoot() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pechay Telemetry | Live Soil Moisture</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 16px; }
    h1 { font-size: 20px; text-align: center; color: #4caf50; margin-bottom: 4px; }
    p.sub { text-align: center; font-size: 13px; color: #888; margin-top: 0; margin-bottom: 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; max-width: 1000px; margin: 0 auto; }
    .card { background: #1e1e1e; border: 1px solid #2e2e2e; border-radius: 8px; padding: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .pot-tag { font-weight: bold; font-size: 16px; }
    .group-tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #333; color: #aaa; text-transform: uppercase; }
    .moisture-val { font-size: 28px; font-weight: bold; color: #2196f3; }
    .raw-val { font-size: 12px; color: #777; margin-top: 2px; }
    .progress-bar-bg { width: 100%; height: 12px; background: #2a2a2a; border-radius: 6px; overflow: hidden; margin-top: 10px; }
    .progress-bar-fill { height: 100%; width: 0%; background: #2196f3; transition: width 0.4s ease, background-color 0.4s ease; }
    .status-dot { height: 8px; width: 8px; background: #4caf50; border-radius: 50%; display: inline-block; margin-right: 6px; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
  </style>
</head>
<body>
  <h1>Pechay 9-Pod Soil Moisture Dashboard</h1>
  <p class="sub"><span class="status-dot"></span>Live Asynchronous Polling (1.5s refresh)</p>
  
  <div class="grid" id="dashboard">
    <!-- Cards dynamically populated by JavaScript -->
  </div>

  <script>
    const groupLabels = [
      "Group A (30-40%)", "Group A (30-40%)", "Group A (30-40%)",
      "Group B (50-60%)", "Group B (50-60%)", "Group B (50-60%)",
      "Group C (70-80%)", "Group C (70-80%)", "Group C (70-80%)"
    ];

    function initDashboard() {
      const container = document.getElementById('dashboard');
      let html = '';
      for (let i = 1; i <= 9; i++) {
        html += `
          <div class="card" id="card-${i}">
            <div class="card-header">
              <span class="pot-tag">Pot P-0${i}</span>
              <span class="group-tag">${groupLabels[i-1]}</span>
            </div>
            <div class="moisture-val" id="val-${i}">--%</div>
            <div class="raw-val" id="raw-${i}">Raw ADC: ----</div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" id="bar-${i}"></div>
            </div>
          </div>
        `;
      }
      container.innerHTML = html;
    }

    async function updateTelemetry() {
      try {
        const response = await fetch('/api/moisture');
        const data = await response.json();
        
        data.pots.forEach(pot => {
          const valElem = document.getElementById(`val-${pot.id}`);
          const rawElem = document.getElementById(`raw-${pot.id}`);
          const barElem = document.getElementById(`bar-${pot.id}`);

          valElem.textContent = `${pot.moisture.toFixed(1)}%`;
          rawElem.textContent = `Raw ADC: ${pot.raw} (Dry: 2483 | Wet: 1255)`;
          barElem.style.width = `${Math.min(100, Math.max(0, pot.moisture))}%`;

          // Dynamic color based on treatment groups
          if (pot.moisture < 30) {
            barElem.style.backgroundColor = '#ff9800'; // Low deficit warning
          } else if (pot.moisture > 80) {
            barElem.style.backgroundColor = '#00bcd4'; // Saturated surplus
          } else {
            barElem.style.backgroundColor = '#4caf50'; // Nominal band
          }
        });
      } catch (err) {
        console.error("Telemetry fetch failed:", err);
      }
    }

    initDashboard();
    updateTelemetry();
    setInterval(updateTelemetry, 1500);
  </script>
</body>
</html>
)rawliteral";
  server.send(200, "text/html", html);
}

void setup() {
  Serial.begin(115200, SERIAL_8N1, 44, 43);

  for (int i = 0; i < 4; i++) {
    pinMode(MUX_SEL[i], OUTPUT);
    digitalWrite(MUX_SEL[i], LOW);
  }

  analogReadResolution(12);
  pinMode(MUX_SIG, INPUT);
  analogSetPinAttenuation(MUX_SIG, ADC_11db);

  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);

  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/moisture", HTTP_GET, handleApiMoisture);
  server.begin();

  Serial.println("AP Web Server Started. IP: 192.168.4.1");
}

void loop() {
  server.handleClient();
}