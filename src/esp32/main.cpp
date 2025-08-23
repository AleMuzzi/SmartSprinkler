//
// Created by Alessandro Muzzi on 23/03/25.
//


/*
 * @Date: 2022-8-27
 * @Description: ESP32 Camera Surveillance Car
 * @FilePath:
 */


#include <esp_camera.h>
#include <WiFi.h>
#include <thread>
#include <utils/string.h>
#include <utils/time.h>

#include <U8g2lib.h>
#include "../services/UdpServer.h"
#include "sensors/temp_humidity_sensor.h"
#include "services/CommandManager.h"

//
// WARNING!!! Make sure that you have either selected ESP32 Wrover Module,
//            or another board which has PSRAM enabled
//
// Adafruit ESP32 Feather

// Select camera model
//#define CAMERA_MODEL_WROVER_KIT
//#define CAMERA_MODEL_M5STACK_PSRAM
#define CAMERA_MODEL_AI_THINKER

const char *ssid = "Brignuzzi WiFi";		   // Enter SSID WIFI Name/Volumes/Data-1/amuzzi/Projects/Omni robot/WD.ZYC0076/ZYC0076-EN/2_Arduino_Code/1_Auto_move/1_Auto_move.ino
const char *password = "88uffleukticegscwrizaqrt"; // Enter WIFI Password
const char *hostname = "OmniRobot";
//const char *ssid = "AndroidAP_6717";		   // Enter SSID WIFI Name
//const char *password = "10000001"; // Enter WIFI Password

IPAddress local_IP(192, 168, 1, 246);
IPAddress gateway(192, 168, 1, 254);
IPAddress subnet(255, 255, 255, 0);

#if defined(CAMERA_MODEL_WROVER_KIT)
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 21
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 19
#define Y4_GPIO_NUM 18
#define Y3_GPIO_NUM 5
#define Y2_GPIO_NUM 4
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

#elif defined(CAMERA_MODEL_AI_THINKER)
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27

#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

#else
#error "Camera model not selected"
#endif

// GPIO Setting
extern int gpLed = 4; // Light
extern String WiFiAddr = "";
std::thread udp_server_thread;

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
	Serial.begin(115200);
	Serial.setDebugOutput(true);
	Serial.println();

	pinMode(gpLed, OUTPUT); // Light
	digitalWrite(gpLed, LOW);

	camera_config_t config;
	config.ledc_channel = LEDC_CHANNEL_0;
	config.ledc_timer = LEDC_TIMER_0;
	config.pin_d0 = Y2_GPIO_NUM;
	config.pin_d1 = Y3_GPIO_NUM;
	config.pin_d2 = Y4_GPIO_NUM;
	config.pin_d3 = Y5_GPIO_NUM;
	config.pin_d4 = Y6_GPIO_NUM;
	config.pin_d5 = Y7_GPIO_NUM;
	config.pin_d6 = Y8_GPIO_NUM;
	config.pin_d7 = Y9_GPIO_NUM;
	config.pin_xclk = XCLK_GPIO_NUM;
	config.pin_pclk = PCLK_GPIO_NUM;
	config.pin_vsync = VSYNC_GPIO_NUM;
	config.pin_href = HREF_GPIO_NUM;
	config.pin_sccb_sda = SIOD_GPIO_NUM;
	config.pin_sccb_scl = SIOC_GPIO_NUM;
	config.pin_pwdn = PWDN_GPIO_NUM;
	config.pin_reset = RESET_GPIO_NUM;
	config.xclk_freq_hz = 20000000;
	config.pixel_format = PIXFORMAT_JPEG;
	// init with high specs to pre-allocate larger buffers
	Serial.println(ESP.getFreePsram());
	if (psramFound())
	{
		config.frame_size = FRAMESIZE_HVGA;/*	FRAMESIZE_96X96,    // 96x96
												FRAMESIZE_QQVGA,    // 160x120
												FRAMESIZE_QCIF,     // 176x144
												FRAMESIZE_HQVGA,    // 240x176
												FRAMESIZE_240X240,  // 240x240
												FRAMESIZE_QVGA,     // 320x240
												FRAMESIZE_CIF,      // 400x296
												FRAMESIZE_HVGA,     // 480x320
												FRAMESIZE_VGA,      // 640x480
												FRAMESIZE_SVGA,     // 800x600
												FRAMESIZE_XGA,      // 1024x768
												FRAMESIZE_HD,       // 1280x720
												FRAMESIZE_SXGA,     // 1280x1024
												FRAMESIZE_UXGA,     // 1600x1200*/
		config.jpeg_quality = 10;		/*It could be anything between 0 and 63.The smaller the number, the higher the quality*/
		config.fb_count = 2;
		Serial.println("FRAMESIZE_HVGA");
	}
	else
	{
		config.frame_size = FRAMESIZE_CIF;
		config.jpeg_quality = 12;
		config.fb_count = 1;
		Serial.println("FRAMESIZE_QVGA");
	}

	// camera init
	esp_err_t err = esp_camera_init(&config);
	if (err != ESP_OK)
	{
		Serial.printf("Camera init failed with error 0x%x", err);
		return;
	}

	// drop down frame size for higher initial frame rate
	auto *s = esp_camera_sensor_get();
	s->set_framesize(s, FRAMESIZE_CIF);
	if (!WiFi.config(local_IP, gateway, subnet)) {
		Serial.println("STA Failed to configure");
	}
	WiFi.setHostname(hostname);
  	WiFi.begin(ssid, password);

	while (WiFi.status() != WL_CONNECTED)
	{
		delay(500);
		Serial.print(".");
	}
	Serial.println("");
	Serial.println("WiFi connected");
	WiFiAddr = WiFi.localIP().toString();

	// start a new thread
	// udp_server_thread = std::thread(start_udp_server);

	printCurrentTime();

	Serial.print(format("Server Ready! Use 'http://%s' to connect\n", WiFiAddr));
	// start_udp_server();
	pinMode(4, OUTPUT);
	// Serial.println("0.1");

	// Start the display
	// u8g2.begin();
	Serial.println("1");

	TempHumiditySensor::init();

	command_manager.init();
	Serial.println("System Initialized!");
}

void loop()
{
	// Serial.println("Waiting for data...");
	// Serial.print("Use 'http://");
	// Serial.println(WiFi.localIP());

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

	command_manager.start_async();

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
