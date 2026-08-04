#!/usr/bin/env python3
"""Mock ESP32 server for SmartSprinkler testing.

Usage:
    python mock_esp.py                      # starts on port 8081, water_low_alert=off
    python mock_esp.py --port 8081 --water-low    # starts with water_low_alert=on
    python mock_esp.py --toggle                       # toggle alert and exit
    python mock_esp.py --set on                      # set alert on and exit
    python mock_esp.py --set off                     # set alert off and exit

While running, press 't' to toggle alert, 'q' to quit.
"""

import argparse
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

DEFAULT_PORT = 8081

water_low_alert = "off"
lock = threading.Lock()


class ESPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def do_GET(self):
        if self.path == "/status":
            with lock:
                response = {
                    "soil_moisture": "45.00",
                    "air_humidity": "62.30",
                    "water_low_alert": water_low_alert,
                    "water_pump": "off",
                    "soil_moisture_0": "420",
                    "active_plant": "null",
                    "status": "ok",
                    "soil_moisture_1": "380",
                    "soil_moisture_2": "510",
                    "soil_moisture_3": "290",
                    "blocked_amount_ml": "0",
                    "camera_url": "192.168.1.10:81/stream",
                    "rotary_position": "2",
                    "air_temperature": "26.50",
                }
            body = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        elif self.path == "/water_alert":
            with lock:
                response = {"alert": water_low_alert == "on"}
            body = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/command":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode())
                print(f"Received command: {data}")
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()


def toggle_alert():
    global water_low_alert
    with lock:
        water_low_alert = "on" if water_low_alert == "off" else "off"
    print(f"water_low_alert = {water_low_alert}")


def set_alert(value: str):
    global water_low_alert
    if value not in ("on", "off"):
        raise ValueError(f"Invalid value: {value}")
    with lock:
        water_low_alert = value
    print(f"water_low_alert = {water_low_alert}")


def run_server(port: int):
    server = HTTPServer(("0.0.0.0", port), ESPHandler)
    print(f"Mock ESP32 running on http://0.0.0.0:{port}")
    print(f"  GET  http://localhost:{port}/status      → ESP status JSON")
    print(f"  GET  http://localhost:{port}/water_alert → {{alert: bool}}")
    print(f"  POST http://localhost:{port}/command     → accepts commands")
    print(f"  GET  http://localhost:{port}/health      → health check")
    print(f"\nPress 't' to toggle water_low_alert, 'q' to quit")
    print("-" * 50)

    def key_reader():
        try:
            while True:
                ch = input()
                if ch.lower() == "t":
                    toggle_alert()
                elif ch.lower() == "q":
                    print("Shutting down...")
                    server.shutdown()
                    break
        except (EOFError, KeyboardInterrupt):
            server.shutdown()

    t = threading.Thread(target=key_reader, daemon=True)
    t.start()
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock ESP32 for SmartSprinkler")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default {DEFAULT_PORT})")
    parser.add_argument("--toggle", action="store_true", help="Toggle water_low_alert and exit")
    parser.add_argument("--set", choices=["on", "off"], help="Set water_low_alert and exit")
    args = parser.parse_args()

    if args.toggle:
        toggle_alert()
    elif args.set:
        set_alert(args.set)
    else:
        run_server(args.port)
