/* ===========================================================================
 * ESP32-S3 Self-Hosted Web Dashboard (WiFi Access Point)
 *
 * The ESP32 creates its own WiFi network. Connect a phone/laptop to it and open
 * http://192.168.4.1 to see telemetry and control the relays. No internet or
 * router needed.
 *
 *   WiFi name : AgriSentry
 *   Password  : agrisentry123
 *   Address   : http://192.168.4.1
 *
 * Safety built in:
 *   - Pump is LOCKED at boot (unlock it from the page)
 *   - Pump only starts if a valve is already open
 *   - Only ONE valve open at a time
 *   - Pump stops before its valve closes
 *   - Valves/pump auto-shut after MAX_WET_ON_MS, light after LIGHT_MAX_MS
 *   - "ALL OFF" button and serial command 'k'
 * ========================================================================= */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP3XX.h>
#include "esp_system.h"

// ----------------------------- WiFi settings -------------------------------
const char* AP_SSID = "AgriSentry";
const char* AP_PASS = "agrisentry123";     // must be 8+ characters

// ------------------------------- Pin map -----------------------------------
const int NUM_PODS   = 9;
const int NUM_RELAYS = 12;                 // 0-8 valves, 9 pump, 10 fan, 11 light
const int PUMP_ID = 9, FAN_ID = 10, LIGHT_ID = 11;
const bool RELAY_ACTIVE_LOW = true;

const int relayPins[NUM_RELAYS] = {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17};

const int MUX_SIG    = 1;
const int MUX_SEL[4] = {2, 3, 4, 5};

const int BMP_SDA = 41;
const int BMP_SCL = 40;

const int PI_UART_RX = 44;
const int PI_UART_TX = 43;

const int LED_INDICATOR_PIN = 21;          // active-LOW

// --------------------------- Calibration & limits --------------------------
int dryADC[NUM_PODS] = {2483, 2483, 2483, 2483, 2483, 2483, 2483, 2483, 2483};
int wetADC[NUM_PODS] = {1120, 1120, 1120, 1120, 1120, 1120, 1120, 1120, 1120};
const int ADC_FAULT_LOW  = 150;
const int ADC_FAULT_HIGH = 4000;
const int ADC_SAMPLES    = 9;

const unsigned long MAX_WET_ON_MS  = 30UL * 1000UL;        // valve/pump auto-off
const unsigned long LIGHT_MAX_MS   = 5UL * 60UL * 1000UL;  // light auto-off
const unsigned long SM_INTERVAL_MS  = 3000;
const unsigned long BMP_INTERVAL_MS = 5000;
const float FAN_ON_TEMP  = 35.0f;
const float FAN_OFF_TEMP = 32.0f;

// -------------------------------- State ------------------------------------
WebServer server(80);
Adafruit_BMP3XX bmp;
bool  bmpAvailable = false;
float tempC = 0, pressHpa = 0;

bool          relayState[NUM_RELAYS] = {false};
unsigned long onSince[NUM_RELAYS]    = {0};
bool pumpLocked = true;
bool fanAuto    = false;

int   rawADC[NUM_PODS];
float moisture[NUM_PODS];                  // -1 = fault
unsigned long lastSm = 0, lastBmp = 0;

// ------------------------------- Helpers -----------------------------------
void hw(int id, bool on) {                 // low-level relay write
  digitalWrite(relayPins[id], (on == RELAY_ACTIVE_LOW) ? LOW : HIGH);
  if (on && !relayState[id]) onSince[id] = millis();
  relayState[id] = on;
}

void initRelays() {
  for (int i = 0; i < NUM_RELAYS; i++) {
    digitalWrite(relayPins[i], RELAY_ACTIVE_LOW ? HIGH : LOW);   // OFF first
    pinMode(relayPins[i], OUTPUT);
    hw(i, false);
  }
}

int openValve() {
  for (int i = 0; i < NUM_PODS; i++) if (relayState[i]) return i;
  return -1;
}

void allOff() {
  if (relayState[PUMP_ID]) { hw(PUMP_ID, false); delay(150); }
  for (int i = 0; i < NUM_RELAYS; i++) hw(i, false);
}

// Applies safety rules. Returns false and fills err if refused.
bool setRelay(int id, bool on, String &err) {
  if (id < 0 || id >= NUM_RELAYS) { err = "bad relay id"; return false; }

  if (on) {
    if (id == PUMP_ID) {
      if (pumpLocked)        { err = "Pump is locked. Unlock it first.";   return false; }
      if (openValve() < 0)   { err = "Open a valve before the pump.";      return false; }
      delay(150);                                   // valve leads pump
      hw(PUMP_ID, true);
    } else if (id < NUM_PODS) {
      int other = openValve();
      if (other >= 0 && other != id) {              // one valve at a time
        if (relayState[PUMP_ID]) { hw(PUMP_ID, false); delay(150); }
        hw(other, false);
      }
      hw(id, true);
    } else {
      if (id == FAN_ID) fanAuto = false;            // manual overrides auto
      hw(id, true);
    }
  } else {
    if (id < NUM_PODS && relayState[PUMP_ID]) {     // pump stops before valve closes
      hw(PUMP_ID, false);
      delay(150);
    }
    if (id == FAN_ID) fanAuto = false;
    hw(id, false);
  }
  return true;
}

const char* resetReasonName(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON:   return "POWERON";
    case ESP_RST_SW:        return "SOFTWARE";
    case ESP_RST_PANIC:     return "PANIC";
    case ESP_RST_INT_WDT:   return "INT_WDT";
    case ESP_RST_TASK_WDT:  return "TASK_WDT";
    case ESP_RST_WDT:       return "WDT";
    case ESP_RST_DEEPSLEEP: return "DEEPSLEEP";
    case ESP_RST_BROWNOUT:  return "BROWNOUT";
    default:                return "OTHER";
  }
}

// ------------------------------ Sensors ------------------------------------
int readMuxRaw(int ch) {
  for (int i = 0; i < 4; i++) digitalWrite(MUX_SEL[i], (ch >> i) & 1);
  delayMicroseconds(80);
  return analogRead(MUX_SIG);
}

int readMuxMedian(int ch) {
  int s[ADC_SAMPLES];
  for (int i = 0; i < ADC_SAMPLES; i++) { s[i] = readMuxRaw(ch); delay(2); }
  for (int i = 1; i < ADC_SAMPLES; i++) {
    int k = s[i], j = i - 1;
    while (j >= 0 && s[j] > k) { s[j + 1] = s[j]; j--; }
    s[j + 1] = k;
  }
  return s[ADC_SAMPLES / 2];
}

void readAllMoisture() {
  for (int i = 0; i < NUM_PODS; i++) {
    int raw = readMuxMedian(i);
    rawADC[i] = raw;
    int span = dryADC[i] - wetADC[i];
    if (raw < ADC_FAULT_LOW || raw > ADC_FAULT_HIGH || span == 0) {
      moisture[i] = -1.0f;
    } else {
      moisture[i] = constrain((float)(dryADC[i] - raw) / span * 100.0f, 0.0f, 100.0f);
    }
  }
}

void initBmp() {
  Wire.begin(BMP_SDA, BMP_SCL);
  Wire.setTimeOut(30);                               // never hang the bus
  const uint8_t addrs[2] = {0x76, 0x77};
  for (uint8_t a : addrs) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0 && bmp.begin_I2C(a, &Wire)) {
      bmpAvailable = true;
      bmp.setTemperatureOversampling(BMP3_OVERSAMPLING_8X);
      bmp.setPressureOversampling(BMP3_OVERSAMPLING_4X);
      return;
    }
  }
}

// ------------------------------ Web page -----------------------------------
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgriSentry</title>
<style>
:root{--bg:#0f1a14;--card:#182820;--tx:#e6f2ea;--mut:#8fae9b;--ok:#3ddc84;--warn:#ffb74d;--bad:#ff5252;--ac:#2e8b57}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--tx);padding:12px;max-width:900px;margin:auto}
h1{font-size:1.3rem;margin:4px 0}
.top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px}
#st{font-size:.85rem;color:var(--mut)}
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));margin:10px 0}
.card{background:var(--card);border-radius:10px;padding:10px}
.card small{color:var(--mut);display:block;font-size:.75rem}
.card b{font-size:1.2rem}
h2{font-size:1rem;margin:16px 0 4px;color:var(--mut)}
.pod .ph{display:flex;justify-content:space-between;margin-bottom:6px}
.bar{height:8px;background:#0b140f;border-radius:4px;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--ok);transition:width .4s}
.raw{font-size:.7rem;color:var(--mut);margin:4px 0 8px}
button{width:100%;padding:9px;border:0;border-radius:8px;background:#26382e;color:var(--tx);font-size:.9rem;cursor:pointer}
button.on{background:var(--ac)}
button.danger{background:var(--bad);font-weight:700}
button.warn{background:var(--warn);color:#222}
.row{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(130px,1fr))}
</style></head><body>
<div class="top"><h1>AgriSentry Control</h1><span id="st">connecting...</span></div>

<div class="grid">
 <div class="card"><small>Temperature</small><b id="t">--</b></div>
 <div class="card"><small>Pressure</small><b id="p">--</b></div>
 <div class="card"><small>Uptime</small><b id="up">--</b></div>
 <div class="card"><small>Free heap</small><b id="hp">--</b></div>
 <div class="card"><small>Last reset</small><b id="rr">--</b></div>
 <div class="card"><small>WiFi clients</small><b id="cl">--</b></div>
</div>

<h2>Soil moisture and valves (one valve at a time)</h2>
<div class="grid" id="pods"></div>

<h2>Auxiliary</h2>
<div class="row">
 <button id="r9"  onclick="tg(9)">Pump OFF</button>
 <button id="r10" onclick="tg(10)">Fan OFF</button>
 <button id="r11" onclick="tg(11)">Light OFF</button>
</div>
<div class="row" style="margin-top:10px">
 <button id="pl" onclick="pl()">Pump LOCKED</button>
 <button id="fa" onclick="fa()">Fan auto: OFF</button>
 <button class="danger" onclick="ao()">ALL OFF</button>
</div>

<script>
const $=id=>document.getElementById(id);
let S=null;
(function(){let h='';for(let i=0;i<9;i++)h+=
'<div class="card pod"><div class="ph"><b>P-0'+(i+1)+'</b><span id="sm'+i+'">--</span></div>'+
'<div class="bar"><i id="bar'+i+'"></i></div><div class="raw" id="raw'+i+'"></div>'+
'<button id="r'+i+'" onclick="tg('+i+')">Valve OFF</button></div>';
$('pods').innerHTML=h;})();

function fmt(s){const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return h+'h '+m+'m '+(s%60)+'s';}
function setBtn(id,label,on){const b=$(id);b.textContent=label+(on?' ON':' OFF');b.className=on?'on':'';}

function render(d){
 S=d;
 $('t').textContent=d.bmp?d.temp.toFixed(1)+' C':'no sensor';
 $('p').textContent=d.bmp?d.press.toFixed(1)+' hPa':'no sensor';
 $('up').textContent=fmt(d.up);
 $('hp').textContent=Math.round(d.heap/1024)+' KB';
 $('rr').textContent=d.rr;
 $('cl').textContent=d.clients;
 for(let i=0;i<9;i++){
  const v=d.sm[i];
  $('sm'+i).textContent=v===null?'FAULT':v.toFixed(1)+'%';
  $('bar'+i).style.width=(v===null?0:v)+'%';
  $('raw'+i).textContent='raw '+d.raw[i];
  setBtn('r'+i,'Valve',d.relays[i]);
 }
 setBtn('r9','Pump',d.relays[9]);
 setBtn('r10','Fan',d.relays[10]);
 setBtn('r11','Light',d.relays[11]);
 const pl=$('pl');pl.textContent=d.pumpLock?'Pump LOCKED (tap to unlock)':'Pump UNLOCKED (tap to lock)';
 pl.className=d.pumpLock?'':'warn';
 const fa=$('fa');fa.textContent='Fan auto: '+(d.fanAuto?'ON':'OFF');fa.className=d.fanAuto?'on':'';
}

async function call(path){
 try{const r=await fetch(path);const j=await r.json();if(j.ok===false)alert(j.err);}
 catch(e){alert('Connection lost');}
 refresh();
}
function tg(id){if(!S)return;call('/api/relay?id='+id+'&state='+(S.relays[id]?0:1));}
function pl(){if(!S)return;call('/api/pumplock?state='+(S.pumpLock?0:1));}
function fa(){if(!S)return;call('/api/fanauto?state='+(S.fanAuto?0:1));}
function ao(){call('/api/alloff');}

async function refresh(){
 try{const r=await fetch('/api/status');render(await r.json());$('st').textContent='online';}
 catch(e){$('st').textContent='offline - reconnect to WiFi';}
}
refresh();setInterval(refresh,2000);
</script></body></html>
)rawliteral";

// ------------------------------ API handlers -------------------------------
void sendJson(const String& body) {
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", body);
}

void handleStatus() {
  String j = "{";
  j += "\"up\":" + String(millis() / 1000UL);
  j += ",\"heap\":" + String(ESP.getFreeHeap());
  j += ",\"rr\":\"" + String(resetReasonName(esp_reset_reason())) + "\"";
  j += ",\"clients\":" + String(WiFi.softAPgetStationNum());
  j += ",\"bmp\":" + String(bmpAvailable ? "true" : "false");
  j += ",\"temp\":" + String(tempC, 2);
  j += ",\"press\":" + String(pressHpa, 2);
  j += ",\"pumpLock\":" + String(pumpLocked ? "true" : "false");
  j += ",\"fanAuto\":" + String(fanAuto ? "true" : "false");
  j += ",\"relays\":[";
  for (int i = 0; i < NUM_RELAYS; i++) { j += relayState[i] ? "1" : "0"; if (i < NUM_RELAYS - 1) j += ","; }
  j += "],\"raw\":[";
  for (int i = 0; i < NUM_PODS; i++) { j += String(rawADC[i]); if (i < NUM_PODS - 1) j += ","; }
  j += "],\"sm\":[";
  for (int i = 0; i < NUM_PODS; i++) {
    j += (moisture[i] < 0) ? String("null") : String(moisture[i], 1);
    if (i < NUM_PODS - 1) j += ",";
  }
  j += "]}";
  sendJson(j);
}

void handleRelay() {
  if (!server.hasArg("id") || !server.hasArg("state")) { sendJson("{\"ok\":false,\"err\":\"missing args\"}"); return; }
  int id = server.arg("id").toInt();
  bool on = server.arg("state").toInt() == 1;
  String err;
  bool ok = setRelay(id, on, err);
  Serial.printf("WEB relay %d -> %s (%s)\n", id, on ? "ON" : "OFF", ok ? "ok" : err.c_str());
  sendJson(ok ? String("{\"ok\":true}") : "{\"ok\":false,\"err\":\"" + err + "\"}");
}

void handlePumpLock() {
  pumpLocked = server.arg("state").toInt() == 1;
  if (pumpLocked && relayState[PUMP_ID]) hw(PUMP_ID, false);
  Serial.printf("WEB pump lock = %d\n", pumpLocked);
  sendJson("{\"ok\":true}");
}

void handleFanAuto() {
  fanAuto = server.arg("state").toInt() == 1;
  if (fanAuto && !bmpAvailable) { fanAuto = false; sendJson("{\"ok\":false,\"err\":\"No BMP388 sensor, auto fan unavailable.\"}"); return; }
  sendJson("{\"ok\":true}");
}

void handleAllOff() {
  allOff();
  Serial.println("WEB ALL OFF");
  sendJson("{\"ok\":true}");
}

// ------------------------------- Arduino -----------------------------------
void setup() {
  initRelays();                                      // everything OFF first

  Serial.begin(115200, SERIAL_8N1, PI_UART_RX, PI_UART_TX);
  delay(300);
  Serial.printf("\nBOOT reset_reason=%s\n", resetReasonName(esp_reset_reason()));

  pinMode(LED_INDICATOR_PIN, OUTPUT);
  digitalWrite(LED_INDICATOR_PIN, HIGH);

  for (int i = 0; i < 4; i++) { pinMode(MUX_SEL[i], OUTPUT); digitalWrite(MUX_SEL[i], LOW); }
  analogReadResolution(12);
  pinMode(MUX_SIG, INPUT);
  analogSetPinAttenuation(MUX_SIG, ADC_11db);
  for (int i = 0; i < NUM_PODS; i++) { rawADC[i] = 0; moisture[i] = -1.0f; }

  initBmp();
  Serial.printf("BMP388 %s\n", bmpAvailable ? "online" : "offline");

  // WiFi AP, started after relays/sensors so a power dip can't leave a relay on
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS, 1, 0, 4);            // channel 1, visible, 4 clients max
  Serial.printf("WiFi AP '%s' up. Open http://%s\n", AP_SSID, WiFi.softAPIP().toString().c_str());

  server.on("/", []() { server.send(200, "text/html", INDEX_HTML); });
  server.on("/api/status",   handleStatus);
  server.on("/api/relay",    handleRelay);
  server.on("/api/pumplock", handlePumpLock);
  server.on("/api/fanauto",  handleFanAuto);
  server.on("/api/alloff",   handleAllOff);
  server.begin();

  readAllMoisture();
}

void loop() {
  server.handleClient();

  // Serial kill switch
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'k' || c == 'K') { allOff(); Serial.println("KILL: all relays OFF"); }
  }

  unsigned long now = millis();

  // Auto-shutoff timers
  if (relayState[PUMP_ID] && now - onSince[PUMP_ID] > MAX_WET_ON_MS) {
    hw(PUMP_ID, false);
    Serial.println("AUTO-OFF: pump max time");
  }
  for (int i = 0; i < NUM_PODS; i++) {
    if (relayState[i] && now - onSince[i] > MAX_WET_ON_MS) {
      if (relayState[PUMP_ID]) { hw(PUMP_ID, false); delay(150); }
      hw(i, false);
      Serial.printf("AUTO-OFF: valve %d max time\n", i + 1);
    }
  }
  if (relayState[LIGHT_ID] && now - onSince[LIGHT_ID] > LIGHT_MAX_MS) {
    hw(LIGHT_ID, false);
    Serial.println("AUTO-OFF: light max time");
  }

  // Sensors
  if (now - lastSm >= SM_INTERVAL_MS) {
    lastSm = now;
    readAllMoisture();
  }
  if (bmpAvailable && now - lastBmp >= BMP_INTERVAL_MS) {
    lastBmp = now;
    if (bmp.performReading()) {
      tempC = bmp.temperature;
      pressHpa = bmp.pressure / 100.0f;
      if (fanAuto) {
        if (tempC >= FAN_ON_TEMP)       hw(FAN_ID, true);
        else if (tempC <= FAN_OFF_TEMP) hw(FAN_ID, false);
      }
    }
  }

  delay(2);
}