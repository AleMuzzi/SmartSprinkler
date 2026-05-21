#include <unity.h>

#include "arduino_mock.h"

SerialMock Serial;
WiFiClass WiFi;
int _mock_pin_modes[40];
int _mock_pin_values[40];
int _mock_pin_mode_count = 0;
unsigned long _mock_millis = 0;

#include "../src/model/command.h"
#include "../src/model/status.h"

void setUp(void) {
    for (int i = 0; i < 40; i++) {
        _mock_pin_modes[i] = 0;
        _mock_pin_values[i] = 0;
    }
    _mock_pin_mode_count = 0;
    _mock_millis = 0;
}

void tearDown(void) {}

// ── Action from_string ──────────────────────────────────────────

void test_action_from_string_stop() {
    bool success = false;
    Action a = Action::from_string("STOP", success);
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(Action::STOP, a.get());
}

void test_action_from_string_start() {
    bool success = false;
    Action a = Action::from_string("START", success);
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(Action::START, a.get());
}

void test_action_from_string_dispense() {
    bool success = false;
    Action a = Action::from_string("DISPENSE_SPECIFIC_AMOUNT", success);
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(Action::DISPENSE_SPECIFIC_AMOUNT, a.get());
}

void test_action_from_string_invalid() {
    bool success = true;
    Action a = Action::from_string("INVALID", success);
    TEST_ASSERT_FALSE(success);
    TEST_ASSERT_EQUAL(Action::STOP, a.get());
}

void test_action_from_string_case_sensitive() {
    bool success = true;
    Action a = Action::from_string("stop", success);
    TEST_ASSERT_FALSE(success);
}

// ── Target from_string ──────────────────────────────────────────

void test_target_from_string_habanero() {
    bool success = false;
    Target t = Target::from_string("HABANERO", success);
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(Target::HABANERO, t.get());
}

void test_target_from_string_naga_morich() {
    bool success = false;
    Target t = Target::from_string("NAGA_MORICH", success);
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(Target::NAGA_MORICH, t.get());
}

void test_target_from_string_carolina_reaper() {
    bool success = false;
    Target t = Target::from_string("CAROLINA_REAPER", success);
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(Target::CAROLINA_REAPER, t.get());
}

void test_target_from_string_rosmarino() {
    bool success = false;
    Target t = Target::from_string("ROSMARINO", success);
    TEST_ASSERT_TRUE(success);
    TEST_ASSERT_EQUAL(Target::ROSMARINO, t.get());
}

void test_target_from_string_invalid() {
    bool success = true;
    Target t = Target::from_string("BASIL", success);
    TEST_ASSERT_FALSE(success);
    TEST_ASSERT_EQUAL(Target::NAGA_MORICH, t.get());
}

// ── Command enumeration values (must match other projects) ──────

void test_action_enum_values() {
    TEST_ASSERT_EQUAL(0, Action::STOP);
    TEST_ASSERT_EQUAL(1, Action::START);
    TEST_ASSERT_EQUAL(2, Action::DISPENSE_SPECIFIC_AMOUNT);
}

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

// ── Status ──────────────────────────────────────────────────────

void test_status_get_type() {
    Status s;
    TEST_ASSERT_EQUAL_STRING("Status", s.getType().c_str());
}

// ── Main ────────────────────────────────────────────────────────

int main(int argc, char** argv) {
    UNITY_BEGIN();
    RUN_TEST(test_action_from_string_stop);
    RUN_TEST(test_action_from_string_start);
    RUN_TEST(test_action_from_string_dispense);
    RUN_TEST(test_action_from_string_invalid);
    RUN_TEST(test_action_from_string_case_sensitive);
    RUN_TEST(test_action_enum_values);
    RUN_TEST(test_target_from_string_habanero);
    RUN_TEST(test_target_from_string_naga_morich);
    RUN_TEST(test_target_from_string_carolina_reaper);
    RUN_TEST(test_target_from_string_rosmarino);
    RUN_TEST(test_target_from_string_invalid);
    RUN_TEST(test_target_enum_values);
    RUN_TEST(test_command_construction);
    RUN_TEST(test_command_with_force);
    RUN_TEST(test_command_with_amount);
    RUN_TEST(test_command_get_type);
    RUN_TEST(test_status_get_type);
    return UNITY_END();
}
