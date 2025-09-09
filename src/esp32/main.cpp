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
float temperature;
float humidity;

CommandManager command_manager;
Hashtable<String, Route> routes;

const Actuator water_pump(PIN_PUMP_RELAY);

void startCameraServer();
void reply_invalid_payload(MongooseHttpServerRequest *req);
bool process_command(const std::shared_ptr<Command> &command, String& error_msg);

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

    // Start the display
    // u8g2.begin();

    TempHumiditySensor::init();

    // Initialize Command Manager
    command_manager.init();
    setup_command_routes();

    Serial.println("\n\nSystem Fully Initialized!");
}

void loop() {
    // --- Non-Blocking Sensor Reading ---
    const unsigned long currentMillis = millis();

    if (currentMillis - previousMillis >= interval) {
        printCurrentTime();
        previousMillis = currentMillis;

        // Get temperature event and print its value
        temperature = TempHumiditySensor::getTemperature();
        if (!isnan(temperature)) {
            Serial.print("Temperature: ");
            Serial.println(temperature);
        }

        // Get humidity event and print its value
        humidity = TempHumiditySensor::getHumidity();
        if (!isnan(humidity)) {
            Serial.print("Humidity: ");
            Serial.println(humidity);
        }
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
                    status.put("temperature", String(temperature, 2));
                    status.put("humidity", String(humidity, 2));
                    status.put("water_pump", water_pump.is_on() ? "on" : "off");

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

bool process_command(const std::shared_ptr<Command> &command, String& error_msg) {
    // Process the received command
    switch (command->get_action()) {
        case Action::STOP:
            // Stop dispensing
            Serial.println("Stopping dispensing.");
            water_pump.switch_off();
            break;
        case Action::START:
            // Start dispensing
            Serial.println("Starting dispensing.");
            water_pump.switch_on();
            break;
        case Action::DISPENSE_SPECIFIC_AMOUNT:
            // Dispense specific amount
            Serial.print("Dispensing ");
            Serial.print(command->get_amount());
            Serial.println(" ml.");
            // TODO: Implement logic to dispense the specific amount
            error_msg = "Command not implemented yet.";
            Serial.println(error_msg);
            return false;
            break;
        default:
            error_msg = "Unknown command: " + String(command->get_action());
            Serial.println(error_msg);
            return false;
    }

    return true;
}
