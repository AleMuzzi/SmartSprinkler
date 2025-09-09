//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef ACTUATOR_H
#define ACTUATOR_H



class Actuator {
/**
 * This class represents an actuator (e.g., a pump or a valve)
 */
public:

    explicit Actuator(int pin);

    void switch_on() const;
    void switch_off() const;
    bool is_on() const;

private:
    // :
    // - params to config it
    // - methods to control it
    int pin;

};



#endif //ACTUATOR_H
