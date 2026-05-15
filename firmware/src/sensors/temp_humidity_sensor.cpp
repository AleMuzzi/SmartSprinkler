//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "temp_humidity_sensor.h"

#include <DHT_U.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>


// Variables for sensor readings
DHT_Unified dht_temp_humidity(DHTPIN, DHTTYPE);

void TempHumiditySensor::init() {
    dht_temp_humidity.begin();
}

float TempHumiditySensor::getTemperature() {
    sensors_event_t event;
    dht_temp_humidity.temperature().getEvent(&event);
    if (isnan(event.temperature)) {
        Serial.println("Error reading temperature!");
    }

    return event.temperature;
}

float TempHumiditySensor::getHumidity() {
    sensors_event_t event;
    dht_temp_humidity.humidity().getEvent(&event);
    if (isnan(event.relative_humidity)) {
        Serial.println("Error reading humidity!");
    }

    return event.relative_humidity;
}