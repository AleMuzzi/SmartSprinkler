//
// Created by Alessandro Muzzi on 06/09/25.
//

#include <Arduino.h>
#include <HardwareSerial.h>

#include "plant_sprinkler.h"

// Binary-valve routing (PCB): 3 x 12V solenoid valves in a binary-tree
// configuration, driven by the Arduino Nano (D6/D7/D8 relay drivers).
//
//   Valve A selects left (0) / right (1) branch.
//   Valve B selects Output 1 (0) / Output 2 (1) on the left branch.
//   Valve C selects Output 3 (0) / Output 4 (1) on the right branch.
//
// Classic binary mapping:
//   ROSMARINO       → A=0 B=0 C=0
//   CAROLINA_REAPER → A=0 B=1 C=0
//   NAGA_MORICH     → A=1 B=0 C=0
//   HABANERO        → A=1 B=0 C=1
//
// State is pushed to the Nano as "V:abc\n" ("1" = valve open, "0" = closed).

#define NANO_VALVE_CMD_PREFIX 'V'

extern void log_event(const char* category, const char* level, const char* event, const char* message);
extern void log_event_details(const char* category, const char* level, const char* event,
                              const char* message, const char* details_json);
extern HardwareSerial NanoSerial;

class ValveSprinkler final : public PlantSprinkler {
public:
    void begin() override {
        // Force every valve closed at boot so nothing waters unexpectedly.
        apply(0, 0, 0);
        Serial.println("Valve routing: all valves closed at boot");
    }

    void tick_calibration() override {
        // No calibration needed: solenoid valves are digital.
    }

    void route_to(Target::Value target) override {
        int a, b, c;
        switch (target) {
            case Target::ROSMARINO:       a = 0; b = 0; c = 0; break;
            case Target::CAROLINA_REAPER: a = 0; b = 1; c = 0; break;
            case Target::NAGA_MORICH:     a = 1; b = 0; c = 0; break;
            case Target::HABANERO:        a = 1; b = 0; c = 1; break;
            default:                      a = 0; b = 0; c = 0; break;
        }
        apply(a, b, c);
        const String state = String(a) + String(b) + String(c);
        const String details = String("{\"valves\":\"" + state + "\"}");
        log_event_details("command", "info", "valves_set", ("Valves set to " + state).c_str(), details.c_str());
        Serial.println("Valves set to A=" + String(a) + " B=" + String(b) + " C=" + String(c));
    }

    bool is_busy() const override {
        return false;
    }

    void reset_selection() override {
        if (valve_state != "000") {
            apply(0, 0, 0);
            log_event_details("command", "info", "valves_closed",
                              "All valves closed", R"({"valves":"000"})");
            Serial.println("All valves closed");
        }
    }

    unsigned long settle_ms() const override {
        return 500;
    }

    void fill_status(Hashtable<String, String>& status) const override {
        status.put("valve_state", valve_state.isEmpty() ? "000" : valve_state);
    }

private:
    void apply(int a, int b, int c) {
        valve_state = String(a) + String(b) + String(c);
        const String cmd = String(NANO_VALVE_CMD_PREFIX) + ":" + valve_state + "\n";
        NanoSerial.print(cmd);
    }

    String valve_state;
};

PlantSprinkler& plant_sprinkler() {
    static ValveSprinkler instance;
    return instance;
}