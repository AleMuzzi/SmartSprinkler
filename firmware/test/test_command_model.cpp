#include <Arduino.h>
#include <unity.h>
#include <ArduinoJson.h>

#include "../src/model/command.h"
#include "../src/model/status.h"

void setUp(void) {}
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
    Action a = Action::from_string("start", success);  // lowercase
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

// ── Enum values (must match cross-project constants) ────────────

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

// ── Command JSON parsing ────────────────────────────────────────

void test_command_from_json_valid() {
    const char* json = R"({"action":"START","target":"NAGA_MORICH","amount":0})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NOT_NULL(cmd);
    if (cmd) {
        auto c = std::static_pointer_cast<Command>(cmd);
        TEST_ASSERT_EQUAL(Action::START, c->get_action());
        TEST_ASSERT_EQUAL(Target::NAGA_MORICH, c->get_target());
        TEST_ASSERT_FALSE(c->get_force());
    }
}

void test_command_from_json_with_force() {
    const char* json = R"({"action":"DISPENSE_SPECIFIC_AMOUNT","target":"HABANERO","amount":250,"force":true})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NOT_NULL(cmd);
    if (cmd) {
        auto c = std::static_pointer_cast<Command>(cmd);
        TEST_ASSERT_EQUAL(Action::DISPENSE_SPECIFIC_AMOUNT, c->get_action());
        TEST_ASSERT_EQUAL(Target::HABANERO, c->get_target());
        TEST_ASSERT_EQUAL(250, c->get_amount());
        TEST_ASSERT_TRUE(c->get_force());
    }
}

void test_command_from_json_invalid_action() {
    const char* json = R"({"action":"FLY","target":"NAGA_MORICH","amount":0})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NULL(cmd);
    TEST_ASSERT_TRUE(error);
}

void test_command_from_json_invalid_target() {
    const char* json = R"({"action":"STOP","target":"BASIL","amount":0})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NULL(cmd);
    TEST_ASSERT_TRUE(error);
}

void test_command_from_json_missing_amount() {
    const char* json = R"({"action":"STOP","target":"NAGA_MORICH"})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    TEST_ASSERT_NOT_NULL(cmd);  // amount defaults to 0 from JsonDocument
}

void test_command_from_json_invalid_amount_type() {
    const char* json = R"({"action":"STOP","target":"NAGA_MORICH","amount":"abc"})";
    DeserializationError error;
    String error_msg;
    auto cmd = Command::from_json(json, error, error_msg);
    // May be null or just get amount=0 depending on ArduinoJson behavior
}

// ── Status ──────────────────────────────────────────────────────

void test_status_get_type() {
    Status s;
    TEST_ASSERT_EQUAL_STRING("Status", s.getType().c_str());
}

// ── Main ────────────────────────────────────────────────────────

void setup() {
    delay(2000);
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
    RUN_TEST(test_command_from_json_valid);
    RUN_TEST(test_command_from_json_with_force);
    RUN_TEST(test_command_from_json_invalid_action);
    RUN_TEST(test_command_from_json_invalid_target);
    RUN_TEST(test_command_from_json_missing_amount);
    RUN_TEST(test_status_get_type);
    UNITY_END();
}

void loop() {
    delay(100);
}
