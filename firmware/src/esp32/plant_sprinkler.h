//
// Created by Alessandro Muzzi on 06/09/25.
//

#ifndef PLANT_SPRINKLER_H
#define PLANT_SPRINKLER_H

#include <Arduino.h>

#include "utils/hashtable_ext.h"
#include "model/command.h"

// Abstraction over how water is routed to the target plant.
//
// Two implementations exist, selected at build time via build_src_filter
// (exactly one plant_sprinkler.cpp is compiled per environment):
//   - plant_sprinkler_rotary.cpp  → breadboard: SG90 rotary selector + calibration
//   - plant_sprinkler_valve.cpp   → PCB:        3 binary 12V valves driven by the Nano
//
// main.cpp should never depend on the concrete variant.
class PlantSprinkler {
public:
    virtual ~PlantSprinkler() = default;

    // Initialize the routing hardware (attach servo / force valves off).
    virtual void begin() = 0;

    // Non-blocking maintenance (rotary calibration advance; no-op on PCB).
    virtual void tick_calibration() = 0;

    // Route water to the given plant. Must be safe to call repeatedly.
    virtual void route_to(Target::Value target) = 0;

    // Reset the routing selection to its default/closed state:
    // rotary → position 0, valves → all closed. Called when dispensing ends.
    virtual void reset_selection() = 0;

    // True while the selector is busy (e.g. calibrating) and cannot route.
    virtual bool is_busy() const = 0;

    // Delay between routing to a plant and starting the pump.
    virtual unsigned long settle_ms() const = 0;

    // Adds routing-specific fields (rotary_position / valve_state) to the status.
    virtual void fill_status(Hashtable<String, String>& status) const = 0;
};

// Instance provided by whichever plant_sprinkler_*.cpp is compiled.
PlantSprinkler& plant_sprinkler();

#endif // PLANT_SPRINKLER_H