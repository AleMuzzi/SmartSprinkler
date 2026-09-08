// SmartSprinkler — Nano Sensor Reader
// Reads 4 HW-390 soil moisture sensors + DHT22 + float switch and sends to ESP32-CAM via serial.
// PCB build (WITH_PCB): additionally drives 3 solenoid valves on D6/D7/D8 (active LOW) as
// commanded by the ESP32 via "V:abc\n".

#include <Arduino.h>
#include <SoftwareSerial.h>
#include "sensors/temp_humidity_sensor.h"

const int RX_PIN = 4;
const int TX_PIN = 3;
const int FLOAT_PIN = 5;

#ifdef WITH_PCB
const int VALVE_PINS[3] = {6, 7, 8};
int valve_state[3] = {0, 0, 0};
#endif

const int SENSOR_PINS[4] = {A0, A1, A2, A3};

SoftwareSerial espSerial(RX_PIN, TX_PIN);

#ifdef WITH_PCB
void valves_all_off() {
    for (int i = 0; i < 3; i++) {
        pinMode(VALVE_PINS[i], OUTPUT);
        digitalWrite(VALVE_PINS[i], HIGH); // active LOW: HIGH = off
        valve_state[i] = 0;
    }
}

void handle_serial_command() {
    while (espSerial.available() > 0) {
        if (espSerial.peek() == 'V') {
            espSerial.read(); // 'V'
            if (espSerial.read() != ':') {
                continue;
            }
            char buf[3];
            const int n = espSerial.readBytes(buf, 3);
            const bool valid = (n == 3) &&
                (buf[0] == '0' || buf[0] == '1') &&
                (buf[1] == '0' || buf[1] == '1') &&
                (buf[2] == '0' || buf[2] == '1');
            if (valid) {
                for (int i = 0; i < 3; i++) {
                    valve_state[i] = (buf[i] == '1') ? 1 : 0;
                    digitalWrite(VALVE_PINS[i], valve_state[i] ? LOW : HIGH); // active LOW
                }
            }
        } else {
            espSerial.read(); // skip unknown bytes
        }
        // Drain the rest of the line.
        while (espSerial.available() > 0 && espSerial.peek() != '\n') {
            espSerial.read();
        }
        if (espSerial.peek() == '\n') {
            espSerial.read();
        }
    }
}
#endif

void setup() {
    espSerial.begin(9600);
    TempHumiditySensor::init();
    pinMode(FLOAT_PIN, INPUT_PULLUP);

    for (int i = 0; i < 4; i++) {
        pinMode(SENSOR_PINS[i], INPUT);
    }

#ifdef WITH_PCB
    valves_all_off();
#endif
}

void loop() {
#ifdef WITH_PCB
    handle_serial_command();
#endif

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

    delay(1000);
}