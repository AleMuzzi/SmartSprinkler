//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "command.h"

#include <memory>

Action Action::from_string(const char* str, bool& success) {
    if (strcmp(str, "STOP") == 0) {
        success = true;
        return STOP;
    }
    if (strcmp(str, "START") == 0) {
        success = true;
        return START;
    }
    if (strcmp(str, "DISPENSE_SPECIFIC_AMOUNT") == 0) {
        success = true;
        return DISPENSE_SPECIFIC_AMOUNT;
    }

    success = false;
    return STOP;
}

Target Target::from_string(const char* str, bool& success) {
    if (strcmp(str, "PEPERONCINO") == 0) {
        success = true;
        return PEPERONCINO;
    }
    if (strcmp(str, "ROSMARINO") == 0) {
        success = true;
        return ROSMARINO;
    }

    success = false;
    return PEPERONCINO;
}

std::shared_ptr<ICanBeDeserialized> Command::from_json(const char *json_str, DeserializationError& error, String &error_msg) {
    JsonDocument doc;
    error = deserializeJson(doc, json_str);

    if (error) {
        return nullptr;
    }

    bool conversion_success;
    const Action action = Action::from_string(doc["action"], conversion_success);
    if (!conversion_success) {
        error = DeserializationError::InvalidInput;
        error_msg = "Invalid 'action' value: " + doc["action"].as<String>();
        return nullptr;
    }

    const Target target = Target::from_string(doc["target"], conversion_success);
    if (!conversion_success) {
        error = DeserializationError::InvalidInput;
        error_msg = "Invalid 'target' value: " + doc["target"].as<String>();
        return nullptr;
    }

    if(!doc["amount"].is<int>()) {
        error = DeserializationError::InvalidInput;
        error_msg = "Invalid 'amount' value: must be an integer";
        return nullptr;
    }


    return std::make_shared<ICanBeDeserialized>(Command(
        action,
        target,
        doc["amount"].as<int>()
        ));
}
