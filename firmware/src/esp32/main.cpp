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

constexpr char ssid[15] = "Brignuzzi WiFi";
constexpr char password[25] = "88uffleukticegscwrizaqrt";
constexpr char hostname[16] = "smart_sprinkler";

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

void startCameraServer();
void reply_invalid_payload(MongooseHttpServerRequest *req);
bool process_command(const std::shared_ptr<Command> &command, String& error_msg);
void plant_to_servo(Target::Value target);
const char* target_to_string(Target::Value target);
void read_nano_soil_moistures();
int servo_degrees_to_us(float degrees);
void calibrate_rotary();
void move_servo_to_position(int position);

void setup_command_routes();

void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println();

    Serial.println("###############################");
    Serial.println("#       Smart Sprinkler       #");
    Serial.println("###############################");
    Serial.println();

    // Camera::init();

    Serial.print("Device's MAC Address: ");
    Serial.println(WiFi.macAddress());

    WiFi.mode(WIFI_MODE_STA);
    WiFi.setHostname(hostname);
    WiFi.begin(ssid, password);

    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    WiFiAddr = WiFi.localIP().toString();
    Serial.print(format("Server Ready! Use 'http://%s' to connect\n", WiFiAddr));

    water_pump.switch_off();

    rotary_servo.attach(PIN_ROTARY_SERVO, SERVO_MIN_US, SERVO_MAX_US);
    Serial.println("Rotary servo attached (GPIO 13)");

    calibrate_rotary();

    NanoSerial.begin(9600, SERIAL_8N1, NANO_RX_PIN, NANO_TX_PIN);
    Serial.println("Nano UART2 initialized (RX=14, TX=15)");

    command_manager.init();
    setup_command_routes();

    Serial.println("\n\nSystem Fully Initialized!");
    Serial.println("-------------------------------");
}

void loop() {
    const unsigned long currentMillis = millis();

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

    if (dispensing_specific && water_pump.is_on()) {
        const unsigned long elapsed_ms = millis() - dispensing_start_ms;
        const unsigned long duration_ms = (static_cast<unsigned long>(dispensing_target_ml) * 60000UL) / FLOW_RATE_ML_PER_MIN;
        if (elapsed_ms >= duration_ms) {
            dispensing_specific = false;
            dispensing_target_ml = 0;
            water_pump.switch_off();
            Serial.println("Auto-stop: target amount dispensed.");
        }
    }

    delay(10);
}

static void sendCorsJson(MongooseHttpServerRequest *req, int code, const char *content) {
    auto *resp = req->beginResponse();
    resp->addHeader("Access-Control-Allow-Origin", "*");
    resp->setContentType("application/json");
    resp->setContent(content);
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
                    status.put("soil_moisture_0", String(soil_moisture_raw[0]));
                    status.put("soil_moisture_1", String(soil_moisture_raw[1]));
                    status.put("soil_moisture_2", String(soil_moisture_raw[2]));
                    status.put("soil_moisture_3", String(soil_moisture_raw[3]));
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

void calibrate_rotary() {
    Serial.println("Starting rotary calibration...");
    bool all_success = true;

    for (int i = 0; i < ROTARY_POSITION_COUNT; i++) {
        const float angle = servo_position_to_degrees(i);
        const int target_us = servo_degrees_to_us(angle);
        rotary_servo.writeMicroseconds(target_us);
        delay(800);

        const int actual_us = rotary_servo.readMicroseconds();
        const int error = abs(actual_us - target_us);

        if (error > 100) {
            Serial.print("Calibration warning at position ");
            Serial.print(i);
            Serial.print(": expected ");
            Serial.print(target_us);
            Serial.print(" us, got ");
            Serial.print(actual_us);
            Serial.print(" us (error ");
            Serial.print(error);
            Serial.println(" us)");
            all_success = false;
        } else {
            Serial.print("Position ");
            Serial.print(i);
            Serial.print(" OK (");
            Serial.print(actual_us);
            Serial.println(" us)");
        }
    }

    if (all_success) {
        rotary_calibrated = true;
        rotary_current_position = 0;
        rotary_servo.writeMicroseconds(servo_degrees_to_us(0));
        Serial.println("Rotary calibration: SUCCESS — all positions verified");
    } else {
        rotary_calibrated = false;
        rotary_current_position = 0;
        rotary_servo.writeMicroseconds(servo_degrees_to_us(0));
        Serial.println("Rotary calibration: PARTIAL — using software tracking");
    }
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
            parse_nano_line(nano_line);
            nano_line_idx = 0;
        } else if (c != '\r' && nano_line_idx < NANO_LINE_MAX - 1) {
            nano_line[nano_line_idx++] = c;
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
    switch (command->get_action()) {
        case Action::STOP:
            Serial.println("Stopping dispensing.");
            dispensing_specific = false;
            dispensing_target_ml = 0;
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
            delay(500);
            water_pump.switch_on();
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
            plant_to_servo(active_target);
            delay(500);
            dispensing_specific = true;
            dispensing_target_ml = command->get_amount();
            dispensing_start_ms = millis();
            water_pump.switch_on();
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