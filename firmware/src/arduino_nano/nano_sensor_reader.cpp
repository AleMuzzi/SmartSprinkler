// SmartSprinkler — Nano Sensor Reader
// Reads 4 HW-390 soil moisture sensors and sends them to ESP32-CAM via serial.

#include <Arduino.h>
#include <SoftwareSerial.h>

const int RX_PIN = 4;  // RX from ESP32 (GPIO 15) — direct connection
const int TX_PIN = 3;  // TX to ESP32 (GPIO 14) — needs 5V→3.3V level shifter

const int SENSOR_PINS[4] = {A0, A1, A2, A3};

SoftwareSerial espSerial(RX_PIN, TX_PIN);

void setup() {
    Serial.begin(115200);
    espSerial.begin(9600);

    for (int i = 0; i < 4; i++) {
        pinMode(SENSOR_PINS[i], INPUT);
    }

    Serial.println("Nano Sensor Reader ready");
}

void loop() {
    int readings[4];
    for (int i = 0; i < 4; i++) {
        readings[i] = analogRead(SENSOR_PINS[i]);
    }

    espSerial.print("S:");
    for (int i = 0; i < 4; i++) {
        espSerial.print(readings[i]);
        if (i < 3) espSerial.print(',');
    }
    espSerial.print('\n');

    delay(500);
}