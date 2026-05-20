//
// Created by Alessandro Muzzi on 23/03/25.
//


/*
 * @Date: 2022-8-27
 * @Description: ESP32 Camera Surveillance Car
 * @FilePath:
 */

#include <WiFi.h>
#include <utils/string.h>
#include <utils/time.h>

#include <U8g2lib.h>

#include "model/command.h"
#include "model/status.h"
#include "model/route.h"
#include "sensors/actuator.h"

#include "sensors/camera.h"
#include "sensors/temp_humidity_sensor.h"
#include "services/CommandManager.h"
#include "utils/hashtable_ext.h"

#define PIN_PUMP_RELAY 12
#define PIN_VALVE_1 13
#define PIN_VALVE_2 15
#define PIN_VALVE_3 16

#define FLOW_RATE_ML_PER_MIN 6000  // User must calibrate — default 6 L/min

constexpr char ssid[15] = "Brignuzzi WiFi";
constexpr char password[25] = "88uffleukticegscwrizaqrt"; // Enter WIFI Password
constexpr char hostname[16] = "smart_sprinkler";
//const char *ssid = "AndroidAP_6717";		   // Enter SSID WIFI Name
//const char *password = "10000001"; // Enter WIFI Password

const IPAddress local_IP(192, 168, 1, 9);
const IPAddress gateway(192, 168, 1, 1);
const IPAddress subnet(255, 255, 255, 0);


// GPIO Setting
const extern uint8_t gpLed = 4; // Light
String WiFiAddr = "";

// Variables for non-blocking timer
unsigned long previousMillis = 0;
constexpr long interval = 2000; // Interval at which to read sensor (milliseconds)

// U8G2_SSD1306_128X64_NONAME_1_HW_I2C u8g2(U8G2_R0, /* clock=*/ A5, /* data=*/ A4, /* reset=*/ U8X8_PIN_NONE);  // High speed I2C
float air_temperature;
float air_humidity;
float soil_moisture;

CommandManager command_manager;
Hashtable<String, Route> routes;

const Actuator water_pump(PIN_PUMP_RELAY);
const Actuator valve_1(PIN_VALVE_1);
const Actuator valve_2(PIN_VALVE_2);
const Actuator valve_3(PIN_VALVE_3);

Target::Value active_target = Target::NAGA_MORICH; // last selected target

// Soil moisture from Arduino Nano (4 HW-390 sensors on A0–A3)
int soil_moisture_raw[4] = {0, 0, 0, 0};
bool nano_available = false;
// soil_moisture (float) stores the average as percentage — used by /status for backward compatibility

void startCameraServer();
void reply_invalid_payload(MongooseHttpServerRequest *req);
bool process_command(const std::shared_ptr<Command> &command, String& error_msg);
void plant_to_valves(Target::Value target);
const char* target_to_string(Target::Value target);
void request_soil_moistures();

void setup_command_routes();

void setup() {
    // Start Serial
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println();

    Serial.println("###############################");
    Serial.println("#       Smart Sprinkler       #");
    Serial.println("###############################");
    Serial.println();

    pinMode(gpLed, OUTPUT); // Light
    digitalWrite(gpLed, LOW);

    // Start Camera
    Camera::init();

    // Connect to WiFi
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

    pinMode(4, OUTPUT);

    // Initialize valve relay pins (start closed)
    pinMode(PIN_VALVE_1, OUTPUT);
    pinMode(PIN_VALVE_2, OUTPUT);
    pinMode(PIN_VALVE_3, OUTPUT);
    digitalWrite(PIN_VALVE_1, LOW);
    digitalWrite(PIN_VALVE_2, LOW);
    digitalWrite(PIN_VALVE_3, LOW);

    // Start the display
    // u8g2.begin();

    TempHumiditySensor::init();

    // Initialize Command Manager
    command_manager.init();
    setup_command_routes();

    Serial.println("\n\nSystem Fully Initialized!");
    Serial.println("-------------------------------");
}

void loop() {
    // --- Non-Blocking Sensor Reading ---
    const unsigned long currentMillis = millis();

    if (currentMillis - previousMillis >= interval) {
        // printCurrentTime();
        previousMillis = currentMillis;

        // Update air temperature
        air_temperature = TempHumiditySensor::getTemperature();
        if (!isnan(air_temperature)) {
            Serial.print("Temperature: ");
            Serial.println(air_temperature);
        }

        // Update air humidity
        air_humidity = TempHumiditySensor::getHumidity();
        if (!isnan(air_humidity)) {
            Serial.print("Humidity: ");
            Serial.println(air_humidity);
        }

        // Update soil moisture from Arduino Nano
        request_soil_moistures();
        if (nano_available) {
            Serial.print("Soil moisture raw: ");
            Serial.print(soil_moisture_raw[0]); Serial.print(", ");
            Serial.print(soil_moisture_raw[1]); Serial.print(", ");
            Serial.print(soil_moisture_raw[2]); Serial.print(", ");
            Serial.println(soil_moisture_raw[3]);
        }
        Serial.println("-------------------------------");
    }

    if (!command_manager.is_stopped()) {
        command_manager.poll();
    }

    delay(100);


    // --- Display Update ---
    // The drawing code MUST be inside this do-while loop for page-buffer mode
    // u8g2.firstPage();
    // do {
    // 	u8g2.setFont(u8g2_font_ncenB10_tr); // A nice, clear font
    //
    // 	// Display Temperature
    // 	u8g2.setCursor(0, 15);
    // 	u8g2.print("Temp: ");
    // 	u8g2.print(temperature, 1); // Print with 1 decimal place
    // 	u8g2.print(" C");
    //
    // 	// Display Humidity
    // 	u8g2.setCursor(0, 45);
    // 	u8g2.print("Humi: ");
    // 	u8g2.print(humidity, 1); // Print with 1 decimal place
    // 	u8g2.print(" %");
    //
    // } while (u8g2.nextPage());
}

void setup_command_routes() {
    routes.put("/health", Route{
                .http_method = HTTP_GET,
                .from_json = nullptr,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    Serial.println("health");
                    req->send(200, "application/json", R"({"status":"ok"})");
                }
            });
    routes.put("/command", Route{
                .http_method = HTTP_POST,
                .from_json = Command::from_json,
                .handler = [](MongooseHttpServerRequest *req, const std::shared_ptr<ICanBeDeserialized>& command) {
                    const auto curr_command = std::static_pointer_cast<Command>(command);

                    if (curr_command->getType() != "Command") {
                        Serial.println("Command type mismatch");
                        reply_invalid_payload(req);
                        return;
                    }

                    String error_msg;
                    if (process_command(curr_command, error_msg)) {
                        req->send(200, "application/json", R"({"status":"ok"})");
                        return;
                    }

                    req->send(
                        400,
                        "application/json",
                        R"({"status":"error","error_code":"invalid_command","message":")" + error_msg + "\"}"
                    );
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
                    status.put("valve_1", valve_1.is_on() ? "on" : "off");
                    status.put("valve_2", valve_2.is_on() ? "on" : "off");
                    status.put("valve_3", valve_3.is_on() ? "on" : "off");
                    status.put("soil_moisture_0", String(soil_moisture_raw[0]));
                    status.put("soil_moisture_1", String(soil_moisture_raw[1]));
                    status.put("soil_moisture_2", String(soil_moisture_raw[2]));
                    status.put("soil_moisture_3", String(soil_moisture_raw[3]));
                    status.put("active_plant", water_pump.is_on() ? target_to_string(active_target) : "null");

                    req->send(
                        200,
                        "application/json",
                        hashtable_to_string(status)
                        );
                }
            });
    command_manager.setup_routes(routes);

    // region Update LCD

    // this->server.on(path.c_str(), route.http_method, [this, request](MongooseHttpServerRequest *req) {
    //     Serial.println("Command request received");
    //     const String body = req->body();
    //     Serial.print("Received HTTP command: ");
    //     Serial.println(body);
    //
    //     DeserializationError error;
    //     String error_msg;
    //     const auto command = request->from_json(body.c_str(), error, error_msg);
    //     if (command != nullptr) {
    //         process_command(*command);
    //         req->send(200, "application/json", R"({"status":"ok"})");
    //     } else {
    //         Serial.print("Failed to parse command: ");
    //         Serial.println(error.c_str());
    //         req->send(
    //             400,
    //             "application/json",
    //             R"({"status":"error","error_code":")" + String(error.c_str()) + R"(","message":")" + error_msg + "\"}"
    //         );
    //     }
    // });

    // endregion
}

void reply_invalid_payload(MongooseHttpServerRequest *req) {
    req->send(
    400,
    "application/json",
    R"({"status":"error","error_code":"invalid_payload","message":"Invalid payload type"})"
    );
}

void plant_to_valves(const Target::Value target) {
    switch (target) {
        // V1 OFF → V2; V2 OFF → plant
        case Target::HABANERO:
            valve_1.switch_off();  // select V2 branch
            valve_2.switch_off();  // select plant 0 on V2
            valve_3.switch_off();  // V3 isolated, safe off
            break;
        case Target::NAGA_MORICH:
            valve_1.switch_off();  // select V2 branch
            valve_2.switch_on();   // select plant 1 on V2
            valve_3.switch_off();  // V3 isolated, safe off
            break;
        // V1 ON → V3; V3 OFF → plant
        case Target::CAROLINA_REAPER:
            valve_1.switch_on();   // select V3 branch
            valve_2.switch_off();  // V2 isolated, safe off
            valve_3.switch_off();  // select plant 0 on V3
            break;
        case Target::ROSMARINO:
            valve_1.switch_on();   // select V3 branch
            valve_2.switch_off();  // V2 isolated, safe off
            valve_3.switch_on();   // select plant 1 on V3
            break;
    }
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

void request_soil_moistures() {
    // Flush any stale data in the RX buffer
    while (Serial.available()) {
        Serial.read();
    }

    // Send sample request to Nano
    Serial.write('S');

    // Read response with timeout
    const unsigned long start = millis();
    String response;
    while (millis() - start < 100) {
        if (Serial.available()) {
            const char c = static_cast<char>(Serial.read());
            if (c == '\n') break;
            response += c;
        }
    }

    if (response.length() == 0) {
        nano_available = false;
        return;
    }

    // Parse "val0,val1,val2,val3"
    int vals[4] = {0};
    int idx = 0;
    int pos = 0;
    for (int i = 0; i <= response.length() && idx < 4; i++) {
        if (i == response.length() || response.charAt(i) == ',') {
            vals[idx++] = response.substring(pos, i).toInt();
            pos = i + 1;
        }
    }

    if (idx == 4) {
        soil_moisture_raw[0] = vals[0];
        soil_moisture_raw[1] = vals[1];
        soil_moisture_raw[2] = vals[2];
        soil_moisture_raw[3] = vals[3];
        // Average raw → percentage (same mapping as old SensorSoilMoisture: 1023→0%, 0→100%)
        const float avg_raw = (vals[0] + vals[1] + vals[2] + vals[3]) / 4.0f;
        soil_moisture = constrain(map(static_cast<int>(avg_raw), 1023, 0, 0, 100), 0, 100);
        nano_available = true;
    }
}

bool process_command(const std::shared_ptr<Command> &command, String& error_msg) {
    // Process the received command
    switch (command->get_action()) {
        case Action::STOP:
            Serial.println("Stopping dispensing.");
            water_pump.switch_off();
            valve_1.switch_off();
            valve_2.switch_off();
            valve_3.switch_off();
            break;
        case Action::START:
            Serial.println("Starting dispensing.");
            active_target = command->get_target();
            plant_to_valves(active_target);
            delay(500); // allow valves to fully open
            water_pump.switch_on();
            break;
        case Action::DISPENSE_SPECIFIC_AMOUNT:
        {
            active_target = command->get_target();
            plant_to_valves(active_target);
            delay(500);
            water_pump.switch_on();
            Serial.print("Dispensing ");
            Serial.print(command->get_amount());
            Serial.println(" ml.");
            const unsigned long duration_ms = static_cast<unsigned long>(
                (static_cast<float>(command->get_amount()) / FLOW_RATE_ML_PER_MIN) * 60.0f * 1000.0f
            );
            delay(duration_ms);
            water_pump.switch_off();
            valve_1.switch_off();
            valve_2.switch_off();
            valve_3.switch_off();
            break;
        }
        default:
            error_msg = "Unknown command: " + String(command->get_action());
            Serial.println(error_msg);
            return false;
    }

    return true;
}
