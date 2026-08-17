#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <LittleFS.h>
#include <esp_system.h>

// Local, flash-backed event log.
//
// - Day file:        /logs/esp_YYYYMMDD.log  (rotated daily at midnight)
// - Pending queue:   /logs/pending.log       (unsent events, forwarded to the server)
// - Retention:       day files older than EVENT_LOG_RETENTION_DAYS are pruned.
//
// Each line is one JSON object:
//   {"ts":<epoch>,"time":"YYYY-MM-DD HH:MM:SS","fw":"1.0.19",
//    "level":"info","category":"command","event":"command_received",
//    "message":"...","details":{...}}
//
// Clock strategy:
//   1. NTP (Europe/Rome, with DST) via configTzTime.
//   2. Server clock fallback (POST response ``server_time``) if NTP never synced.
//   3. ``ts:0`` if no clock at all (still logged to a ``esp_nosync.log``).
#define EVENT_LOG_RETENTION_DAYS 15
#define EVENT_LOG_PENDING_MAX_BYTES (64 * 1024)
#define EVENT_LOG_TAIL_MAX_BYTES (64 * 1024)

#include <cstddef>

class EventLog {
public:
    void begin();
    void append(const char* category, const char* level, const char* event, const char* message);
    void appendDetails(const char* category, const char* level, const char* event,
                       const char* message, const char* details_json);

    // Build "{\"events\":[...]}" from the head of pending.log into ``out_body``.
    // Returns the number of lines included (0 == nothing to send).
    size_t buildPendingBatch(String& out_body, size_t max_events);
    // Remove the first ``count`` lines of pending.log (successfully uploaded).
    void ackPending(size_t count);

    bool timeSynced() const;
    uint32_t epochSec() const;          // NTP epoch, else server-fallback, else 0
    void setServerEpoch(uint32_t epoch_sec);

    // Tail of the current day file (or the pre-sync fallback) as plain text,
    // for the remote ``GET /logs`` endpoint. Never more than
    // EVENT_LOG_TAIL_MAX_BYTES. Empty string when no log file exists yet.
    String recentLogsPlain(size_t max_lines) const;
    // Tail of a specific day file ``/logs/esp_<date_compact>.log`` where
    // ``date_compact`` is "YYYYMMDD". Empty string when that file does not
    // exist.
    String logsForDatePlain(const String& date_compact, size_t max_lines) const;

private:
    bool rotateToToday();
    void pruneOldFiles();
    void writeLine(const String& line);
    void writePending(const String& line);
    String localDateStr() const;
    String localDateTimeStr() const;

    // Self-heal watermark: NVS flag set just before every LittleFS write and
    // cleared after the filesystem flush returns. If a boot finds the flag
    // still armed, the previous boot crashed *during* a LittleFS write, so the
    // filesystem metadata may be inconsistent -> begin() formats it.
    void armWrite();
    void disarmWrite();

    File _day_file;
    String _day_file_name;
    uint32_t _epoch_base = 0;   // fallback clock adopted from the server
    bool _pending_overflow_logged = false;
};