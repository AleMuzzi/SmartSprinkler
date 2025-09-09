//
// Created by Alessandro Muzzi on 23/08/25.
//

#ifndef STATUS_H
#define STATUS_H

#include <memory>
#include <ArduinoJson.h>

#include "ICanBeDeserialized.h"


class Status: public ICanBeDeserialized {
public:

    Status() = default;

    static std::shared_ptr<ICanBeDeserialized> from_json(const char *json_str, DeserializationError& error, String &error_msg);
    String getType() const override;
};



#endif //STATUS_H
