/**
 * Drone Firmware UDP
 *
 * @author Alessandro Muzzi
 * @since 13/05/2020
 */

#include <Arduino.h>
#include <WiFiEsp.h>
#include <WiFiEspUdp.h>
#include <Servo.h>

// Emulate Serial1 on pins 0/1 if not present
#ifndef HAVE_HWSERIAL1
#include "SoftwareSerial.h"
SoftwareSerial Serial1(0, 1); // RX, TX
#endif

//region Constants

#define BUFFER_SIZE 255

//endregion

//region Fields

//region Udp Server

char ssid[] = "ESP8266 WiFi";            // your network SSID (name)
char pass[] = "10000001";        // your network password
int status = WL_IDLE_STATUS;     // the Wifi radio's status

unsigned int localPort = 10002;  // local port to listen on

char packetBuffer[BUFFER_SIZE];          // buffer to hold incoming packet
char ReplyBuffer[] = "ACK";      // a string to send back

WiFiEspUDP Udp;

//endregion

//region Drone

// Trottle
Servo Throttle;
// Yaw
Servo Rudder;
// Roll
Servo Aileron;
// Pitch
Servo Elevator;
Servo Auxiliary;
int throttleValue = 1000;
int rudderValue = 1500;
int aileronValue = 1500;
int elevatorValue = 1500;
int auxiliaryValue = 1000;

//endregion

//endregion

//region Function Prototypes

void printWifiStatus(char* requiredSSID);
void droneCommand(char* receivedPacket);

//endregion

void setup() {

    //region Drone
    //KK2 order (up to down): AIL, ELE, THR, RUD, AUX
    Throttle.attach(9);
    Rudder.attach(6);
    Aileron.attach(11);
    Elevator.attach(10);
    Auxiliary.attach(5);

    //set initial positions
    Throttle.writeMicroseconds(throttleValue);  //down (this may need to be 2000)
    Rudder.writeMicroseconds(rudderValue);    //centre
    Aileron.writeMicroseconds(aileronValue);   //centre
    Elevator.writeMicroseconds(elevatorValue);  //centre
    Auxiliary.writeMicroseconds(auxiliaryValue);//off
    delay(5000);  //wait 5 seconds for the system to stabalise

    //endregion

    //region Udp Server

    // initialize serial for debugging
    Serial.begin(115200);
    // initialize serial for ESP module
    Serial1.begin(115200);
    // initialize ESP module
    WiFi.init(&Serial1);

    // check for the presence of the shield:
    if (WiFi.status() == WL_NO_SHIELD) {
        Serial.println("WiFi shield not present");
        // don't continue:
        while (true);
    }

    Serial.print("Attempting to start AP ");
    Serial.println(ssid);

    // uncomment these two lines if you want to set the IP address of the AP
    //IPAddress localIp(192, 168, 111, 111);
    //WiFi.configAP(localIp);

    // start access point
    status = WiFi.beginAP(ssid, 10, pass, ENC_TYPE_WPA2_PSK);

    Serial.println("Access point started");
    printWifiStatus(ssid);

    Serial.println("\nStarting UDP server...");
    // if you get a connection, report back via serial:
    Udp.begin(localPort);

    Serial.print("Listening on port ");
    Serial.println(localPort);

    // if setup succeeded, light up the led
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, HIGH);
}


void loop() {

    // if there's data available, read a packet
    int packetSize = Udp.parsePacket();
    if (packetSize) {
//        Serial.print("Received packet of size ");
//        Serial.println(packetSize);
//        Serial.print("From ");
//        IPAddress remoteIp = Udp.remoteIP();
//        Serial.print(remoteIp);
//        Serial.print(", port ");
//        Serial.println(Udp.remotePort());

        // read the packet into packetBufffer
        int len = Udp.read(packetBuffer, BUFFER_SIZE);
        if (len > 0) {
            packetBuffer[len] = 0;
        }
//        Serial.print("Contents: ");
//        Serial.println(packetBuffer);

        droneCommand(packetBuffer);

//    // send a reply, to the IP address and port that sent us the packet we received
//    Udp.beginPacket(Udp.remoteIP(), Udp.remotePort());
//    Udp.write(ReplyBuffer);
//    Udp.endPacket();
    }

    // update axis values
    Throttle.writeMicroseconds(throttleValue);
    Rudder.writeMicroseconds(rudderValue);
    Aileron.writeMicroseconds(aileronValue);
    Elevator.writeMicroseconds(elevatorValue);
    Auxiliary.writeMicroseconds(auxiliaryValue);
    delay(30); // Poll every 50ms
}

void droneCommand(char* receivedPacket) {
    int values[5];

    sscanf(receivedPacket, "T:%d Y:%d P:%d R:%d A:%d",&values[0], &values[1], &values[2], &values[3], &values[4]);
//    Serial.print("Parsed: T:");
//    Serial.print(values[0]);
//    Serial.print(" Y:");
//    Serial.print(values[1]);
//    Serial.print(" P:");
//    Serial.print(values[2]);
//    Serial.print(" R:");
//    Serial.println(values[3]);

    // T [throttle]
    throttleValue = values[0];
    // Y [yaw]
    rudderValue = values[1];
    // P [elevator]
    elevatorValue = values[2];
    // R [aileron]
    aileronValue = values[3];
    // A [auxiliary]
    auxiliaryValue = values[4];
}

void printWifiStatus(char* requiredSSID) {
    // print the SSID of the network you're attached to:
    Serial.print("SSID: ");
    char* actualSSID = WiFi.SSID();
    if(strcmp(actualSSID, "") == 0){
        strcpy(actualSSID, requiredSSID);
    }
    Serial.println(actualSSID);

    // print your WiFi shield's IP address:
    IPAddress ip = WiFi.localIP();
    Serial.print("IP Address: ");
    Serial.println(ip);

    // print the received signal strength:
    long rssi = WiFi.RSSI();
    Serial.print("signal strength (RSSI):");
    Serial.print(rssi);
    Serial.println(" dBm");
}
