#include <Arduino.h>
#include <U8g2lib.h>

#include <Adafruit_Sensor.h>
#include <DHT_U.h>
#include <Wire.h>

#define DHTPIN 2        // Pin a cui è collegato il sensore
#define DHTTYPE DHT22    // Indicazione del modello del sensore

DHT_Unified dht_temp_humidity(DHTPIN, DHTTYPE);
U8G2_SSD1306_128X64_NONAME_1_HW_I2C u8g2(U8G2_R0, /* clock=*/ A5, /* data=*/ A4, /* reset=*/ U8X8_PIN_NONE);  // High speed I2C

// Variables for sensor readings
float temperature = 0.0;
float humidity = 0.0;

// Variables for non-blocking timer
unsigned long previousMillis = 0;
const long interval = 2000; // Interval at which to read sensor (milliseconds)

void setup() {
    Serial.begin(115200);

    // Start the display
    u8g2.begin();

    // Start the DHT sensor
    dht_temp_humidity.begin(); // Now you can uncomment this!

    Serial.println("System Initialized!");
}

void loop() {
    // --- Non-Blocking Sensor Reading ---
    unsigned long currentMillis = millis();

    if (currentMillis - previousMillis >= interval) {
        previousMillis = currentMillis;

        // Get temperature event and print its value
        sensors_event_t event;
        dht_temp_humidity.temperature().getEvent(&event);
        if (!isnan(event.temperature)) {
            temperature = event.temperature;
            Serial.print("Temperature: ");
            Serial.println(temperature);
        } else {
            Serial.println("Error reading temperature!");
        }

        // Get humidity event and print its value
        dht_temp_humidity.humidity().getEvent(&event);
        if (!isnan(event.relative_humidity)) {
            humidity = event.relative_humidity;
            Serial.print("Humidity: ");
            Serial.println(humidity);
        } else {
            Serial.println("Error reading humidity!");
        }
    }

    // --- Display Update ---
    // The drawing code MUST be inside this do-while loop for page-buffer mode
    u8g2.firstPage();
    do {
        u8g2.setFont(u8g2_font_ncenB10_tr); // A nice, clear font

        // Display Temperature
        u8g2.setCursor(0, 15);
        u8g2.print("Temp: ");
        u8g2.print(temperature, 1); // Print with 1 decimal place
        u8g2.print(" C");

        // Display Humidity
        u8g2.setCursor(0, 45);
        u8g2.print("Humi: ");
        u8g2.print(humidity, 1); // Print with 1 decimal place
        u8g2.print(" %");

    } while (u8g2.nextPage());
}

// uint32_t delayMS;
//
// void setup() {
//   Serial.begin(9600);
//   // Initialize device.
//   dht.begin();
//   Serial.println(F("DHTxx Unified Sensor Example"));
//   // Print temperature sensor details.
//   sensor_t sensor;
//   dht.temperature().getSensor(&sensor);
//   Serial.println(F("------------------------------------"));
//   Serial.println(F("Temperature Sensor"));
//   Serial.print  (F("Sensor Type: ")); Serial.println(sensor.name);
//   Serial.print  (F("Driver Ver:  ")); Serial.println(sensor.version);
//   Serial.print  (F("Unique ID:   ")); Serial.println(sensor.sensor_id);
//   Serial.print  (F("Max Value:   ")); Serial.print(sensor.max_value); Serial.println(F("°C"));
//   Serial.print  (F("Min Value:   ")); Serial.print(sensor.min_value); Serial.println(F("°C"));
//   Serial.print  (F("Resolution:  ")); Serial.print(sensor.resolution); Serial.println(F("°C"));
//   Serial.println(F("------------------------------------"));
//   // Print humidity sensor details.
//   dht.humidity().getSensor(&sensor);
//   Serial.println(F("Humidity Sensor"));
//   Serial.print  (F("Sensor Type: ")); Serial.println(sensor.name);
//   Serial.print  (F("Driver Ver:  ")); Serial.println(sensor.version);
//   Serial.print  (F("Unique ID:   ")); Serial.println(sensor.sensor_id);
//   Serial.print  (F("Max Value:   ")); Serial.print(sensor.max_value); Serial.println(F("%"));
//   Serial.print  (F("Min Value:   ")); Serial.print(sensor.min_value); Serial.println(F("%"));
//   Serial.print  (F("Resolution:  ")); Serial.print(sensor.resolution); Serial.println(F("%"));
//   Serial.println(F("------------------------------------"));
//   // Set delay between sensor readings based on sensor details.
//   delayMS = sensor.min_delay / 1000;
// }
//
// void loop() {
//   // Delay between measurements.
//   delay(1000);
//   // Get temperature event and print its value.
//   sensors_event_t event;
//   dht.temperature().getEvent(&event);
//   if (isnan(event.temperature)) {
//     Serial.println(F("Error reading temperature!"));
//   }
//   else {
//     Serial.print(F("Temperature: "));
//     Serial.print(event.temperature);
//     Serial.println(F("°C"));
//   }
//   // Get humidity event and print its value.
//   dht.humidity().getEvent(&event);
//   if (isnan(event.relative_humidity)) {
//     Serial.println(F("Error reading humidity!"));
//   }
//   else {
//     Serial.print(F("Humidity: "));
//     Serial.print(event.relative_humidity);
//     Serial.println(F("%"));
//   }
// }