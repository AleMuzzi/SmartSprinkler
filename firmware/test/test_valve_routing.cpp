#include <Arduino.h>
#include <unity.h>

#include "../src/model/command.h"
#include "../src/sensors/actuator.h"

#define PIN_VALVE_1 13
#define PIN_VALVE_2 15
#define PIN_VALVE_3 16

Actuator valve_1(PIN_VALVE_1);
Actuator valve_2(PIN_VALVE_2);
Actuator valve_3(PIN_VALVE_3);

void plant_to_valves(Target::Value target) {
    switch (target) {
        case Target::HABANERO:
            valve_1.switch_off();
            valve_2.switch_off();
            valve_3.switch_off();
            break;
        case Target::NAGA_MORICH:
            valve_1.switch_off();
            valve_2.switch_on();
            valve_3.switch_off();
            break;
        case Target::CAROLINA_REAPER:
            valve_1.switch_on();
            valve_2.switch_off();
            valve_3.switch_off();
            break;
        case Target::ROSMARINO:
            valve_1.switch_on();
            valve_2.switch_off();
            valve_3.switch_on();
            break;
    }
}

void setUp(void) {
    valve_1.switch_off();
    valve_2.switch_off();
    valve_3.switch_off();
}

void tearDown(void) {}

// ── Valve routing tests ─────────────────────────────────────────

void test_habanero_routing() {
    plant_to_valves(Target::HABANERO);
    // V1 OFF → V2 branch; V2 OFF → plant 0 on V2
    TEST_ASSERT_FALSE(valve_1.is_on());
    TEST_ASSERT_FALSE(valve_2.is_on());
    TEST_ASSERT_FALSE(valve_3.is_on());
}

void test_naga_morich_routing() {
    plant_to_valves(Target::NAGA_MORICH);
    // V1 OFF → V2 branch; V2 ON → plant 1 on V2
    TEST_ASSERT_FALSE(valve_1.is_on());
    TEST_ASSERT_TRUE(valve_2.is_on());
    TEST_ASSERT_FALSE(valve_3.is_on());
}

void test_carolina_reaper_routing() {
    plant_to_valves(Target::CAROLINA_REAPER);
    // V1 ON → V3 branch; V3 OFF → plant 0 on V3
    TEST_ASSERT_TRUE(valve_1.is_on());
    TEST_ASSERT_FALSE(valve_2.is_on());
    TEST_ASSERT_FALSE(valve_3.is_on());
}

void test_rosmarino_routing() {
    plant_to_valves(Target::ROSMARINO);
    // V1 ON → V3 branch; V3 ON → plant 1 on V3
    TEST_ASSERT_TRUE(valve_1.is_on());
    TEST_ASSERT_FALSE(valve_2.is_on());
    TEST_ASSERT_TRUE(valve_3.is_on());
}

void test_transition_habanero_to_reaper() {
    plant_to_valves(Target::HABANERO);
    plant_to_valves(Target::CAROLINA_REAPER);
    TEST_ASSERT_TRUE(valve_1.is_on());
    TEST_ASSERT_FALSE(valve_2.is_on());
    TEST_ASSERT_FALSE(valve_3.is_on());
}

void test_transition_reaper_to_rosmarino() {
    plant_to_valves(Target::CAROLINA_REAPER);
    plant_to_valves(Target::ROSMARINO);
    TEST_ASSERT_TRUE(valve_1.is_on());
    TEST_ASSERT_FALSE(valve_2.is_on());
    TEST_ASSERT_TRUE(valve_3.is_on());
}

void test_branch_isolation() {
    // When V1 selects V2 branch, V3 must be OFF (isolated)
    plant_to_valves(Target::HABANERO);
    TEST_ASSERT_FALSE(valve_3.is_on());

    // When V1 selects V3 branch, V2 must be OFF (isolated)
    plant_to_valves(Target::ROSMARINO);
    TEST_ASSERT_FALSE(valve_2.is_on());
}

void test_all_valves_off_represents_one_plant() {
    // All three valves OFF → Habanero (plant 0 on V2 branch)
    plant_to_valves(Target::HABANERO);
    TEST_ASSERT_FALSE(valve_1.is_on());
    TEST_ASSERT_FALSE(valve_2.is_on());
    TEST_ASSERT_FALSE(valve_3.is_on());

    // Verify that same state is not achievable by other plants
    plant_to_valves(Target::NAGA_MORICH);
    TEST_ASSERT_TRUE(valve_2.is_on());
}

// ── Main ────────────────────────────────────────────────────────

void setup() {
    delay(2000);
    UNITY_BEGIN();
    RUN_TEST(test_habanero_routing);
    RUN_TEST(test_naga_morich_routing);
    RUN_TEST(test_carolina_reaper_routing);
    RUN_TEST(test_rosmarino_routing);
    RUN_TEST(test_transition_habanero_to_reaper);
    RUN_TEST(test_transition_reaper_to_rosmarino);
    RUN_TEST(test_branch_isolation);
    RUN_TEST(test_all_valves_off_represents_one_plant);
    UNITY_END();
}

void loop() {
    delay(100);
}
