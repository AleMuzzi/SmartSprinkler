# SmartSprinkler — Firmware

PlatformIO project for the ESP32-CAM board that controls the irrigation pump and exposes sensor readings via HTTP.

## Hardware

| Component | GPIO | Notes |
|---|---|---|
| DHT22 (temp/humidity) | GPIO 2 | Adafruit DHT sensor library |
| HW-390 soil moisture | GPIO 14 | Analog read, 0-1023 mapped to 0-100% |
| Water pump relay | GPIO 12 | Active HIGH |
| (Optional) MQ-135 air quality | — | Not yet wired in the active code |

## API endpoints (Mongoose, port 80)

### `GET /status`

Returns current sensor readings as JSON:

```json
{
    "status": "ok",
    "air_temperature": "25.30",
    "air_humidity": "60.50",
    "soil_moisture": "42.00",
    "water_pump": "off"
}
```

### `POST /command`

Controls the pump relay:

```json
{"action": "START", "target": "PEPERONCINO", "amount": 0}
{"action": "STOP",  "target": "PEPERONCINO", "amount": 0}
```

| Field | Values |
|---|---|
| `action` | `START`, `STOP` |
| `target` | `PEPERONCINO`, `ROSMARINO` (extend `Target` enum for more plants) |
| `amount` | ml (reserved for `DISPENSE_SPECIFIC_AMOUNT`, not yet implemented) |

### `GET /health`

Returns `{"status":"ok"}`.

## Targets (`Target` enum)

The firmware ships with `PEPERONCINO` and `ROSMARINO`. When adding new plants to the Bayesian server or mobile app, add them to `src/model/command.h`:

```cpp
enum Target { PEPERONCINO=0, ROSMARINO=1, HABANERO=2, CAROLINA_REAPER=3 };
```

## Build & deploy

```bash
pio run --target upload
pio device monitor  # serial console at 115200 baud
```

WiFi credentials are hardcoded in `src/esp32/main.cpp`.
