//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef ICANBEDESERIALIZED_H
#define ICANBEDESERIALIZED_H


#include "ArduinoJson.h"

class ICanBeDeserialized {
public:
    virtual ~ICanBeDeserialized() = default;

    static std::shared_ptr<ICanBeDeserialized> from_json(const char *json_str, DeserializationError& error, String &error_msg);

    virtual String getType() const {
        throw std::runtime_error("getType() not implemented");
    };
};

#endif //ICANBEDESERIALIZED_H
