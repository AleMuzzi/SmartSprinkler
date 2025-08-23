//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "CommandManager.h"

#include <ArduinoJson.h>

#include "MongooseCore.h"

void CommandManager::init() {
    this->stopped = false;

    // char* error = nullptr;
    // const int res = this->udp_server.init(error);
    // if (res < 0) {
    //     Serial.print("Failed to initialize UDP server: ");
    //     Serial.println(error);
    // }
    Mongoose.begin();
    this->server.begin(HTTP_PORT);

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
    Serial.println("CommandManager initialized");

}

void CommandManager::start_async() {
            Mongoose.poll(100);

    // Start the UDP server in a separate thread
    // BaseType_t udp_server_task = xTaskCreate(
    //     [](void* param) {
    //         Mongoose.poll(1000);
    //
    //         // auto* self = static_cast<CommandManager*>(param);
    //         // while (!self->stopped) {
    //         //     char buffer[MAX_BUFFER_SIZE];
    //         //
    //         //     if (self->udp_server.check_for_data(buffer)) {
    //         //         Serial.print("Received data: ");
    //         //         Serial.println(buffer);
    //         //
    //         //         DeserializationError error;
    //         //         auto command = Command::from_json(buffer, error);
    //         //         if (command != nullptr) {
    //         //             process_command(*command);
    //         //         } else {
    //         //             Serial.print("Failed to parse command: ");
    //         //             Serial.println(error.c_str());
    //         //         }
    //         //     }
    //         //     delay(500);
    //         // }
    //     },
    //     "MongooseServerTask",
    //     4096,
    //     nullptr,
    //     1,
    //     &this->xHandle
    // );
    //
    // if( udp_server_task != pdPASS )
    // {
    //     Serial.println("Failed to create UDP server task");
    // }
}

void CommandManager::stop() {
    this->stopped = true;
    if (xHandle != nullptr) {
        vTaskDelete( xHandle );
    }
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