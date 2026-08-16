#pragma once

// Thin logging facade used across the firmware (main.cpp, services, ...).
// ``log_event`` persists to the on-device EventLog and prints to Serial;
// ``log_event_details`` additionally embeds a raw-JSON ``details`` object.

void log_event(const char* category, const char* level, const char* event, const char* message);
void log_event_details(const char* category, const char* level, const char* event,
                       const char* message, const char* details_json);