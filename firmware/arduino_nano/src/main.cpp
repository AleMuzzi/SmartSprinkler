/*
 * SmartSprinkler — Arduino Nano soil moisture sensor hub
 *
 * Reads 4 HW-390 capacitive soil moisture sensors on A0–A3.
 * Communicates with the ESP32 over its hardware Serial (D0=RX, D1=TX).
 * Responds only to byte 'S' (0x53) with a CSV line of raw ADC values.
 *
 * Wiring:
 *   Nano D0 (RX) → ESP32 GPIO 1 (TX)
 *   Nano D1 (TX) → ESP32 GPIO 3 (RX)
 *   Nano GND     → ESP32 GND
 *   Nano 5V      → 5V rail (shared PSU)
 *   Nano A0      → HW-390 #1 (Habanero)
 *   Nano A1      → HW-390 #2 (Naga Morich)
 *   Nano A2      → HW-390 #3 (Carolina Reaper)
 *   Nano A3      → HW-390 #4 (Rosmarino)
 */

#define SENSOR_A0 A0
#define SENSOR_A1 A1
#define SENSOR_A2 A2
#define SENSOR_A3 A3

#define BAUD_RATE 115200

void setup() {
    Serial.begin(BAUD_RATE);

    pinMode(SENSOR_A0, INPUT);
    pinMode(SENSOR_A1, INPUT);
    pinMode(SENSOR_A2, INPUT);
    pinMode(SENSOR_A3, INPUT);
}

void loop() {
    if (Serial.available() > 0) {
        const byte cmd = Serial.read();
        if (cmd == 'S') {
            Serial.print(analogRead(SENSOR_A0));
            Serial.print(',');
            Serial.print(analogRead(SENSOR_A1));
            Serial.print(',');
            Serial.print(analogRead(SENSOR_A2));
            Serial.print(',');
            Serial.println(analogRead(SENSOR_A3));
        }
    }
}
