#include <Arduino.h>

const int NUM_PODS = 9;

// NodeMCU-32S Multiplexer Pin Mapping
const int MUX_SIG    = 34;                // ADC1_CH6 (Analog In)
const int MUX_SEL[4] = {18, 19, 4, 5};    // S0, S1, S2, S3

// Two-point calibration benchmarks (dry = ~0%, wet = ~100%)[cite: 1, 12]
const int dryADC[NUM_PODS] = {2553, 2553, 2553, 2553, 2553, 2553, 2553, 2553, 2553};
const int wetADC[NUM_PODS] = {1130, 1130, 1130, 1130, 1130, 1130, 1130, 1130, 1130};

int readMuxMedian(int channel) {
  // Set binary select lines S0-S3
  for (int i = 0; i < 4; i++) {
    digitalWrite(MUX_SEL[i], (channel >> i) & 0x01);
  }
  delayMicroseconds(50); // Line settling time

  // Take 9 readings and median-filter to eliminate noise
  int s[9];
  for (int i = 0; i < 9; i++) {
    s[i] = analogRead(MUX_SIG);
    delay(2);
  }
  for (int i = 1; i < 9; i++) {
    int key = s[i], j = i - 1;
    while (j >= 0 && s[j] > key) { s[j + 1] = s[j]; j--; }
    s[j + 1] = key;
  }
  return s[4];
}

float calculateMoisturePercent(int pod, int raw) {
  int span = dryADC[pod] - wetADC[pod];
  if (span == 0) return -1.0f;
  // Capacitive sensors output higher values in dry soil, lower in wet[cite: 1, 16]
  float pct = (float)(dryADC[pod] - raw) / (float)span * 100.0f;
  return constrain(pct, 0.0f, 100.0f);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  for (int i = 0; i < 4; i++) {
    pinMode(MUX_SEL[i], OUTPUT);
    digitalWrite(MUX_SEL[i], LOW);
  }

  analogReadResolution(12);
  pinMode(MUX_SIG, INPUT);

  Serial.println("\n--- 9-Channel Soil Moisture Live Monitor ---");
}

void loop() {
  Serial.println("\n------------------------------------------------------------");
  for (int i = 0; i < NUM_PODS; i++) {
    int raw = readMuxMedian(i);
    float pct = calculateMoisturePercent(i, raw);

    Serial.print("Pot P-0");
    Serial.print(i + 1);
    Serial.print(" | Raw ADC: ");
    Serial.print(raw);
    Serial.print(" | Moisture: ");
    Serial.print(pct, 1);
    Serial.println("%");
  }
  delay(2000);
}