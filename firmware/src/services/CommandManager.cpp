//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "CommandManager.h"

#include <ArduinoJson.h>
#include <Update.h>
#include <esp_task_wdt.h>

#include "MongooseCore.h"
#include "esp32/log.h"
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
            const String uri = req->uri().toString();
            Serial.println(uri.substring(0, uri.indexOf(' ')));
            const String body = req->body();
            // Serial.print("Request body: ");
            // Serial.println(body);

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
                route->handler(req, std::shared_ptr<ICanBeDeserialized>());
                return;
            }

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

bool ota_completed = false;
size_t ota_received_bytes = 0;

static void ota_write_error(MongooseHttpServerRequest *req) {
    auto *resp = req->beginResponseStream();
    resp->setCode(500);
    resp->setContentType("text/plain");
    resp->printf("Firmware update failed: %d", Update.getError());
    req->send(resp);
    Update.printError(Serial);
    log_event("ota", "error", "ota_failed", String("OTA update failed: " + String(Update.getError())).c_str());
}

void CommandManager::setup_ota() {
    Serial.println("Setting up OTA route: /update");

    this->server.on("/update", HTTP_POST)
        ->onRequest([](MongooseHttpServerRequest *req) {
            ota_completed = false;
            ota_received_bytes = 0;
        })
        ->onUpload([](MongooseHttpServerRequest *req, int ev, MongooseString filename,
                      uint64_t index, uint8_t *data, size_t len) {
            if (ev == MG_EV_HTTP_PART_BEGIN) {
                Serial.printf("OTA start: %s\n", filename.c_str());
                log_event("ota", "info", "ota_started", ("OTA update started: " + String(filename.c_str())).c_str());
                if (!Update.begin()) {
                    ota_write_error(req);
                }
            }

            if (!Update.hasError()) {
                esp_task_wdt_reset();
                if (Update.write(data, len) != len) {
                    ota_write_error(req);
                }
                ota_received_bytes += len;
            }

            if (ev == MG_EV_HTTP_PART_END) {
                Serial.printf("OTA data finished (%u B)\n", ota_received_bytes);
                if (Update.end(true)) {
                    Serial.printf("OTA success: %u B\n", ota_received_bytes);
                    log_event("ota", "info", "ota_success", ("OTA update completed (" + String(ota_received_bytes) + " B)").c_str());
                    req->send(200, "text/plain", "OK");
                    ota_completed = true;
                } else {
                    ota_write_error(req);
                    log_event("ota", "error", "ota_failed", String("OTA update failed: " + String(Update.getError())).c_str());
                }
            }

            return len;
        })
        ->onClose([](MongooseHttpServerRequest *req) {
            if (ota_completed) {
                Serial.println("OTA complete, rebooting...");
                ESP.restart();
            }
        });
}