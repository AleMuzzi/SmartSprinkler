"""Firmware ESP32 API contract tests.

The ESP32 firmware serves JSON over Mongoose HTTP. Mongoose sends each
response in chunks (256-byte send buffer, flushed on subsequent polls), so a
handler that stores a raw pointer to a short-lived Arduino `String` returns a
truncated/corrupt body (the historical "/status" bug).

These tests emulate that chunked send pattern against the exact documented
schema, and assert the client side (ESP32Client) always ends up with complete,
valid JSON with every expected field.
"""

import json
import socket
import threading
import time

import pytest
import requests

from bayesian_sprinkler.sensor_client import ESP32Client

THRESHOLDS = {
    "soil_moisture": {"dry": 35, "moist": 65},
    "temperature": {"low": 16, "medium": 29},
    "humidity": {"low": 45, "medium": 70},
}

STATUS_FIELDS = {
    "status": "ok",
    "air_temperature": "28.50",
    "air_humidity": "60.00",
    "soil_moisture": "45.00",
    "water_pump": "off",
    "rotary_position": "1",
    "soil_moisture_0": "80",
    "soil_moisture_1": "65",
    "soil_moisture_2": "70",
    "soil_moisture_3": "55",
    "water_low_alert": "off",
    "blocked_amount_ml": "0",
    "active_plant": "null",
    "camera_url": "192.168.1.10:81/stream",
}

HEALTH_VERSION = "1.0.0.7"


def _chunked_send(sock, payload, chunk_size=17):
    """Write a body in small chunks with a flush in between, exactly like
    Mongoose's poll-driven sendBody(): data must survive across sends."""
    for i in range(0, len(payload), chunk_size):
        sock.send(payload[i:i + chunk_size])
        time.sleep(0.001)


class FirmwareMock:
    """Minimal raw-socket HTTP server emulating the ESP32 firmware API."""

    def __init__(self, chunk_size=17):
        self.chunk_size = chunk_size
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.last_body = b""
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            try:
                self._handle(conn)
            finally:
                conn.close()

    def _handle(self, conn):
        conn.settimeout(5)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk

        line = data.split(b"\r\n")[0].decode()
        method, path, _ = line.split(" ", 2)

        if path.startswith("/status"):
            body = json.dumps(STATUS_FIELDS)
            self._respond(conn, 200, "application/json", body)
        elif path == "/health":
            self._respond(
                conn, 200, "application/json",
                f'{{"status":"ok","version":"{HEALTH_VERSION}"}}',
            )
        elif path.startswith("/command"):
            content_length = 0
            for hdr in data.split(b"\r\n")[1:]:
                if hdr.lower().startswith(b"content-length:"):
                    content_length = int(hdr.split(b":")[1].strip())
            if method == "POST":
                body_data = data.split(b"\r\n\r\n", 1)[1]
                while len(body_data) < content_length:
                    body_data += conn.recv(4096)
                self.last_body = body_data
                cmd = json.loads(body_data)
                if cmd.get("action") == "BAD_ACTION":
                    self._respond(
                        conn,
                        400,
                        "application/json",
                        '{"status":"error","error_code":"invalid_command","message":"Unknown command"}',
                    )
                else:
                    self._respond(conn, 200, "application/json", '{"status":"ok"}')
            else:
                self._respond(conn, 405, "text/plain", "")
        else:
            self._respond(conn, 404, "text/plain", "not found")

    def _respond(self, conn, code, content_type, body):
        reason = {200: "OK", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed"}[code]
        header = (
            f"HTTP/1.1 {code} {reason}\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode()
        conn.send(header)
        # Emulate Mongoose: headers in one send, body streamed in tiny chunks.
        _chunked_send(conn, body.encode(), self.chunk_size)

    def shutdown(self):
        self.sock.close()


@pytest.fixture(scope="module")
def firmware():
    mock = FirmwareMock()
    yield mock
    mock.shutdown()


@pytest.fixture(scope="module")
def client(firmware):
    return ESP32Client(
        base_url=f"http://127.0.0.1:{firmware.port}",
        thresholds=THRESHOLDS,
    )


class TestStatusSchema:
    def test_status_returns_complete_valid_json(self, client):
        status = client.get_status()
        assert status["status"] == "ok"

    def test_status_has_all_documented_fields(self, client):
        status = client.get_status()
        missing = set(STATUS_FIELDS) - set(status)
        assert not missing, f"Missing fields in /status: {sorted(missing)}"

    def test_status_field_types_are_strings(self, client):
        status = client.get_status()
        for key, value in status.items():
            assert isinstance(value, str), f"/status.{key} should be str, got {type(value).__name__}"

    def test_status_values_match_expected(self, client):
        status = client.get_status()
        for key, value in STATUS_FIELDS.items():
            assert status[key] == value, f"/status.{key}: expected {value!r}, got {status[key]!r}"

    def test_status_not_truncated_despite_chunked_send(self, client):
        # The historical bug produced a short/partial body. A complete,
        # parseable payload proves every chunk was delivered intact.
        status = client.get_status()
        assert len(status) == len(STATUS_FIELDS)

    def test_camera_url_is_present(self, client):
        status = client.get_status()
        assert status["camera_url"].startswith("192.168.1.10:81")

    def test_cors_header_present(self, firmware):
        with socket.create_connection(("127.0.0.1", firmware.port), timeout=5) as sock:
            sock.sendall(b"GET /health HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
            response = b""
            while True:
                part = sock.recv(4096)
                if not part:
                    break
                response += part
        headers = response.split(b"\r\n\r\n")[0].decode()
        assert "Access-Control-Allow-Origin: *" in headers


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        port = client.base_url.rsplit(":", 1)[1]
        resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "version": HEALTH_VERSION}

    def test_health_reports_firmware_version(self, client):
        assert client.get_firmware_version() == HEALTH_VERSION


class TestCommandEndpoint:
    def test_start_command_roundtrip(self, firmware, client):
        result = client.send_command("START", "HABANERO")
        assert result == {"status": "ok"}
        assert json.loads(firmware.last_body) == {
            "action": "START",
            "target": "HABANERO",
            "amount": 0,
        }

    def test_stop_command_roundtrip(self, firmware, client):
        client.send_command("STOP", "NAGA_MORICH")
        assert json.loads(firmware.last_body) == {
            "action": "STOP",
            "target": "NAGA_MORICH",
            "amount": 0,
        }

    def test_dispense_specific_amount_roundtrip(self, firmware, client):
        client.send_command("DISPENSE_SPECIFIC_AMOUNT", "ROSMARINO", amount=500)
        assert json.loads(firmware.last_body) == {
            "action": "DISPENSE_SPECIFIC_AMOUNT",
            "target": "ROSMARINO",
            "amount": 500,
        }

    def test_invalid_action_returns_error_json(self, firmware):
        resp = requests.post(
            f"http://127.0.0.1:{firmware.port}/command",
            json={"action": "BAD_ACTION", "target": "HABANERO", "amount": 0},
            timeout=5,
        )
        assert resp.status_code == 400
        assert resp.json()["status"] == "error"
        assert resp.json()["error_code"] == "invalid_command"


class TestUnknownEndpoint:
    def test_unknown_path_returns_404(self, firmware):
        resp = requests.get(f"http://127.0.0.1:{firmware.port}/nope", timeout=5)
        assert resp.status_code == 404


class TestClientFailureMode:
    def test_client_raises_on_invalid_json(self):
        """If the firmware regresses to a truncated body, the client must
        fail loudly instead of silently consuming broken data."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]

        def serve():
            conn, _ = sock.accept()
            conn.recv(4096)
            conn.send(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 100\r\n"  # larger than the actual body
                b"Connection: close\r\n\r\n"
                b'{"status":"o'
            )
            conn.close()
            sock.close()

        threading.Thread(target=serve, daemon=True).start()
        broken_client = ESP32Client(
            base_url=f"http://127.0.0.1:{port}",
            thresholds=THRESHOLDS,
        )
        with pytest.raises(
            (
                requests.exceptions.JSONDecodeError,
                requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
            )
        ):
            broken_client.get_status()
