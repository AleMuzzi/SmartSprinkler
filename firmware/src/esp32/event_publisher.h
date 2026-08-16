#pragma once

#include <Arduino.h>

#include "MongooseHttpClient.h"
#include "event_log.h"

// Batches pending events from EventLog and POSTs them to the BayesianSprinkler
// server (``POST /api/esp/events``) using the shared Mongoose client.
//
// The publisher is serviced by CommandManager::poll()'s Mongoose event loop and
// rates itself on a simple backoff (5s -> 60s) to avoid hammering an
// unreachable server. The request object, URI and body are members so their
// memory stays valid for the whole request lifetime (the client keeps raw
// pointers, see MongooseHttpClientRequest).
class EventPublisher {
public:
    explicit EventPublisher(EventLog* log) : _log(log) {}

    // ``url`` is the server base URL (e.g. ``http://192.168.1.100:8080``).
    // Empty string disables the publisher.
    void setServerUrl(const String& url);

    // Call from loop(); decides whether a new batch should be sent.
    void tick();

private:
    void sendBatch();
    void onResponse(MongooseHttpClientResponse* resp);
    void onClose();

    static const size_t MAX_EVENTS_PER_BATCH = 20;
    static const uint32_t INITIAL_BACKOFF_MS = 5000;
    static const uint32_t MAX_BACKOFF_MS = 60000;
    static const uint32_t SEND_TIMEOUT_MS = 20000;

    EventLog* _log;
    MongooseHttpClient _client;
    String _base_url;
    bool _sending = false;
    uint32_t _last_attempt_ms = 0;
    uint32_t _backoff_ms = INITIAL_BACKOFF_MS;
    uint32_t _sent_ms = 0;

    // Keep-alive buffers for the in-flight request.
    String _batch_body;
    String _request_uri;
    MongooseHttpClientRequest* _request = nullptr;
    size_t _batch_count = 0;
};