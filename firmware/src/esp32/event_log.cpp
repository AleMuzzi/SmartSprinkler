#include "event_log.h"

#include <time.h>

#if __has_include("fw_version.h")
#include "fw_version.h"
#endif
#ifndef FW_VERSION
#define FW_VERSION "0.0.0"
#endif

// Events written to the log when other subsystems cannot produce a timestamp.
// We rely on NTP or the server fallback; see EventLog::epochSec().
static const char* LOG_DIR = "/logs";

static bool sortNameAsc(const String& a, const String& b) {
    return a < b;
}

void EventLog::begin() {
    if (!LittleFS.begin(true)) {
        Serial.println("! EventLog: LittleFS mount failed");
        return;
    }
    if (!LittleFS.exists(LOG_DIR)) {
        LittleFS.mkdir(LOG_DIR);
    }
    rotateToToday();
}

uint32_t EventLog::epochSec() const {
    time_t now = time(nullptr);
    if (now > 1600000000ULL) {  // NTP-synced wall clock
        return static_cast<uint32_t>(now);
    }
    if (_epoch_base > 0) {
        return _epoch_base + static_cast<uint32_t>(millis() / 1000);
    }
    return 0;
}

bool EventLog::timeSynced() const {
    return time(nullptr) > 1600000000ULL;
}

void EventLog::setServerEpoch(uint32_t epoch_sec) {
    // Only adopt the fallback clock when NTP is unavailable. Rebase to "now" so
    // that epochSec() keeps advancing with uptime.
    if (!timeSynced() && epoch_sec > 1600000000ULL) {
        _epoch_base = epoch_sec - static_cast<uint32_t>(millis() / 1000);
    }
}

String EventLog::localDateStr() const {
    if (!timeSynced() && _epoch_base == 0) {
        return "";
    }
    time_t now = static_cast<time_t>(epochSec());
    struct tm tmv;
    if (!localtime_r(&now, &tmv)) {
        return "";
    }
    char buf[16];
    snprintf(buf, sizeof(buf), "%04d%02d%02d", tmv.tm_year + 1900, tmv.tm_mon + 1, tmv.tm_mday);
    return String(buf);
}

bool EventLog::rotateToToday() {
    String today = localDateStr();
    if (today.length() == 0) {
        // No clock yet: keep a combined "nosync" file until a time source appears.
        today = "nosync";
    }
    if (_day_file_name == today && _day_file) {
        return true;
    }
    if (_day_file) {
        _day_file.close();
    }
    String path = String(LOG_DIR) + "/esp_" + today + ".log";
    _day_file = LittleFS.open(path.c_str(), FILE_APPEND);
    _day_file_name = today;
    if (_day_file && today != "nosync") {
        pruneOldFiles();
    }
    return static_cast<bool>(_day_file);
}

void EventLog::pruneOldFiles() {
    File root = LittleFS.open(LOG_DIR);
    if (!root || !root.isDirectory()) {
        return;
    }
    // Collect candidate day-file names (esp_YYYYMMDD.log).
    String names[64];
    size_t count = 0;
    File entry = root.openNextFile();
    while (entry && count < 64) {
        String name = String(entry.name());
        entry.close();
        if (name.startsWith("esp_") && name.endsWith(".log") && !name.startsWith("esp_nosync")) {
            names[count++] = name;
        }
        entry = root.openNextFile();
    }
    // Sort desc and delete everything beyond the retention window.
    for (size_t i = 0; i < count; i++) {
        for (size_t j = i + 1; j < count; j++) {
            if (sortNameAsc(names[j], names[i])) {
                String tmp = names[i];
                names[i] = names[j];
                names[j] = tmp;
            }
        }
    }
    size_t keep = (count > EVENT_LOG_RETENTION_DAYS) ? EVENT_LOG_RETENTION_DAYS : count;
    for (size_t i = keep; i < count; i++) {
        String path = String(LOG_DIR) + "/" + names[i];
        LittleFS.remove(path.c_str());
    }
}

void EventLog::append(const char* category, const char* level, const char* event,
                      const char* message) {
    appendDetails(category, level, event, message, nullptr);
}

void EventLog::appendDetails(const char* category, const char* level, const char* event,
                             const char* message, const char* details_json) {
    JsonDocument doc;
    doc["ts"] = epochSec();
    doc["fw"] = FW_VERSION;
    doc["level"] = level;
    doc["category"] = category;
    doc["event"] = event;
    doc["message"] = message;
    if (details_json != nullptr && details_json[0] != '\0') {
        doc["details"] = serialized(details_json);
    }

    String line;
    serializeJson(doc, line);

    if (rotateToToday() && _day_file) {
        _day_file.print(line);
        _day_file.print('\n');
        _day_file.flush();
    }

    writePending(line);
}

void EventLog::writePending(const String& line) {
    String path = String(LOG_DIR) + "/pending.log";
    File pending = LittleFS.open(path.c_str(), FILE_APPEND);
    if (!pending) {
        return;
    }
    if (pending.size() > EVENT_LOG_PENDING_MAX_BYTES && !_pending_overflow_logged) {
        _pending_overflow_logged = true;
        Serial.println("! EventLog: pending.log full, dropping outgoing events");
        pending.close();
        return;
    }
    pending.print(line);
    pending.print('\n');
    pending.flush();
    pending.close();
}

size_t EventLog::buildPendingBatch(String& out_body, size_t max_events) {
    File pending = LittleFS.open(String(LOG_DIR) + "/pending.log", FILE_READ);
    if (!pending) {
        out_body = "";
        return 0;
    }
    String items;
    size_t n = 0;
    String line;
    while (pending.available() && n < max_events) {
        int c = pending.read();
        if (c == '\n' || c == -1) {
            if (line.length() > 0) {
                if (n > 0) items += ',';
                items += line;
                n++;
            }
            line = "";
            if (c == -1) break;
        } else {
            line += static_cast<char>(c);
        }
    }
    pending.close();
    if (n == 0) {
        out_body = "";
        return 0;
    }
    out_body = "{\"events\":[";
    out_body += items;
    out_body += "]}";
    return n;
}

void EventLog::ackPending(size_t count) {
    if (count == 0) return;
    String path = String(LOG_DIR) + "/pending.log";
    File in = LittleFS.open(path.c_str(), FILE_READ);
    if (!in) return;
    String rest;
    size_t skipped = 0;
    String line;
    while (in.available()) {
        int c = in.read();
        if (c == '\n' || c == -1) {
            if (line.length() > 0) {
                if (skipped < count) {
                    skipped++;
                } else {
                    if (rest.length() > 0) rest += '\n';
                    rest += line;
                }
            }
            line = "";
            if (c == -1) break;
        } else {
            line += static_cast<char>(c);
        }
    }
    in.close();
    if (skipped == 0) return;
    File out = LittleFS.open(path.c_str(), FILE_WRITE);
    if (!out) return;
    out.print(rest);
    out.flush();
    out.close();
}