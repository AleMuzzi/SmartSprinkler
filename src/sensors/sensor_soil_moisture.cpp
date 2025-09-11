//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "sensor_soil_moisture.h"

#include <Arduino.h>


SensorSoilMoisture::SensorSoilMoisture(const uint8_t pin): pin(pin) {
    pinMode(pin, INPUT);
}


float SensorSoilMoisture::getSoilMoisture() const {
    const int sensorValue = analogRead(this->pin); // Read the analog value from the sensor
    Serial.print("Soil moisture reading: ");
    Serial.println(sensorValue);
    // Convert the analog value (0-1023) to a percentage (0-100%)
    return map(sensorValue, 1023, 0, 0, 100);
}
