#include "event_publisher.h"

#include <ArduinoJson.h>
#include <WiFi.h>

void EventPublisher::setServerUrl(const String& url) {
    String trimmed = url;
    while (trimmed.endsWith("/") && trimmed.length() > 0) {
        trimmed.remove(trimmed.length() - 1);
    }
    _base_url = trimmed;
    _backoff_ms = INITIAL_BACKOFF_MS;
}

void EventPublisher::tick() {
    if (_base_url.length() == 0 || _sending) {
        return;
    }
    if (WiFi.status() != WL_CONNECTED) {
        _last_attempt_ms = millis();
        return;
    }
    if (millis() - _last_attempt_ms < _backoff_ms) {
        return;
    }
    _last_attempt_ms = millis();

    // Watchdog: if a connect fails synchronously the client never fires a close
    // event, so back off and let the caller retry.
    if (_sent_ms != 0 && millis() - _sent_ms > SEND_TIMEOUT_MS) {
        _sending = false;
        _request = nullptr;
        _sent_ms = 0;
    }

    sendBatch();
}

void EventPublisher::sendBatch() {
    const size_t n = _log->buildPendingBatch(_batch_body, MAX_EVENTS_PER_BATCH);
    if (n == 0) {
        _backoff_ms = INITIAL_BACKOFF_MS;
        _batch_body = "";
        return;
    }
    _batch_count = n;

    // Reuse a JsonDocument right away is not needed; batch body is already JSON.
    _request_uri = _base_url + "/api/esp/events";
    _request = _client.beginRequest(_request_uri.c_str());
    _request->setMethod(HTTP_POST)
        ->setContentType("application/json")
        ->setContent(_batch_body.c_str())
        ->onResponse([this](MongooseHttpClientResponse* resp) { onResponse(resp); })
        ->onClose([this]() { onClose(); });
    _client.send(_request);

    _sent_ms = millis();
    _sending = true;
}

void EventPublisher::onResponse(MongooseHttpClientResponse* resp) {
    if (resp == nullptr) {
        return;
    }
    const int code = resp->respCode();

    if (code >= 200 && code < 300) {
        // Server accepted the batch: drop the acked events.
        _log->ackPending(_batch_count);
        _backoff_ms = INITIAL_BACKOFF_MS;

        // Clock fallback: if NTP never synced, adopt the server-reported time.
        if (!_log->timeSynced()) {
            const String body = resp->body().toString();
            JsonDocument doc;
            if (deserializeJson(doc, body) == DeserializationError::Ok) {
                const JsonVariant server_time = doc["server_time"];
                if (!server_time.isNull() && server_time.is<uint32_t>()) {
                    _log->setServerEpoch(server_time.as<uint32_t>());
                }
            }
        }
    } else {
        // Non-2xx (4xx/5xx): retry later with growing backoff.
        if (_backoff_ms < MAX_BACKOFF_MS) {
            _backoff_ms *= 2;
        }
        if (_backoff_ms > MAX_BACKOFF_MS) {
            _backoff_ms = MAX_BACKOFF_MS;
        }
    }
}

void EventPublisher::onClose() {
    _sending = false;
    _request = nullptr;
    _sent_ms = 0;
}