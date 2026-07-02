// SmartSprinkler — Nano Sensor Reader
// Reads 4 HW-390 soil moisture sensors + DHT22 + float switch and sends to ESP32-CAM via serial.

#include <Arduino.h>
#include <SoftwareSerial.h>
#include "sensors/temp_humidity_sensor.h"

const int RX_PIN = 4;
const int TX_PIN = 3;
const int FLOAT_PIN = 5;

const int SENSOR_PINS[4] = {A0, A1, A2, A3};

SoftwareSerial espSerial(RX_PIN, TX_PIN);

void setup() {
    espSerial.begin(9600);
    TempHumiditySensor::init();
    pinMode(FLOAT_PIN, INPUT_PULLUP);

    for (int i = 0; i < 4; i++) {
        pinMode(SENSOR_PINS[i], INPUT);
    }
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

    int water_ok = digitalRead(FLOAT_PIN) == LOW ? 1 : 0;

    espSerial.print("S:");
    for (int i = 0; i < 4; i++) {
        espSerial.print(soil[i]);
        if (i < 3) espSerial.print('#');
    }
    espSerial.print('#');
    espSerial.print(temp, 1);
    espSerial.print('#');
    espSerial.print(hum, 1);
    espSerial.print('#');
    espSerial.print(water_ok);
    espSerial.print('\n');

    delay(500);
}
