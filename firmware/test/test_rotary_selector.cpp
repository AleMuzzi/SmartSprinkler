#include <Arduino.h>
#include <unity.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>

#include "../src/model/command.h"
#include "../src/model/status.h"

extern int _rotary_position;
extern int servo_degrees_to_us(float degrees);
extern void move_servo_to_position(int position);
void calibrate_rotary();

void setUp(void) {}
void tearDown(void) {}

// ── Servo angle to microseconds ─────────────────────────────────

void test_servo_degrees_to_us_min() {
    TEST_ASSERT_EQUAL(500, servo_degrees_to_us(0.0f));
}

void test_servo_degrees_to_us_mid() {
    const int us = servo_degrees_to_us(90.0f);
    TEST_ASSERTTrue(us > 1400 && us < 1600);
}

void test_servo_degrees_to_us_max() {
    const int us = servo_degrees_to_us(180.0f);
    TEST_ASSERT_EQUAL(2500, us);
}

void test_servo_degrees_to_us_delta_15() {
    const int us0 = servo_degrees_to_us(0.0f);
    const int us15 = servo_degrees_to_us(15.0f);
    const int expected_step = (2500 - 500) * (15.0f / 180.0f);
    TEST_ASSERT_EQUAL(expected_step, us15 - us0);
}

// ── Target to rotary position mapping ────────────────────────────

void test_target_habanero_maps_to_position_0() {
    TEST_ASSERT_EQUAL(0, static_cast<int>(Target::HABANERO));
}

void test_target_naga_morich_maps_to_position_1() {
    TEST_ASSERT_EQUAL(1, static_cast<int>(Target::NAGA_MORICH));
}

void test_target_carolina_reaper_maps_to_position_2() {
    TEST_ASSERT_EQUAL(2, static_cast<int>(Target::CAROLINA_REAPER));
}

void test_target_rosmarino_maps_to_position_3() {
    TEST_ASSERT_EQUAL(3, static_cast<int>(Target::ROSMARINO));
}

// ── Action enum values ───────────────────────────────────────────

void test_action_enum_values() {
    TEST_ASSERT_EQUAL(0, Action::STOP);
    TEST_ASSERT_EQUAL(1, Action::START);
    TEST_ASSERT_EQUAL(2, Action::DISPENSE_SPECIFIC_AMOUNT);
}

// ── Target enum values (must match cross-project) ───────────────

void test_target_enum_values() {
    TEST_ASSERT_EQUAL(0, Target::NAGA_MORICH);
    TEST_ASSERT_EQUAL(1, Target::ROSMARINO);
    TEST_ASSERT_EQUAL(2, Target::HABANERO);
    TEST_ASSERT_EQUAL(3, Target::CAROLINA_REAPER);
}

// ── Command construction ────────────────────────────────────────

void test_command_construction() {
    Command cmd(Action::START, Target::NAGA_MORICH, 0, false);
    TEST_ASSERT_EQUAL(Action::START, cmd.get_action());
    TEST_ASSERT_EQUAL(Target::NAGA_MORICH, cmd.get_target());
    TEST_ASSERT_EQUAL(0, cmd.get_amount());
    TEST_ASSERT_FALSE(cmd.get_force());
}

void test_command_with_force() {
    Command cmd(Action::START, Target::HABANERO, 0, true);
    TEST_ASSERT_TRUE(cmd.get_force());
}

void test_command_with_amount() {
    Command cmd(Action::DISPENSE_SPECIFIC_AMOUNT, Target::ROSMARINO, 500, false);
    TEST_ASSERT_EQUAL(Action::DISPENSE_SPECIFIC_AMOUNT, cmd.get_action());
    TEST_ASSERT_EQUAL(Target::ROSMARINO, cmd.get_target());
    TEST_ASSERT_EQUAL(500, cmd.get_amount());
}

void test_command_get_type() {
    Command cmd(Action::STOP, Target::CAROLINA_REAPER);
    TEST_ASSERT_EQUAL_STRING("Command", cmd.getType().c_str());
}

// ── Command JSON parsing ────────────────────────────────────────

void test_command_from_json_valid() {
    const char* json = R"({"action":"START","target":"NAGA_MORICH","amount":0})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NOT_NULL(cmd);
}

void test_command_from_json_with_force() {
    const char* json = R"({"action":"DISPENSE_SPECIFIC_AMOUNT","target":"HABANERO","amount":250,"force":true})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NOT_NULL(cmd);
    if (cmd) {
        auto c = std::static_pointer_cast<Command>(cmd);
        TEST_ASSERT_TRUE(c->get_force());
        TEST_ASSERT_EQUAL(250, c->get_amount());
    }
}

void test_command_from_json_invalid_action() {
    const char* json = R"({"action":"FLY","target":"NAGA_MORICH","amount":0})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NULL(cmd);
}

void test_command_from_json_invalid_target() {
    const char* json = R"({"action":"STOP","target":"BASIL","amount":0})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NULL(cmd);
}

void test_status_get_type() {
    Status s;
    TEST_ASSERT_EQUAL_STRING("Status", s.getType().c_str());
}

// ── Main ────────────────────────────────────────────────────────

void setup() {
    delay(2000);
    UNITY_BEGIN();
    RUN_TEST(test_servo_degrees_to_us_min);
    RUN_TEST(test_servo_degrees_to_us_mid);
    RUN_TEST(test_servo_degrees_to_us_max);
    RUN_TEST(test_servo_degrees_to_us_delta_15);
    RUN_TEST(test_target_habanero_maps_to_position_0);
    RUN_TEST(test_target_naga_morich_maps_to_position_1);
    RUN_TEST(test_target_carolina_reaper_maps_to_position_2);
    RUN_TEST(test_target_rosmarino_maps_to_position_3);
    RUN_TEST(test_action_enum_values);
    RUN_TEST(test_target_enum_values);
    RUN_TEST(test_command_construction);
    RUN_TEST(test_command_with_force);
    RUN_TEST(test_command_with_amount);
    RUN_TEST(test_command_get_type);
    RUN_TEST(test_command_from_json_valid);
    RUN_TEST(test_command_from_json_with_force);
    RUN_TEST(test_command_from_json_invalid_action);
    RUN_TEST(test_command_from_json_invalid_target);
    RUN_TEST(test_status_get_type);
    UNITY_END();
}

void loop() {
    delay(100);
}