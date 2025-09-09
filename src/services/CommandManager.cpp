//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "CommandManager.h"

#include <ArduinoJson.h>

#include "MongooseCore.h"
#include "model/command.h"

void CommandManager::init() {
    this->stopped = false;

    Mongoose.begin();

    if (this->server.begin(HTTP_PORT)) {
        Serial.println("CommandManager initialized");
        return;
    }


    Serial.print("Error initializing CommandManager on port ");
    Serial.println(HTTP_PORT);
    this->stopped = true;
}

void CommandManager::poll() {
    Mongoose.poll(100);
}

void CommandManager::setup_routes(const Hashtable<String, Route>& routes) {
    for (const auto &path : routes.keys()) {
        const auto route = routes.get(path);
        Serial.print("Setting up route: ");
        Serial.println(path);

        this->server.on(path.c_str(), route->getHttpMethod(), [route](MongooseHttpServerRequest *req) {
            Serial.print("Request received on path: ");
            Serial.println(req->uri().c_str());
            const String body = req->body();
            Serial.print("Request body: ");
            Serial.println(body);

            // const auto curr_route = this->routes.get(req->uri());
            if (route == nullptr) {
                Serial.println("! Error: Route config not found");
                req->send(500, "application/json", R"({"status":"error","error_code":"not_found","message":"Route not found"})");
                return;
            }

            if (!route->hasHandler()) {
                Serial.println("! Error: No handler for this route");
                req->send(500, "application/json", R"({"status":"error","error_code":"no_handler","message":"No handler for this route"})");
                return;
            }

            if (!route->hasPayload()) {
                Serial.println("No payload");
                route->handler(req, std::shared_ptr<ICanBeDeserialized>());
                return;
            }

            Serial.println("Request has payload, parsing...");
            DeserializationError error;
            String error_msg;
            const auto command = route->fromJson(body.c_str(), error, error_msg);
            if (command != nullptr) {
                route->handler(req, command);
            } else {
                Serial.print("! Error: Failed to parse command: ");
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