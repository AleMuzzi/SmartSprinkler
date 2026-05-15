#include <Arduino.h>
#include <Servo.h>
#include <SoftwareSerial.h>

#include "utils/string.h"

// servo control pin
#define MOTOR_PIN           9
// PWM control pin
#define PWM1_PIN            5
#define PWM2_PIN            6
// 74HCT595N chip pin
#define SHCP_PIN            2                               // The displacement of the clock
#define EN_PIN              7                               // Can make control
#define DATA_PIN            8                               // Serial data
#define STCP_PIN            4                               // Memory register clock
// 超声波控制引脚
#define Trig_PIN            12
#define Echo_PIN            13
// 循迹控制引脚
#define LEFT_LINE_TRACJING      A0
#define CENTER_LINE_TRACJING    A1
#define right_LINE_TRACJING     A2

#define AXES_RATIO_THRESHOLD    0.3
#define AXES_DEAD_ZONE          0.2
#define SPEED_MULTIPLIER        1

Servo MOTORservo;

const int Forward = 92; // 01011100     Forward
const int Backward = 163; // 10100011     Back
const int Left = 149; // 10010101     left translation
const int Right = 106; // 01101010     Right translation
const int Top_Left = 20; // 00010100     Upper left mobile
const int Bottom_Left = 129; // 10000001     Lower left mobile
const int Top_Right = 72; // 01001000     Upper right mobile
const int Bottom_Right = 34; // 00100010     The lower right move
const int Stop = 0; // 00000000     Stop
const int CountClockwise = 172; // 10101100     Counterclockwise rotation
const int Clockwise = 83; // 01010011     Rotate clockwise

const int Moedl1 = 25; // model1
const int Moedl2 = 26; // model2
const int Moedl3 = 27; // model3
const int Moedl4 = 28; // model4
const int MotorLeft = 230; // servo turn left
const int MotorRight = 231; // servo turn right

int Left_Tra_Value;
int Center_Tra_Value;
int Right_Tra_Value;
int Black_Line = 400;

int leftDistance = 0;
int middleDistance = 0;
int rightDistance = 0;

byte tmp_package[7] = {0xA5, 0, 0, 0, 0, 0, 0x5A};
byte RX_package[7] = {0xA5, 0, 0, 0, 0, 0, 0x5A};
// byte RX_package[7] = {0};
uint16_t angle = 90;
char model_var = 0;
byte order = Stop;
int forward, right, yaw, roll, aux;
int UT_distance = 0;

void RXpack_func(); //Receive data
void Motor(int Dir, int Speed); // motor drive
void model1_func(byte orders);

void model2_func();

void model3_func();

void model4_func();

float SR04(int Trig, int Echo); // ultrasonic measured distance
void motorleft(); //servo
void motorright(); //servo

SoftwareSerial debugSerial(A4, A5); // RX, TX

void setup() {
    Serial.setTimeout(10);
    pinMode(A4, INPUT_PULLUP); // Add this line
    debugSerial.begin(9600);
    debugSerial.println("Debug Serial Start");
    Serial.begin(115200);

    // MOTORservo.attach(MOTOR_PIN);

    pinMode(SHCP_PIN, OUTPUT);
    pinMode(EN_PIN, OUTPUT);
    pinMode(DATA_PIN, OUTPUT);
    pinMode(STCP_PIN, OUTPUT);
    pinMode(PWM1_PIN, OUTPUT);
    pinMode(PWM2_PIN, OUTPUT);

    pinMode(Trig_PIN, OUTPUT);
    pinMode(Echo_PIN, INPUT);

    pinMode(LEFT_LINE_TRACJING, INPUT);
    pinMode(CENTER_LINE_TRACJING, INPUT);
    pinMode(right_LINE_TRACJING, INPUT);

    // MOTORservo.write(angle);
    //pinMode(LED_BUILTIN, OUTPUT);
    Motor(Stop, 0);
    model_var = 0;
    order = Stop;

    // RX_package[0] = 0xA5;
    // RX_package[6] = 0x5A;
}

void loop() {
    // debugSerial.println("Hello from Arduino!");
    // delay(1000);
    // RX_package[1] = -50;
    // RX_package[2] = RX_package[2] -1;
    // Serial.write(tmp_package, sizeof(tmp_package));
    RXpack_func();

    int speed = 0;
    order = Stop;

    // left joystick
    if (abs(yaw) > AXES_DEAD_ZONE) {
        if (yaw > 0) order = Clockwise;
        else order = CountClockwise;
        speed = abs(yaw) * 250 / 100 * SPEED_MULTIPLIER;

    } else if (abs(forward) > AXES_DEAD_ZONE || abs(right) > AXES_DEAD_ZONE) {
        const float fw_right_ratio = static_cast<float>(forward) / static_cast<float>(right);
        // char *msg = format("fw_right_ratio:", fw_right_ratio);
        // Serial.print("fw_right_ratio: ");
        // Serial.println(fw_right_ratio);
        // free(msg);

        // moving diagonal
        float abs_fw_right_ratio = fw_right_ratio > 0 ? fw_right_ratio : -fw_right_ratio;
        if (abs_fw_right_ratio > 1 - AXES_RATIO_THRESHOLD && abs_fw_right_ratio < 1 + AXES_RATIO_THRESHOLD) {
            // top right or bottom left
            if (fw_right_ratio > 0) {
                if (forward > 0) {
                    order = Top_Right;
                } else {
                    order = Bottom_Left;
                }
            } else {
                if (forward > 0) {
                    order = Top_Left;
                } else {
                    order = Bottom_Right;
                }
            }
            // forward or right is the same as they're very close
            speed = abs(forward) * 250 / 100 * SPEED_MULTIPLIER;
        } else {
            // Serial.println("Debug 1");

            if (abs(forward) > abs(right)) {
                if (forward > 0) order = Forward;
                else order = Backward;
                speed = abs(forward) * 250 / 100 * SPEED_MULTIPLIER;
            } else {
                if (right > 0) order = Right;
                else order = Left;
                speed = abs(right) * 250 / 100 * SPEED_MULTIPLIER;
            }
        }
    }
    // char *msg = format("Order: %d Speed: %d", order, speed);
    // Serial.println(msg);
    // free(msg);


    // TODO IMPROVE
    // if (abs(forward) > abs(right)) {
    //     if (abs(forward) > abs(yaw)) {
    //         if (forward > 0)  order = Forward;
    //         else order = Backward;
    //         speed = abs(forward)/100 * 250;
    //     }
    // } else if (abs(right) > abs(yaw)) {
    //     if (right > 0)  order = Right;
    //     else order = Left;
    //     speed = abs(right)/100 * 250;
    //
    // } else {
    //     if (yaw > 0)  order = Clockwise;
    //     else order = CountClockwise;
    //     speed = abs(yaw)/100 * 250;
    // }

    Motor(order, speed);

    // char tmp[20];
    // sprintf(tmp, "--%d-%d--\n", model_var, order);
    // debugSerial.write(tmp);
    // sscanf(order, "%d,%d,%d,%d,%d", &throttle, &roll, &yaw, &pitch, &aux);
    // switch (model_var) {
    //     case 0:
    //         model1_func(order);
    //         break;
    //     case 1:
    //         model2_func(); // OA model
    //         break;
    //     case 2:
    //         model3_func(); // follow model
    //         break;
    //     case 3:
    //         model4_func(); // Tracking model
    //         break;
    //     default: ;
    // }
    //
    delay(1);
}

/**
void model1_func(byte orders) {
    switch (orders) {
        case Stop:
            Motor(Stop, 0);
            break;
        case Forward:
            Motor(Forward, 250);
            break;
        case Backward:
            Motor(Backward, 250);
            break;
        case Left:
            Motor(Left, 250);
            break;
        case Right:
            Motor(Right, 250);
            break;
        case Top_Left:
            Motor(Top_Left, 250);
            break;
        case Top_Right:
            Motor(Top_Right, 250);
            break;
        case Bottom_Left:
            Motor(Bottom_Left, 250);
            break;
        case Bottom_Right:
            Motor(Bottom_Right, 250);
            break;
        case Clockwise:
            Motor(Clockwise, 250);
            break;
        case MotorLeft:
            motorleft();
            break;
        case MotorRight:
            motorright();
            break;
        default:
            // debugSerial.println(".");
            order = 0;
            Motor(Stop, 0);
            break;
    }
}


void model2_func() // OA
{
    MOTORservo.write(90);
    UT_distance = SR04(Trig_PIN, Echo_PIN);
    Serial.println(UT_distance);
    middleDistance = UT_distance;

    if (middleDistance <= 25) {
        Motor(Stop, 0);
        for (int i = 0; i < 500; i++) {
            delay(1);
            RXpack_func();
            if (model_var != 1)
                return;
        }
        MOTORservo.write(10);
        for (int i = 0; i < 300; i++) {
            delay(1);
            RXpack_func();
            if (model_var != 1)
                return;
        }
        rightDistance = SR04(Trig_PIN, Echo_PIN); //SR04();
        Serial.print("rightDistance:  ");
        Serial.println(rightDistance);
        MOTORservo.write(90);
        for (int i = 0; i < 300; i++) {
            delay(1);
            RXpack_func();
            if (model_var != 1)
                return;
        }
        MOTORservo.write(170);
        for (int i = 0; i < 300; i++) {
            delay(1);
            RXpack_func();
            if (model_var != 1)
                return;
        }
        leftDistance = SR04(Trig_PIN, Echo_PIN); //SR04();
        Serial.print("leftDistance:  ");
        Serial.println(leftDistance);
        MOTORservo.write(90);
        if ((rightDistance < 20) && (leftDistance < 20)) {
            Motor(Backward, 180);
            for (int i = 0; i < 1000; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
            Motor(CountClockwise, 250);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
        } else if (rightDistance < leftDistance) {
            Motor(Stop, 0);
            for (int i = 0; i < 100; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
            Motor(Backward, 180);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
            Motor(CountClockwise, 250);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
        } //turn right
        else if (rightDistance > leftDistance) {
            Motor(Stop, 0);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
            Motor(Backward, 180);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
            Motor(Clockwise, 250);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
        } else {
            Motor(Backward, 180);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
            Motor(Clockwise, 250);
            for (int i = 0; i < 500; i++) {
                delay(1);
                RXpack_func();
                if (model_var != 1)
                    return;
            }
        }
    } else {
        Motor(Forward, 250);
    }
}

void model3_func() // follow model
{
    MOTORservo.write(90);
    UT_distance = SR04(Trig_PIN, Echo_PIN);
    Serial.println(UT_distance);
    if (UT_distance < 15) {
        Motor(Backward, 200);
    } else if (15 <= UT_distance && UT_distance <= 20) {
        Motor(Stop, 0);
    } else if (20 <= UT_distance && UT_distance <= 25) {
        Motor(Forward, 180);
    } else if (25 <= UT_distance && UT_distance <= 50) {
        Motor(Forward, 220);
    } else {
        Motor(Stop, 0);
    }
}

void model4_func() // tracking model
{
    MOTORservo.write(90);
    Left_Tra_Value = analogRead(LEFT_LINE_TRACJING);
    Center_Tra_Value = analogRead(CENTER_LINE_TRACJING);
    Right_Tra_Value = analogRead(right_LINE_TRACJING);
    if (Left_Tra_Value < Black_Line && Center_Tra_Value >= Black_Line && Right_Tra_Value < Black_Line) {
        Motor(Forward, 250);
    } else if (Left_Tra_Value >= Black_Line && Center_Tra_Value >= Black_Line && Right_Tra_Value < Black_Line) {
        Motor(CountClockwise, 220);
    } else if (Left_Tra_Value >= Black_Line && Center_Tra_Value < Black_Line && Right_Tra_Value < Black_Line) {
        Motor(CountClockwise, 250);
    } else if (Left_Tra_Value < Black_Line && Center_Tra_Value < Black_Line && Right_Tra_Value >= Black_Line) {
        Motor(Clockwise, 250);
    } else if (Left_Tra_Value < Black_Line && Center_Tra_Value >= Black_Line && Right_Tra_Value >= Black_Line) {
        Motor(Clockwise, 220);
    } else if (Left_Tra_Value >= Black_Line && Center_Tra_Value >= Black_Line && Right_Tra_Value >= Black_Line) {
        Motor(Stop, 0);
    }
}

void motorleft() //servo
{
    MOTORservo.write(angle);
    angle += 1;
    if (angle >= 180) angle = 180;
    delay(10);
}

void motorright() //servo
{
    MOTORservo.write(angle);
    angle -= 1;
    if (angle <= 1) angle = 1;
    delay(10);
}
*/

void Motor(int Dir, int Speed) // motor drive
{
    digitalWrite(EN_PIN, LOW);
    analogWrite(PWM1_PIN, Speed);
    analogWrite(PWM2_PIN, Speed);

    digitalWrite(STCP_PIN, LOW);
    shiftOut(DATA_PIN, SHCP_PIN, MSBFIRST, Dir);
    digitalWrite(STCP_PIN, HIGH);
}

float SR04(int Trig, int Echo) // ultrasonic measured distance
{
    digitalWrite(Trig, LOW);
    delayMicroseconds(2);
    digitalWrite(Trig, HIGH);
    delayMicroseconds(10);
    digitalWrite(Trig, LOW);
    float distance = pulseIn(Echo, HIGH) / 58.00;
    delay(10);

    return distance;
}

void RXpack_func() //Receive data
{
    if (Serial.available() > 0) {
        delay(1); // delay 1MS
        //     // debugSerial.println("Waiting for RX_package...\n");
        if (Serial.readBytes(RX_package, 7)) {
            // char *msg = format("RX_package: %d %d %d %d %d %d %d\n", RX_package[0], RX_package[1], RX_package[2],
            //                    RX_package[3], RX_package[4], RX_package[5], RX_package[6]);
            // Serial.println(msg);
            // free(msg);
            if (RX_package[0] == 0xA5 && RX_package[6] == 0x5A) // The header and tail of the packet are verified
            {
                forward = RX_package[1];
                forward = forward > 100 ? forward - 256 : forward;

                right = RX_package[2];
                right = right > 100 ? right - 256 : right;

                roll = RX_package[3];
                roll = roll > 100 ? roll - 256 : roll;

                yaw = RX_package[4];
                yaw = yaw > 100 ? yaw - 256 : yaw;

                aux = RX_package[5];
                aux = aux > 100 ? aux - 256 : aux;
                // msg = format("forward: %d, right: %d, yaw: %d, pitch: %d, aux: %d\n", forward, right, yaw, pitch, aux);
                // Serial.println(msg);
                // free(msg);
                // order = RX_package[1];
                // if (order == Moedl1) {
                //     model_var = 0;
                // } else if (order == Moedl2) {
                //     model_var = 1;
                // } else if (order == Moedl3) {
                //     model_var = 2;
                // } else if (order == Moedl4) {
                //     model_var = 3;
                // }
                //////////////////////////////
                // switch (RX_package[1])
                // {
                // case Stop:
                //     debugSerial.println("Stop");
                //     break;
                // case Forward:
                //     debugSerial.println("Forward");
                //     break;
                // case Backward:
                //     debugSerial.println("Backward");
                //     break;
                // case Turn_Left:
                //     debugSerial.println("Turn_Left");
                //     break;
                // case Turn_Right:
                //     debugSerial.println("Turn_Right");
                //     break;
                // case Top_Left:
                //     debugSerial.println("Top_Left");
                //     break;
                // case Bottom_Left:
                //     debugSerial.println("Bottom_Left");
                //     break;
                // case Top_Right:
                //     debugSerial.println("Top_Right");
                //     break;
                // case Bottom_Right:
                //     debugSerial.println("Bottom_Right");
                //     break;
                // case Clockwise:
                //     debugSerial.println("Clockwise");
                //     break;
                // case MotorLeft:
                //     debugSerial.println("MotorLeft");
                //     break;
                // case MotorRight:
                //     debugSerial.println("MotorRight");
                //     break;
                // case Moedl1:
                //     debugSerial.println("Moedl1");
                //     break;
                // case Moedl2:
                //     debugSerial.println("Moedl2");
                //     break;
                // case Moedl3:
                //     debugSerial.println("Moedl3");
                //     break;
                // case Moedl4:
                //     debugSerial.println("Moedl4");
                //     break;
                // default:
                //     break;
                // }
            }
        }
    }
}
