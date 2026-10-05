//
// Created by Alessandro Muzzi on 06/09/25.
//

#include <Arduino.h>
#include <ESP32Servo.h>

#include "plant_sprinkler.h"

// Rotation selector (SG90 servo + 3D-printed water path selector).
//
// The rotary selector needs calibration at boot: each position is stepped
// through and the actual servo position is verified against the target. This
// is done non-blocking via tick_calibration().

#define PIN_ROTARY_SERVO 13

#define SERVO_MIN_US 500
#define SERVO_MAX_US 2500
#define SERVOFreq 50

#define ROTARY_DELTA_DEG 19.0f
#define ROTARY_START_DEG  5.0f
#define ROTARY_POSITION_COUNT 6

extern void log_event(const char* category, const char* level, const char* event, const char* message);

static Servo rotary_servo;
static int rotary_current_position = 0;
static bool rotary_calibrated = false;

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

class RotarySprinkler final : public PlantSprinkler {
public:
    void begin() override {
        rotary_servo.attach(PIN_ROTARY_SERVO, SERVO_MIN_US, SERVO_MAX_US);
        Serial.println("Rotary servo attached (GPIO 13)");
        begin_calibration();
    }

    void tick_calibration() override {
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
                log_event("system", "info", "calibration_completed", "Rotary calibration SUCCESS");
                Serial.println("Rotary calibration: SUCCESS — all positions verified");
            } else {
                rotary_calibrated = false;
                log_event("system", "warn", "calibration_partial", "Rotary calibration PARTIAL — using software tracking");
                Serial.println("Rotary calibration: PARTIAL — using software tracking");
            }
            rotary_current_position = 0;
            rotary_servo.writeMicroseconds(servo_degrees_to_us(0));
            return;
        }

        calibration_moved_at_ms = now;
        move_servo_to_position(calibration_step);
    }

    void route_to(Target::Value target) override {
        int position;
        switch (target) {
            case Target::HABANERO:        position = 4; break;
            case Target::NAGA_MORICH:     position = 3; break;
            case Target::CAROLINA_REAPER: position = 2; break;
            case Target::ROSMARINO:       position = 1; break;
            default:                      position = 0;
        }
        move_servo_to_position(position);
    }

    bool is_busy() const override {
        return calibration_in_progress;
    }

    void reset_selection() override {
        // Return the selector to its home position (unused output 0).
        move_servo_to_position(0);
    }

    unsigned long settle_ms() const override {
        return 500;
    }

    void fill_status(Hashtable<String, String>& status) const override {
        status.put("rotary_position", rotary_calibrated ? String(rotary_current_position) : "uncalibrated");
    }

private:
    void begin_calibration() {
        Serial.println("Starting rotary calibration (non-blocking)...");
        log_event("system", "info", "calibration_started", "Rotary calibration started");
        calibration_in_progress = true;
        calibration_step = 0;
        calibration_all_success = true;
        calibration_moved_at_ms = millis();
        move_servo_to_position(0);
    }

    bool calibration_in_progress = false;
    int calibration_step = 0;
    bool calibration_all_success = true;
    unsigned long calibration_moved_at_ms = 0;
};

PlantSprinkler& plant_sprinkler() {
    static RotarySprinkler instance;
    return instance;
}