//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef COMMAND_H
#define COMMAND_H

#include <memory>
#include <ArduinoJson.h>

#include "ICanBeDeserialized.h"

class Action {
public:
    enum Value {
        STOP = 0,
        START = 1,
        DISPENSE_SPECIFIC_AMOUNT = 2,
    };

    Action() = default;
    Action(const Value v) : value(v) {}

    Value get() const { return value; }

    static Action from_string(const char* str, bool& success);

private:
    Value value;
};

class Target {
public:
    enum Value {
        PEPERONCINO = 0,
        ROSMARINO = 1,
    };

    Target() = default;
    Target(const Value v) : value(v) {}

    Value get() const { return value; }

    static Target from_string(const char* str, bool& success);

private:
    Value value;
};

class Command: public ICanBeDeserialized {
public:

    Command(const Action action, const Target target, const int amount = 0)
        : action(action), target(target), amount(amount) {}

    // region Getters

    Action::Value get_action() const { return this->action.get(); }
    Target::Value get_target() const { return this->target.get(); }
    int get_amount() const { return this->amount; }

    // endregion

    static std::shared_ptr<ICanBeDeserialized> from_json(const char *json_str, DeserializationError& error, String &error_msg);

private:
    Action action;
    Target target;  // target plant
    int amount = 0; // in milliliters (only valid if action is DISPENSE_SPECIFIC_AMOUNT)
};



#endif //COMMAND_H
