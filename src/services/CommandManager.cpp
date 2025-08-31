//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "CommandManager.h"

#include <ArduinoJson.h>

#include "MongooseCore.h"

void CommandManager::init() {
    this->stopped = false;

    Mongoose.begin();

    this->server.begin(HTTP_PORT);

    Serial.println("CommandManager initialized");
}

void CommandManager::poll() {
    Mongoose.poll(100);
}

void CommandManager::setup_routes(const Hashtable<String, Route>& routes) {
    for (const auto &path : routes.keys()) {
        const auto route = routes.get(path);

        this->server.on(path.c_str(), HTTP_POST, [route](MongooseHttpServerRequest *req) {
            Serial.println("Command request received");
            const String body = req->body();
            Serial.print("Received HTTP command: ");
            Serial.println(body);

            DeserializationError error;
            String error_msg;
            const auto command = route->fromJson(body.c_str(), error, error_msg);
            if (command != nullptr) {
                route->handler(req, command);
            } else {
                Serial.print("Failed to parse command: ");
                Serial.println(error.c_str());
                req->send(
                    400,
                    "application/json",
                    R"({"status":"error","error_code":")" + String(error.c_str()) + R"(","message":")" + error_msg + "\"}"
                );
            }
        });
    }
}