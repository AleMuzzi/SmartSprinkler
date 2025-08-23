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
#include "../services/UdpServer.h"
#include "sensors/camera.h"
#include "sensors/temp_humidity_sensor.h"
#include "services/CommandManager.h"

const char *ssid = "Brignuzzi WiFi";		   // Enter SSID WIFI Name/Volumes/Data-1/amuzzi/Projects/Omni robot/WD.ZYC0076/ZYC0076-EN/2_Arduino_Code/1_Auto_move/1_Auto_move.ino
const char *password = "88uffleukticegscwrizaqrt"; // Enter WIFI Password
const char *hostname = "OmniRobot";
//const char *ssid = "AndroidAP_6717";		   // Enter SSID WIFI Name
//const char *password = "10000001"; // Enter WIFI Password

IPAddress local_IP(192, 168, 1, 246);
IPAddress gateway(192, 168, 1, 254);
IPAddress subnet(255, 255, 255, 0);


// GPIO Setting
extern int gpLed = 4; // Light
extern String WiFiAddr = "";

// Variables for non-blocking timer
unsigned long previousMillis = 0;
constexpr long interval = 2000; // Interval at which to read sensor (milliseconds)

// U8G2_SSD1306_128X64_NONAME_1_HW_I2C u8g2(U8G2_R0, /* clock=*/ A5, /* data=*/ A4, /* reset=*/ U8X8_PIN_NONE);  // High speed I2C
float temperature;
float humidity;

CommandManager command_manager;

void startCameraServer();

void setup()
{
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
	if (!WiFi.config(local_IP, gateway, subnet)) {
		Serial.println("STA Failed to configure");
	}

	WiFi.setHostname(hostname);
  	WiFi.begin(ssid, password);

	Serial.print("Connecting to WiFi");
	while (WiFi.status() != WL_CONNECTED)
	{
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

	Serial.println("System Fully Initialized!");
}

void loop()
{

	// --- Non-Blocking Sensor Reading ---
	unsigned long currentMillis = millis();

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

	command_manager.poll();

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
	// init_udp_server();

	// sleep(5);
	// put your main code here, to run repeatedly:
	// digitalWrite(4, HIGH);
	// delay(2000);
	// digitalWrite(4, LOW);
	// delay(2000);
}
