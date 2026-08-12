#include<Arduino.h>

// uart pins
#define RX2_PIN 16
#define TX2_PIN 17

// relay pin mapping
const int RELAY_PINS[4] = {25, 26, 27, 14};

// active low relay definitions
#define RELAY_ON LOW
#define RELAY_OFF HIGH


void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, RX2_PIN, TX2_PIN);

  // initialize relay pins to off
  for (int i = 0; i < 4; i++){
    pinMode(RELAY_PINS[i], OUTPUT);
    digitalWrite(RELAY_PINS[i], RELAY_OFF);
  }

  Serial.println("RELAY and UART actuation firmware ready");

}

void loop() {
  // put your main code here, to run repeatedly:
  if (Serial2.available() > 0){
    String command = Serial2.readStringUntil('\n');
    command.trim();

    Serial.print("Received from Pi: ");
    Serial.println(command);

    // command: WATER,<channel number> e.g. WATER,1
    if (command.startsWith("WATER,")){
      int ch = command.substring(6).toInt() - 1;

      if (ch >= 0 && ch < 3){
        Serial2.println("ACK,WATERING_START");

        // turn on solenoid channel + pump (IN4)
        digitalWrite(RELAY_PINS[ch], RELAY_ON); // solenoid on
        digitalWrite(RELAY_PINS[3], RELAY_ON); // pump on
        Serial.println("Actuated: Solenoid " + String(ch + 1) + " + Pump ON");

        delay(500);

        // turn off solenoid channel + pump (IN4)
        digitalWrite(RELAY_PINS[ch], RELAY_OFF); // solenoid off
        digitalWrite(RELAY_PINS[3], RELAY_OFF); // pump off
        Serial.println("Actuated: Solenoid " + String(ch + 1) + " + Pump OFF");

        Serial2.println("ACK,WATERING_COMPLETE");
      }

      else{
        Serial2.println("ERR,INVALID_CHANNEL");
      }
    }
    // Command all off
    else if (command == "ALL_OFF"){
      for (int i = 0; i < 4; i++){
        digitalWrite(RELAY_PINS[i], RELAY_OFF);
      }
      Serial2.println("ACK,ALL_OFF");
    }
    else if (command == "PING"){
      Serial2.println("PONG,ESP32_READY");
    }
  }
}
