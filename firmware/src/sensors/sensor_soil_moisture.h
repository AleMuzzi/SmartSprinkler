//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef SENSOR_SOIL_MOISTURE_H
#define SENSOR_SOIL_MOISTURE_H

#include "Arduino.h"

class SensorSoilMoisture {
public:
    explicit SensorSoilMoisture(uint8_t pin);

    float getSoilMoisture() const;

private:
    uint8_t pin;
};

#endif //SENSOR_SOIL_MOISTURE_H
