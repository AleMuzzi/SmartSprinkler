//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "actuator.h"

#include <Arduino.h>
#include <cstdint>

Actuator::Actuator(const uint8_t pin): pin(pin) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW); // Ensure the actuator is off initially
}

void Actuator::switch_on() const {
    digitalWrite(this->pin, HIGH);
}

void Actuator::switch_off() const {
    digitalWrite(this->pin, LOW);
}

bool Actuator::is_on() const {
    return digitalRead(this->pin) == HIGH;
}
