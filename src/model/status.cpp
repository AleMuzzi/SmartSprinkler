//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "status.h"

#include <memory>

std::shared_ptr<ICanBeDeserialized> Status::from_json(const char *json_str, DeserializationError& error, String &error_msg) {
    return std::make_shared<ICanBeDeserialized>(Status());
}
