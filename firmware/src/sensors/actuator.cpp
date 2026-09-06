//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "actuator.h"

#include <Arduino.h>

// Relay polarity depends on the hardware:
//   WITH_PCB  — Active LOW  (GPIO LOW energizes the relay; standard PCB
//               relay modules with optocoupler/transistor).
//   Breadboard — Active HIGH (GPIO HIGH energizes the relay; typical
//               prototype relay module).
// Both keep the pump off at boot once switch_off() is called.

Actuator::Actuator(const uint8_t pin): pin(pin) {
    pinMode(pin, OUTPUT);
#ifdef WITH_PCB
    digitalWrite(pin, HIGH); // Active LOW: HIGH = off
#else
    digitalWrite(pin, LOW);  // Active HIGH: LOW = off
#endif
}

void Actuator::switch_on() const {
#ifdef WITH_PCB
    digitalWrite(this->pin, LOW);   // Active LOW: LOW = on
#else
    digitalWrite(this->pin, HIGH);  // Active HIGH: HIGH = on
#endif
}

void Actuator::switch_off() const {
#ifdef WITH_PCB
    digitalWrite(this->pin, HIGH);  // Active LOW: HIGH = off
#else
    digitalWrite(this->pin, LOW);   // Active HIGH: LOW = off
#endif
}

bool Actuator::is_on() const {
#ifdef WITH_PCB
    return digitalRead(this->pin) == LOW;   // Active LOW
#else
    return digitalRead(this->pin) == HIGH;  // Active HIGH
#endif
}
