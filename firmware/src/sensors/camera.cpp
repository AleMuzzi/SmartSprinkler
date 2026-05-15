//
// Created by Alessandro Muzzi on 23/08/25.
//

#include "camera.h"

#include <Esp.h>
#include <esp_camera.h>
#include <HardwareSerial.h>

#include "model/esp_32_cam_pinout.h"

void Camera::init() {
	Serial.println("Camera initialization started");

	// Camera configuration
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
	const esp_err_t err = esp_camera_init(&config);
	if (err != ESP_OK)
	{
		Serial.printf("Camera init failed with error 0x%x", err);
		return;
	}

	// drop down frame size for higher initial frame rate
	auto *s = esp_camera_sensor_get();
	s->set_framesize(s, FRAMESIZE_CIF);
}