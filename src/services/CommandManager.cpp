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
    this->setup_routes();

    Serial.println("CommandManager initialized");
}

void CommandManager::poll() {
    Mongoose.poll(100);
}

void CommandManager::process_command(const Command &command) {
    // Process the received command
    switch (command.get_action()) {
        case Action::STOP:
            // Stop dispensing
            Serial.println("Stopping dispensing.");
            break;
        case Action::START:
            // Start dispensing
            Serial.println("Starting dispensing.");
            break;
        case Action::DISPENSE_SPECIFIC_AMOUNT:
            // Dispense specific amount
            Serial.print("Dispensing ");
            Serial.print(command.get_amount());
            Serial.println(" ml.");
            break;
        default:
            Serial.println("Unknown command action.");
            break;
    }
}

void CommandManager::setup_routes() {
    this->server.on("/command", HTTP_POST, [this](MongooseHttpServerRequest *req) {
        Serial.println("Command request received");
        const String body = req->body();
        Serial.print("Received HTTP command: ");
        Serial.println(body);

        DeserializationError error;
        String error_msg;
        const auto command = Command::from_json(body.c_str(), error, error_msg);
        if (command != nullptr) {
            process_command(*command);
            req->send(200, "application/json", R"({"status":"ok"})");
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