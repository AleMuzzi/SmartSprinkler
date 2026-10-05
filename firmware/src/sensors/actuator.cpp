//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "actuator.h"

#include <Arduino.h>

// Relay polarity: Active HIGH (GPIO HIGH energizes the relay; NPN transistor
// driver on the PCB, or typical prototype relay module on breadboard).
// Keeps the pump off at boot once switch_off() is called.

Actuator::Actuator(const uint8_t pin): pin(pin) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
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
