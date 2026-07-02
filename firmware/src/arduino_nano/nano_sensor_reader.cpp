// SmartSprinkler — Nano Sensor Reader
// Reads 4 HW-390 soil moisture sensors + DHT22 and sends to ESP32-CAM via serial.

#include <Arduino.h>
#include <SoftwareSerial.h>
#include "temp_humidity_sensor.h"

const int RX_PIN = 4;
const int TX_PIN = 3;

const int SENSOR_PINS[4] = {A0, A1, A2, A3};

SoftwareSerial espSerial(RX_PIN, TX_PIN);

void setup() {
    Serial.begin(115200);
    espSerial.begin(9600);
    TempHumiditySensor::init();

    for (int i = 0; i < 4; i++) {
        pinMode(SENSOR_PINS[i], INPUT);
    }

    Serial.println("Nano Sensor Reader ready (soil + DHT22)");
}

void loop() {
    int soil[4];
    for (int i = 0; i < 4; i++) {
        soil[i] = analogRead(SENSOR_PINS[i]);
    }

    float temp = TempHumiditySensor::getTemperature();
    float hum = TempHumiditySensor::getHumidity();

    if (isnan(temp)) temp = -1;
    if (isnan(hum)) hum = -1;

    espSerial.print("S:");
    for (int i = 0; i < 4; i++) {
        espSerial.print(soil[i]);
        if (i < 3) espSerial.print(',');
    }
    espSerial.print(',');
    espSerial.print(temp, 1);
    espSerial.print(',');
    espSerial.print(hum, 1);
    espSerial.print('\n');

    delay(500);
}
