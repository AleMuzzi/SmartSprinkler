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
#include <esp_task_wdt.h>

#define PIN_PUMP_RELAY 12
#define PIN_ROTARY_SERVO 13

#define SERVO_MIN_US 500
#define SERVO_MAX_US 2500
#define SERVOFreq 50

#define ROTARY_DELTA_DEG 19.0f
#define ROTARY_START_DEG  5.0f
#define ROTARY_POSITION_COUNT 10

#define FLOW_RATE_ML_PER_MIN 1380

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

bool calibration_in_progress = false;
int calibration_step = 0;
bool calibration_all_success = true;
unsigned long calibration_moved_at_ms = 0;

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
    } else {
        Serial.println("\n! WiFi not connected — restarting connection in background (reconnect handler active).");
        WiFiAddr = String(hostname) + ".local";
    }

    water_pump.switch_off();

    rotary_servo.attach(PIN_ROTARY_SERVO, SERVO_MIN_US, SERVO_MAX_US);
    Serial.println("Rotary servo attached (GPIO 13)");

    begin_calibration();

    NanoSerial.begin(9600, SERIAL_8N1, NANO_RX_PIN, NANO_TX_PIN);
    Serial.println("Nano UART2 initialized (RX=14, TX=15)");

    command_manager.init();
    setup_command_routes();

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

void setup_command_routes() {
    routes.put("/health", Route{
                .http_method = HTTP_GET,
                .from_json = nullptr,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    sendCorsJson(req, 200, R"({"status":"ok"})");
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
                    if (process_command(curr_command, error_msg)) {
                        sendCorsJson(req, 200, R"({"status":"ok"})");
                        return;
                    }

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
            Serial.println("Rotary calibration: SUCCESS — all positions verified");
        } else {
            rotary_calibrated = false;
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
        water_low_alert = (water_ok == 0);
        if (temp != -1) air_temperature = temp;
        if (hum != -1) air_humidity = hum;
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
        if (dispensing_specific) {
            dispensing_start_ms = now;
        }
        Serial.println("Pump switched ON (after servo settle).");
    }

    if (dispensing_specific && water_pump.is_on()) {
        const unsigned long elapsed_ms = now - dispensing_start_ms;
        const unsigned long duration_ms = (static_cast<unsigned long>(dispensing_target_ml) * 60000UL) / FLOW_RATE_ML_PER_MIN;
        if (elapsed_ms >= duration_ms) {
            dispensing_specific = false;
            dispensing_target_ml = 0;
            water_pump.switch_off();
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
    Serial.println("WiFi credentials loaded from NVS/local config.");
}

void on_wifi_connected(WiFiEvent_t event) {
    WiFiAddr = WiFi.localIP().toString();
    Serial.print("WiFi connected: ");
    Serial.println(WiFiAddr);
    Serial.print(format("Server Ready! Use 'http://%s' to connect\n", WiFiAddr));
}

void on_wifi_disconnected(WiFiEvent_t event) {
    WiFiAddr = String(hostname) + ".local";
    Serial.println("WiFi disconnected — attempting to reconnect...");
    WiFi.reconnect();
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
                                prefs.putString("ssid", new_ssid);
                                prefs.putString("password", new_password);
                                wifi_ssid = new_ssid;
                                wifi_password = new_password;
                                Serial.println("WiFi credentials updated. Reconnecting...");
                                WiFi.disconnect();
                                WiFi.begin(wifi_ssid.c_str(), wifi_password.c_str());
                            }
                        }
                    }
                } else {
                    Serial.println("Unknown command. Usage: WIFI <ssid> <password>");
                }
            }
            line = "";
        } else {
            line += c;
        }
    }
}