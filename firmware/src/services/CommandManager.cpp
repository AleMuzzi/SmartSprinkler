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

#include "esp32/fw_version.h"
#ifndef FW_VERSION
#define FW_VERSION "0.0.0"
#endif

// Version sentinel embedded in the firmware image. The OTA updater scans an
// uploaded binary for this marker to report the version of the firmware being
// flashed. It is printed at boot (see main.cpp) both so that the linker keeps
// it in the image and so it is visible on the serial monitor.
extern "C" const char FW_IMAGE_VERSION_MARKER[] __attribute__((used)) =
    "SSFWVER:" FW_VERSION;

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

// ── Uploaded-firmware version detection ──────────────────────────────
// The .bin is a raw flash image so it has no "version" header field; instead
// we scan the streamed bytes for the ``SSFWVER:<version>`` sentinel that every
// build embeds in .rodata (see FW_IMAGE_VERSION_MARKER above).

#define FW_VER_MARKER "SSFWVER:"
#define FW_VER_MARKER_LEN 8

static char ota_new_fw_version[20] = {0};
static size_t ota_new_fw_version_len = 0;
static bool ota_scan_done = false;
static size_t ota_scan_match_len = 0;
static bool ota_scan_collecting = false;

static bool ota_is_version_char(char c) {
    return (c >= '0' && c <= '9') || c == '.';
}

// Streaming scanner: the marker and the version digits that follow it may be
// split arbitrarily across OTA upload chunks, so the match/collect state
// persists between calls. The scanner's own "SSFWVER:" constant also lives in
// the image, so a marker that is NOT followed by version digits is treated as
// a false positive and scanning continues.
static void ota_scan_for_version(const uint8_t* data, size_t len) {
    for (size_t i = 0; i < len && !ota_scan_done; i++) {
        const char c = static_cast<char>(data[i]);
        if (ota_scan_collecting) {
            if (ota_is_version_char(c)) {
                if (ota_new_fw_version_len < sizeof(ota_new_fw_version) - 1) {
                    ota_new_fw_version[ota_new_fw_version_len++] = c;
                }
            } else if (ota_new_fw_version_len == 0) {
                ota_scan_collecting = false;
                ota_scan_match_len = (c == FW_VER_MARKER[0]) ? 1 : 0;
            } else {
                ota_scan_done = true;
                ota_new_fw_version[ota_new_fw_version_len] = '\0';
            }
        } else {
            if (c == FW_VER_MARKER[ota_scan_match_len]) {
                ota_scan_match_len++;
                if (ota_scan_match_len == FW_VER_MARKER_LEN) {
                    ota_scan_collecting = true;
                    ota_scan_match_len = 0;
                }
            } else {
                ota_scan_match_len = (c == FW_VER_MARKER[0]) ? 1 : 0;
            }
        }
    }
}

static String ota_uploaded_version_str() {
    return ota_new_fw_version_len > 0 ? String(ota_new_fw_version) : String("unknown");
}

static void ota_write_error(MongooseHttpServerRequest *req) {
    auto *resp = req->beginResponseStream();
    resp->setCode(500);
    resp->setContentType("text/plain");
    resp->printf("Firmware update failed: %d", Update.getError());
    req->send(resp);
    Update.printError(Serial);
    const String new_fw = ota_uploaded_version_str();
    log_event_details(
        "ota", "error", "ota_failed",
        ("OTA update failed: firmware " + new_fw + " error=" +
         String(Update.getError())).c_str(),
        (String("{\"old_fw\":\"") + FW_VERSION + "\",\"new_fw\":\"" +
         new_fw + "\"}").c_str());
}

void CommandManager::setup_ota() {
    Serial.println("Setting up OTA route: /update");

    this->server.on("/update", HTTP_POST)
        ->onRequest([](MongooseHttpServerRequest *req) {
            ota_completed = false;
            ota_received_bytes = 0;
            ota_new_fw_version_len = 0;
            ota_scan_done = false;
            ota_scan_match_len = 0;
            ota_scan_collecting = false;
        })
        ->onUpload([](MongooseHttpServerRequest *req, int ev, MongooseString filename,
                      uint64_t index, uint8_t *data, size_t len) {
            if (ev == MG_EV_HTTP_PART_BEGIN) {
                Serial.printf("OTA start: %s\n", filename.c_str());
                log_event("ota", "info", "ota_started",
                          ("OTA update started: " + String(filename.c_str())).c_str());
                if (!Update.begin()) {
                    ota_write_error(req);
                }
            }

            if (!Update.hasError()) {
                esp_task_wdt_reset();
                ota_scan_for_version(data, len);
                if (Update.write(data, len) != len) {
                    ota_write_error(req);
                }
                ota_received_bytes += len;
            }

            if (ev == MG_EV_HTTP_PART_END) {
                const String new_fw = ota_uploaded_version_str();
                Serial.printf("OTA data finished (%u B)\n", ota_received_bytes);
                if (Update.end(true)) {
                    Serial.printf("OTA success: %u B\n", ota_received_bytes);
                    log_event_details(
                        "ota", "info", "ota_success",
                        ("OTA update completed: firmware " + new_fw + " (" +
                         String(ota_received_bytes) + " B)").c_str(),
                        (String("{\"old_fw\":\"") + FW_VERSION + "\",\"new_fw\":\"" +
                         new_fw + "\"}").c_str());
                    req->send(200, "text/plain", "OK");
                    ota_completed = true;
                } else {
                    ota_write_error(req);
                    log_event_details(
                        "ota", "error", "ota_failed",
                        ("OTA update failed: firmware " + new_fw + " error=" +
                         String(Update.getError())).c_str(),
                        (String("{\"old_fw\":\"") + FW_VERSION + "\",\"new_fw\":\"" +
                         new_fw + "\"}").c_str());
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