//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef ACTUATOR_H
#define ACTUATOR_H

#include <cstdint>


class Actuator {
/**
 * This class represents an actuator (e.g., a pump or a valve)
 */
public:

    explicit Actuator(uint8_t pin);

    void switch_on() const;
    void switch_off() const;
    bool is_on() const;

private:
    uint8_t pin{};

};


#endif //ACTUATOR_H
