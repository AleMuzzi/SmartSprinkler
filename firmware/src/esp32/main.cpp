//
// Created by Alessandro Muzzi on 23/03/25.
//

#include <WiFi.h>
#include <utils/string.h>
#include <utils/time.h>

#include <U8g2lib.h>

#include "model/command.h"
#include "model/status.h"
#include "model/route.h"
#include "sensors/actuator.h"

#include "camera.h"
#include "sensors/temp_humidity_sensor.h"
#include "services/CommandManager.h"
#include "utils/hashtable_ext.h"

#include <ESP32Servo.h>
#include <HardwareSerial.h>
#include <Preferences.h>
#include <esp_system.h>
#include <esp_task_wdt.h>

#include "esp32/event_log.h"
#include "esp32/event_publisher.h"
#include "esp32/log.h"

#if __has_include("server_config.h")
#include "server_config.h"
#endif
#ifndef SMARTSPRINKLER_SERVER_URL
#define SMARTSPRINKLER_SERVER_URL ""
#endif

#if __has_include("fw_version.h")
#include "fw_version.h"
#endif
#ifndef FW_VERSION
#define FW_VERSION "0.0.0"
#endif

extern "C" const char FW_IMAGE_VERSION_MARKER[];

#define PIN_PUMP_RELAY 12
#define PIN_ROTARY_SERVO 13

#define SERVO_MIN_US 500
#define SERVO_MAX_US 2500
#define SERVOFreq 50

#define ROTARY_DELTA_DEG 19.0f
#define ROTARY_START_DEG  5.0f
#define ROTARY_POSITION_COUNT 6

#define FLOW_RATE_ML_PER_MIN 1380
// Safety net: force the pump off if it stays on longer than this (avoids
// a runaway pump when a START is never followed by a STOP, e.g. backend
// crash or a lost network connection).
#define MAX_PUMP_ON_MS (5UL * 60UL * 1000UL)

#define NANO_RX_PIN 14
#define NANO_TX_PIN 15
#define SOIL_DRY_ADC 1000

#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#endif

#ifndef WIFI_SSID_LOCAL
#define WIFI_SSID_LOCAL ""
#endif
#ifndef WIFI_PASSWORD_LOCAL
#define WIFI_PASSWORD_LOCAL ""
#endif

constexpr char hostname[16] = "smart_sprinkler";

Preferences prefs;
String wifi_ssid;
String wifi_password;

const IPAddress local_IP(192, 168, 1, 10);
const IPAddress gateway(192, 168, 1, 1);
const IPAddress subnet(255, 255, 255, 0);

String WiFiAddr = "";

unsigned long previousMillis = 0;
constexpr long interval = 2000;

float air_temperature = -1;
float air_humidity = -1;
float soil_moisture;

CommandManager command_manager;
Hashtable<String, Route> routes;

const Actuator water_pump(PIN_PUMP_RELAY);
Servo rotary_servo;

Target::Value active_target = Target::NAGA_MORICH;
int rotary_current_position = 0;
bool rotary_calibrated = false;

int soil_moisture_raw[4] = {0, 0, 0, 0};
bool nano_connected = false;

HardwareSerial NanoSerial(2);

bool water_low_alert = false;
int blocked_amount_ml = 0;

bool dispensing_specific = false;
int dispensing_target_ml = 0;
unsigned long dispensing_start_ms = 0;
bool pump_start_pending = false;
unsigned long pump_start_planned_ms = 0;
unsigned long pump_started_ms = 0;

bool calibration_in_progress = false;
int calibration_step = 0;
bool calibration_all_success = true;
unsigned long calibration_moved_at_ms = 0;

EventLog event_log;
EventPublisher event_publisher(&event_log);

// Edge detection for sensor-derived alerts.
bool prev_water_low_alert = false;
bool prev_sensor_reading_valid = true;
uint32_t last_sensor_warn_ms = 0;
uint32_t last_nano_data_ms = 0;
bool nano_lost_logged = false;

void log_event(const char* category, const char* level, const char* event, const char* message) {
    event_log.append(category, level, event, message);
    Serial.printf("[%s] %s\n", event, message);
}

void log_event_details(const char* category, const char* level, const char* event,
                       const char* message, const char* details_json) {
    event_log.appendDetails(category, level, event, message, details_json);
    Serial.printf("[%s] %s\n", event, message);
}

static const char* reset_reason_str() {
    switch (esp_reset_reason()) {
        case ESP_RST_POWERON:   return "power_on";
        case ESP_RST_EXT:       return "external_pin";
        case ESP_RST_SW:        return "software_reset";
        case ESP_RST_PANIC:     return "exception_panic";
        case ESP_RST_INT_WDT:   return "interrupt_watchdog";
        case ESP_RST_TASK_WDT:  return "task_watchdog";
        case ESP_RST_WDT:       return "watchdog";
        case ESP_RST_DEEPSLEEP: return "deep_sleep";
        case ESP_RST_BROWNOUT:  return "brownout";
        case ESP_RST_SDIO:      return "sdio";
        default:                return "unknown";
    }
}

void startCameraServer();
void reply_invalid_payload(MongooseHttpServerRequest *req);
bool process_command(const std::shared_ptr<Command> &command, String& error_msg);
void plant_to_servo(Target::Value target);
const char* target_to_string(Target::Value target);
void read_nano_soil_moistures();
int servo_degrees_to_us(float degrees);
void begin_calibration();
void tick_calibration();
void move_servo_to_position(int position);
void tick_dispensing();
void schedule_pump_start();
void load_wifi_credentials();
void on_wifi_connected(WiFiEvent_t event);
void on_wifi_disconnected(WiFiEvent_t event);
void handle_serial_command();
void init_time_ntp();
String load_server_url();

void setup_command_routes();

void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println();

    Serial.println("###############################");
    Serial.println("#       Smart Sprinkler       #");
    Serial.println("###############################");
    Serial.println();

    esp_task_wdt_init(10, true);
    esp_task_wdt_add(NULL);

    load_wifi_credentials();

    init_time_ntp();

    event_log.begin();
    String server_url = load_server_url();
    event_publisher.setServerUrl(server_url);
    Serial.print("Server URL: ");
    Serial.println(server_url.length() ? server_url
                                       : "(unset - publishing disabled; use 'SERVER <url>')");
    if (server_url.length() == 0) {
        log_event("network", "warn", "publisher_disabled",
                  "No server URL configured: ESP event publishing disabled");
    }
    log_event_details(
        "system", "info", "boot",
        String("Smart Sprinkler firmware " + String(FW_VERSION)).c_str(),
        (String("{\"reset_reason\":\"") + reset_reason_str() + "\"}").c_str());

    // Camera::init();

    Serial.print("Device's MAC Address: ");
    Serial.println(WiFi.macAddress());

    WiFi.onEvent(on_wifi_connected, ARDUINO_EVENT_WIFI_STA_GOT_IP);
    WiFi.onEvent(on_wifi_disconnected, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);

    WiFi.mode(WIFI_MODE_STA);
    WiFi.setHostname(hostname);
    WiFi.begin(wifi_ssid.c_str(), wifi_password.c_str());

    Serial.print("Connecting to WiFi");
    const unsigned long wifi_timeout_start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - wifi_timeout_start < 20000) {
        delay(200);
        esp_task_wdt_reset();
        Serial.print(".");
    }
    if (WiFi.status() == WL_CONNECTED) {
        WiFiAddr = WiFi.localIP().toString();
        Serial.print(format("Server Ready! Use 'http://%s' to connect\n", WiFiAddr));
        log_event("network", "info", "wifi_connected", ("WiFi connected, IP " + WiFiAddr).c_str());
    } else {
        Serial.println("\n! WiFi not connected — restarting connection in background (reconnect handler active).");
        WiFiAddr = String(hostname) + ".local";
        log_event("network", "error", "wifi_connect_failed", "WiFi not connected at boot");
    }

    water_pump.switch_off();

    rotary_servo.attach(PIN_ROTARY_SERVO, SERVO_MIN_US, SERVO_MAX_US);
    Serial.println("Rotary servo attached (GPIO 13)");

    begin_calibration();

    NanoSerial.begin(9600, SERIAL_8N1, NANO_RX_PIN, NANO_TX_PIN);
    Serial.println("Nano UART2 initialized (RX=14, TX=15)");

    command_manager.init();
    setup_command_routes();
    command_manager.setup_ota();

    Serial.print("Smart Sprinkler firmware ");
    Serial.println(FW_VERSION);
    Serial.print("firmware marker: ");
    Serial.println(FW_IMAGE_VERSION_MARKER);

    log_event("system", "info", "ready", "System fully initialized");
    Serial.println("\n\nSystem Fully Initialized!");
    Serial.println("-------------------------------");
}

void loop() {
    esp_task_wdt_reset();

    const unsigned long currentMillis = millis();

    tick_calibration();

    if (currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis;
        read_nano_soil_moistures();

        if (nano_connected && !nano_lost_logged && millis() - last_nano_data_ms > 6000) {
            nano_lost_logged = true;
            nano_connected = false;
            log_event("sensor", "error", "sensor_nano_lost", "Nano sensor data lost");
        } else if (!nano_connected && !nano_lost_logged && last_nano_data_ms != 0 &&
                   millis() - last_nano_data_ms > 30000) {
            // Received data at some point but nothing for 30s.
            nano_lost_logged = true;
            log_event("sensor", "error", "sensor_nano_lost", "Nano sensor data lost");
        } else if (!nano_connected && !nano_lost_logged && last_nano_data_ms == 0 &&
                   millis() > 60000) {
            // Never received a single line since boot — Nano/UART unreachable.
            nano_lost_logged = true;
            log_event("sensor", "error", "sensor_nano_no_data", "No Nano sensor data since boot");
        }

        Serial.printf("[%lu] T=%.1f H=%.1f SM=[%d,%d,%d,%d] WL=%s\n",
            currentMillis / 1000,
            air_temperature, air_humidity,
            soil_moisture_raw[0], soil_moisture_raw[1],
            soil_moisture_raw[2], soil_moisture_raw[3],
            water_low_alert ? "LOW" : "OK");
    }

    if (!command_manager.is_stopped()) {
        command_manager.poll();
    }

    tick_dispensing();
    event_publisher.tick();
    handle_serial_command();

    delay(10);
}

static void sendCorsJson(MongooseHttpServerRequest *req, int code, const char *content) {
    auto *resp = req->beginResponseStream();
    resp->setCode(code);
    resp->addHeader("Access-Control-Allow-Origin", "*");
    resp->setContentType("application/json");
    resp->write((const uint8_t*)content, strlen(content));
    req->send(resp);
}

static void sendPlainText(MongooseHttpServerRequest *req, int code, const String& text) {
    auto *resp = req->beginResponseStream();
    resp->setCode(code);
    resp->addHeader("Access-Control-Allow-Origin", "*");
    resp->setContentType("text/plain; charset=utf-8");
    resp->write((const uint8_t*)text.c_str(), text.length());
    req->send(resp);
}

static String getQueryParam(const String& query, const char* name) {
    const String key = String(name) + "=";
    int pos = 0;
    while (pos < query.length()) {
        const int amp = query.indexOf('&', pos);
        const String kv = (amp < 0) ? query.substring(pos) : query.substring(pos, amp);
        if (kv.startsWith(key)) {
            return kv.substring(key.length());
        }
        if (amp < 0) break;
        pos = amp + 1;
    }
    return "";
}

// Parses "YYYY-MM-DD" into the compact "YYYYMMDD" used for the day-file names.
// Returns "" when the value is malformed or not a real calendar date.
static String parseLogDate(const String& value) {
    if (value.length() != 10 || value[4] != '-' || value[7] != '-') {
        return "";
    }
    for (int i = 0; i < 10; i++) {
        if (i == 4 || i == 7) continue;
        if (value[i] < '0' || value[i] > '9') return "";
    }
    const int year = value.substring(0, 4).toInt();
    const int month = value.substring(5, 7).toInt();
    const int day = value.substring(8, 10).toInt();
    if (month < 1 || month > 12 || day < 1) return "";
    static const uint8_t days_in_month[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    int max_day = days_in_month[month - 1];
    if (month == 2 && ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0)) {
        max_day = 29;
    }
    if (day > max_day) return "";
    return value.substring(0, 4) + value.substring(5, 7) + value.substring(8, 10);
}

static void sendLogsPlain(MongooseHttpServerRequest *req) {
    const String query = req->queryString().toString();

    // ``?limit=N`` controls how many trailing lines are returned.
    size_t limit = 300;
    const String limit_str = getQueryParam(query, "limit");
    if (limit_str.length() > 0) {
        const long parsed = limit_str.toInt();
        if (parsed > 0) limit = static_cast<size_t>(parsed);
    }

    // ``?date=YYYY-MM-DD`` selects a specific day file; without it the current
    // day (or pre-sync) logs are returned.
    const String date_value = getQueryParam(query, "date");
    if (date_value.length() > 0) {
        const String compact = parseLogDate(date_value);
        if (compact.length() == 0) {
            sendPlainText(req, 400,
                          "Invalid date format. Correct format: YYYY-MM-DD "
                          "(example: ?date=2026-08-16)\n");
            return;
        }
        String text = event_log.logsForDatePlain(compact, limit);
        if (text.length() == 0) {
            text = String("# esp_") + compact + ".log: no logs for this date\n";
        }
        sendPlainText(req, 200, text);
        return;
    }

    sendPlainText(req, 200, event_log.recentLogsPlain(limit));
}

void setup_command_routes() {
    routes.put("/health", Route{
                .http_method = HTTP_GET,
                .from_json = nullptr,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    sendCorsJson(req, 200, (String(R"({"status":"ok","version":")") + FW_VERSION + "\"}").c_str());
                }
            });
    routes.put("/water_alert", Route{
                .http_method = HTTP_GET,
                .from_json = nullptr,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    sendCorsJson(req, 200, water_low_alert ? R"({"alert":true})" : R"({"alert":false})");
                }
            });
    routes.put("/command", Route{
                .http_method = HTTP_POST,
                .from_json = Command::from_json,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    const auto curr_command = std::static_pointer_cast<Command>(command);

                    if (curr_command->getType() != "Command") {
                        reply_invalid_payload(req);
                        return;
                    }

                    String error_msg;
                    const String details =
                        String("{\"action\":\"") + Action::to_string(curr_command->get_action()) +
                        "\",\"target\":\"" + Target::to_string(curr_command->get_target()) +
                        "\",\"amount\":" + String(curr_command->get_amount()) +
                        ",\"force\":" + (curr_command->get_force() ? "true" : "false") + "}";

                    log_event_details("command", "debug", "command_received", "Command received", details.c_str());

                    if (process_command(curr_command, error_msg)) {
                        log_event_details("command", "debug", "command_accepted", "Command accepted", details.c_str());
                        sendCorsJson(req, 200, R"({"status":"ok"})");
                        return;
                    }

                    log_event_details("command", "warn", "command_rejected", error_msg.c_str(), details.c_str());
                    sendCorsJson(req, 400, (String(R"({"status":"error","error_code":"invalid_command","message":")") + error_msg + "\"}").c_str());
                }
            });
    routes.put("/status", Route{
                .http_method = HTTP_GET,
                .from_json = nullptr,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    Hashtable<String, String> status;
                    status.put("status", "ok");
                    status.put("air_temperature", String(air_temperature, 2));
                    status.put("air_humidity", String(air_humidity, 2));
                    status.put("soil_moisture", String(soil_moisture, 2));
                    status.put("water_pump", water_pump.is_on() ? "on" : "off");
                    status.put("rotary_position", rotary_calibrated ? String(rotary_current_position) : "uncalibrated");
                    status.put("soil_moisture_0", String(constrain(map(soil_moisture_raw[0], SOIL_DRY_ADC, 0, 0, 100), 0, 100)));
                    status.put("soil_moisture_1", String(constrain(map(soil_moisture_raw[1], SOIL_DRY_ADC, 0, 0, 100), 0, 100)));
                    status.put("soil_moisture_2", String(constrain(map(soil_moisture_raw[2], SOIL_DRY_ADC, 0, 0, 100), 0, 100)));
                    status.put("soil_moisture_3", String(constrain(map(soil_moisture_raw[3], SOIL_DRY_ADC, 0, 0, 100), 0, 100)));
                    status.put("water_low_alert", water_low_alert ? "on" : "off");
                    status.put("blocked_amount_ml", String(blocked_amount_ml));
                    status.put("active_plant", water_pump.is_on() ? target_to_string(active_target) : "null");
                    status.put("camera_url", (WiFiAddr + ":81/stream").c_str());

                    String statusJson = hashtable_to_string(status);
                    sendCorsJson(req, 200, statusJson.c_str());
                }
            });
    routes.put("/logs", Route{
                .http_method = HTTP_GET,
                .from_json = nullptr,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    sendLogsPlain(req);
                }
            });
    command_manager.setup_routes(routes);
}

void reply_invalid_payload(MongooseHttpServerRequest *req) {
    sendCorsJson(req, 400, R"({"status":"error","error_code":"invalid_payload","message":"Invalid payload type"})");
}

int servo_degrees_to_us(float degrees) {
    const float range_us = SERVO_MAX_US - SERVO_MIN_US;
    return SERVO_MIN_US + static_cast<int>((degrees / 180.0f) * range_us);
}

float servo_position_to_degrees(int position) {
    return ROTARY_START_DEG + (position * ROTARY_DELTA_DEG);
}

void move_servo_to_position(int position) {
    if (position < 0 || position >= ROTARY_POSITION_COUNT) {
        Serial.print("Invalid position: ");
        Serial.println(position);
        return;
    }
    const float angle = servo_position_to_degrees(position);
    const int us = servo_degrees_to_us(angle);
    rotary_servo.writeMicroseconds(us);
    rotary_current_position = position;
    Serial.print("Servo moved to position ");
    Serial.print(position);
    Serial.print(" (");
    Serial.print(angle);
    Serial.print(" deg, ");
    Serial.print(us);
    Serial.println(" us)");
}

void begin_calibration() {
    Serial.println("Starting rotary calibration (non-blocking)...");
    log_event("system", "info", "calibration_started", "Rotary calibration started");
    calibration_in_progress = true;
    calibration_step = 0;
    calibration_all_success = true;
    calibration_moved_at_ms = millis();
    move_servo_to_position(0);
}

void tick_calibration() {
    if (!calibration_in_progress) {
        return;
    }

    const unsigned long now = millis();
    if (now - calibration_moved_at_ms < 800) {
        return;
    }

    const int position = calibration_step;
    const float angle = servo_position_to_degrees(position);
    const int target_us = servo_degrees_to_us(angle);
    const int actual_us = rotary_servo.readMicroseconds();
    const int error = abs(actual_us - target_us);

    if (error > 100) {
        Serial.print("Calibration warning at position ");
        Serial.print(position);
        Serial.print(": expected ");
        Serial.print(target_us);
        Serial.print(" us, got ");
        Serial.print(actual_us);
        Serial.print(" us (error ");
        Serial.print(error);
        Serial.println(" us)");
        calibration_all_success = false;
    } else {
        Serial.print("Position ");
        Serial.print(position);
        Serial.print(" OK (");
        Serial.print(actual_us);
        Serial.println(" us)");
    }

    calibration_step++;
    if (calibration_step >= ROTARY_POSITION_COUNT) {
        calibration_in_progress = false;
        if (calibration_all_success) {
            rotary_calibrated = true;
            log_event("system", "info", "calibration_completed", "Rotary calibration SUCCESS");
            Serial.println("Rotary calibration: SUCCESS — all positions verified");
        } else {
            rotary_calibrated = false;
            log_event("system", "warn", "calibration_partial", "Rotary calibration PARTIAL — using software tracking");
            Serial.println("Rotary calibration: PARTIAL — using software tracking");
        }
        rotary_current_position = 0;
        rotary_servo.writeMicroseconds(servo_degrees_to_us(0));
        return;
    }

    calibration_moved_at_ms = now;
    move_servo_to_position(calibration_step);
}

void plant_to_servo(Target::Value target) {
    int position;
    switch (target) {
        case Target::HABANERO:      position = 4; break;
        case Target::NAGA_MORICH:   position = 3; break;
        case Target::CAROLINA_REAPER: position = 2; break;
        case Target::ROSMARINO:     position = 1; break;
        default: position = 0;
    }
    move_servo_to_position(position);
}

const char* target_to_string(const Target::Value target) {
    switch (target) {
        case Target::HABANERO:      return "HABANERO";
        case Target::NAGA_MORICH:   return "NAGA_MORICH";
        case Target::CAROLINA_REAPER: return "CAROLINA_REAPER";
        case Target::ROSMARINO:     return "ROSMARINO";
    }
    return "UNKNOWN";
}

#define NANO_LINE_MAX 64
static char nano_line[NANO_LINE_MAX];
static int nano_line_idx = 0;

static void parse_nano_line(const char* line) {
    if (line == nullptr || line[0] != 'S') {
        while (NanoSerial.available()) NanoSerial.read();
        nano_line_idx = 0;
        return;
    }
    int s0, s1, s2, s3, water_ok;
    float temp, hum;
    if (sscanf(line, "S:%d#%d#%d#%d#%f#%f#%d", &s0, &s1, &s2, &s3, &temp, &hum, &water_ok) == 7) {
        soil_moisture_raw[0] = s0;
        soil_moisture_raw[1] = s1;
        soil_moisture_raw[2] = s2;
        soil_moisture_raw[3] = s3;
        const bool low = (water_ok == 0);
        if (low != prev_water_low_alert) {
            prev_water_low_alert = low;
            water_low_alert = low;
            if (low) {
                log_event("alert", "warn", "water_low_on", "Water level low (float switch)");
            } else {
                log_event("alert", "info", "water_low_off", "Water level restored");
            }
        } else {
            water_low_alert = low;
        }
        const bool temp_ok = (temp != -1);
        const bool hum_ok = (hum != -1);
        const bool fully_valid = temp_ok && hum_ok;
        if (!fully_valid) {
            // Log on the valid→invalid transition and then every ~15s while the
            // problem persists, always with the values + raw line so we can tell
            // whether the Nano is sending -1 or the parse is failing.
            if (prev_sensor_reading_valid || millis() - last_sensor_warn_ms > 15000) {
                last_sensor_warn_ms = millis();
                const String details = String("{\"temp\":") + String(temp, 2) +
                    ",\"hum\":" + String(hum, 2) +
                    ",\"raw\":\"" + String(line) + "\"}";
                log_event_details("sensor", "warn", "sensor_invalid_reading",
                                  "Invalid temperature/humidity reading from Nano",
                                  details.c_str());
            }
        }
        prev_sensor_reading_valid = fully_valid;
        // Update each channel independently: a single bad reading on one
        // sensor (e.g. an intermittent DHT humidity drop-out) must not freeze
        // the other channel on its previous value.
        if (temp_ok) {
            air_temperature = temp;
        }
        if (hum_ok) {
            air_humidity = hum;
        }
        last_nano_data_ms = millis();
        if (nano_lost_logged) {
            nano_lost_logged = false;
        }
    } else {
        if (millis() - last_sensor_warn_ms > 15000) {
            last_sensor_warn_ms = millis();
            const String details = String("{\"raw\":\"") + String(line) + "\"}";
            log_event_details("sensor", "warn", "sensor_nano_parse_error",
                              "Malformed Nano sensor line", details.c_str());
        }
    }
}

void read_nano_soil_moistures() {
    while (NanoSerial.available()) {
        const char c = NanoSerial.read();
        if (c == '\n') {
            nano_line[nano_line_idx] = '\0';
            if (nano_line_idx > 0) {
                parse_nano_line(nano_line);
            }
            nano_line_idx = 0;
        } else if (c != '\r' && nano_line_idx < NANO_LINE_MAX - 1) {
            nano_line[nano_line_idx++] = c;
        } else if (nano_line_idx >= NANO_LINE_MAX - 1) {
            nano_line_idx = 0;
        }
    }
    if (!nano_connected && nano_line_idx > 0) {
        nano_connected = true;
        nano_lost_logged = false;
        log_event("sensor", "info", "sensor_nano_connected", "Nano sensor data received");
        Serial.println("Nano sensor data received");
    }
    const int avg_raw = (soil_moisture_raw[0] + soil_moisture_raw[1] +
                         soil_moisture_raw[2] + soil_moisture_raw[3]) / 4;
    soil_moisture = constrain(map(avg_raw, SOIL_DRY_ADC, 0, 0, 100), 0, 100);
}

bool process_command(const std::shared_ptr<Command> &command, String& error_msg) {
    if (calibration_in_progress) {
        error_msg = "Rotary calibration in progress — try again in a few seconds.";
        Serial.println(error_msg);
        return false;
    }

    switch (command->get_action()) {
        case Action::STOP:
            Serial.println("Stopping dispensing.");
            dispensing_specific = false;
            dispensing_target_ml = 0;
            pump_start_pending = false;
            water_pump.switch_off();
            break;
        case Action::START:
            if (water_low_alert && !command->get_force()) {
                error_msg = "Water level low — watering blocked. Use force=true to override.";
                Serial.println(error_msg);
                blocked_amount_ml = 0;
                return false;
            }
            Serial.println("Starting dispensing.");
            active_target = command->get_target();
            plant_to_servo(active_target);
            schedule_pump_start();
            break;
        case Action::DISPENSE_SPECIFIC_AMOUNT:
        {
            if (water_low_alert && !command->get_force()) {
                error_msg = "Water level low — blocked " + String(command->get_amount()) + " ml.";
                Serial.println(error_msg);
                blocked_amount_ml = command->get_amount();
                return false;
            }
            active_target = command->get_target();
            dispensing_specific = true;
            dispensing_target_ml = command->get_amount();
            plant_to_servo(active_target);
            schedule_pump_start();
            Serial.print("Dispensing ");
            Serial.print(command->get_amount());
            Serial.println(" ml (non-blocking).");
            break;
        }
        default:
            error_msg = "Unknown command: " + String(command->get_action());
            Serial.println(error_msg);
            return false;
    }

    return true;
}

void schedule_pump_start() {
    pump_start_pending = true;
    pump_start_planned_ms = millis() + 500;
}

void tick_dispensing() {
    const unsigned long now = millis();

    if (pump_start_pending && now >= pump_start_planned_ms) {
        pump_start_pending = false;
        water_pump.switch_on();
        pump_started_ms = now;
        if (dispensing_specific) {
            dispensing_start_ms = now;
        }
        const String details = String("{\"target\":\"") + target_to_string(active_target) +
                               "\",\"amount\":" + String(dispensing_target_ml) + "}";
        log_event_details("command", "info", "watering_started", "Pump switched ON", details.c_str());
        Serial.println("Pump switched ON (after servo settle).");
    }

    if (water_pump.is_on() && water_low_alert) {
        dispensing_specific = false;
        dispensing_target_ml = 0;
        pump_start_pending = false;
        water_pump.switch_off();
        const String details = String("{\"target\":\"") + target_to_string(active_target) + "\"}";
        log_event_details("alert", "warn", "watering_stopped_low_water",
                          "Pump auto-stopped: water tank low during watering", details.c_str());
        Serial.println("EMERGENCY STOP: water tank low during active watering.");
        return;
    }

    if (water_pump.is_on() && (now - pump_started_ms) >= MAX_PUMP_ON_MS) {
        dispensing_specific = false;
        dispensing_target_ml = 0;
        pump_start_pending = false;
        water_pump.switch_off();
        const String details = String("{\"target\":\"") + target_to_string(active_target) + "\"}";
        log_event_details("alert", "error", "watering_stopped_max_runtime",
                          "Pump auto-stopped: max runtime (5 min) exceeded", details.c_str());
        Serial.println("EMERGENCY STOP: pump max runtime exceeded.");
        return;
    }

    if (dispensing_specific && water_pump.is_on()) {
        const unsigned long elapsed_ms = now - dispensing_start_ms;
        const unsigned long duration_ms = (static_cast<unsigned long>(dispensing_target_ml) * 60000UL) / FLOW_RATE_ML_PER_MIN;
        if (elapsed_ms >= duration_ms) {
            const String details = String("{\"target\":\"") + target_to_string(active_target) +
                                   "\",\"amount\":" + String(dispensing_target_ml) + "}";
            dispensing_specific = false;
            dispensing_target_ml = 0;
            water_pump.switch_off();
            log_event_details("command", "info", "watering_completed", "Auto-stop: target amount dispensed", details.c_str());
            Serial.println("Auto-stop: target amount dispensed.");
        }
    }
}

void load_wifi_credentials() {
    prefs.begin("wifi", false);
    wifi_ssid = prefs.getString("ssid", WIFI_SSID_LOCAL);
    wifi_password = prefs.getString("password", WIFI_PASSWORD_LOCAL);
    if (wifi_ssid.length() == 0 || wifi_password.length() == 0) {
        wifi_ssid = WIFI_SSID_LOCAL;
        wifi_password = WIFI_PASSWORD_LOCAL;
        prefs.putString("ssid", wifi_ssid);
        prefs.putString("password", wifi_password);
    }
    prefs.end();
    Serial.println("WiFi credentials loaded from NVS/local config.");
}

void init_time_ntp() {
    // Europe/Rome with DST. Without NTP the ESP falls back to the server clock
    // (see EventPublisher / EventLog::setServerEpoch).
    configTzTime("CET-1CEST-2,M3.5.0/2,M10.5.0/3", "pool.ntp.org", "time.google.com");
}

String load_server_url() {
    prefs.begin("server", false);
    String url = prefs.getString("url", SMARTSPRINKLER_SERVER_URL);
    if (url.length() == 0) {
        url = SMARTSPRINKLER_SERVER_URL;
    }
    prefs.end();
    return url;
}

void on_wifi_connected(WiFiEvent_t event) {
    WiFiAddr = WiFi.localIP().toString();
    Serial.print("WiFi connected: ");
    Serial.println(WiFiAddr);
    Serial.print(format("Server Ready! Use 'http://%s' to connect\n", WiFiAddr));
    log_event("network", "info", "wifi_connected", ("WiFi connected, IP " + WiFiAddr).c_str());
}

void on_wifi_disconnected(WiFiEvent_t event) {
    WiFiAddr = String(hostname) + ".local";
    Serial.println("WiFi disconnected — attempting to reconnect...");
    WiFi.reconnect();
    log_event("network", "warn", "wifi_disconnected", "WiFi disconnected");
}

void handle_serial_command() {
    if (Serial.available() == 0) {
        return;
    }

    static String line = "";
    while (Serial.available()) {
        const char c = Serial.read();
        if (c == '\n') {
            line.trim();
            if (line.length() > 0) {
                Serial.print("Serial command: ");
                Serial.println(line);
                if (line.startsWith("WIFI")) {
                    int first_space = line.indexOf(' ');
                    if (first_space > 0) {
                        const int second_space = line.indexOf(' ', first_space + 1);
                        if (second_space > 0) {
                            const String new_ssid = line.substring(first_space + 1, second_space);
                            const String new_password = line.substring(second_space + 1);
                            if (new_ssid.length() > 0 && new_password.length() > 0) {
                                prefs.begin("wifi", false);
                                prefs.putString("ssid", new_ssid);
                                prefs.putString("password", new_password);
                                wifi_ssid = new_ssid;
                                wifi_password = new_password;
                                prefs.end();
                                Serial.println("WiFi credentials updated. Reconnecting...");
                                WiFi.disconnect();
                                WiFi.begin(wifi_ssid.c_str(), wifi_password.c_str());
                            }
                        }
                    }
                } else if (line.startsWith("SERVER")) {
                    int first_space = line.indexOf(' ');
                    if (first_space > 0) {
                        const String new_url_line = line.substring(first_space + 1);
                        String new_url = new_url_line;
                        new_url.trim();
                        if (new_url.length() > 0) {
                            prefs.begin("server", false);
                            prefs.putString("url", new_url);
                            prefs.end();
                            event_publisher.setServerUrl(new_url);
                            log_event("network", "info", "server_url_updated", ("Server URL updated: " + new_url).c_str());
                            Serial.println("Server URL updated.");
                        }
                    }
                } else {
                    Serial.println("Unknown command. Usage: WIFI <ssid> <password> | SERVER <url>");
                }
            }
            line = "";
        } else {
            line += c;
        }
    }
}