//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "route.h"


std::shared_ptr<ICanBeDeserialized> Route::fromJson(const char *json_str, DeserializationError &error, String &error_msg) const {
    return this->_from_json(json_str, error, error_msg);
}

void Route::handler(MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized> &command) const {
    this->_handler(req, command);
}
