# SmartSprinkler — Firmware

PlatformIO project for the ESP32-CAM board that controls the irrigation pump, routes water via 3-way solenoid valves to 4 plants, and exposes sensor readings via HTTP.

## Hardware

### Pinout

| Component             | GPIO                                                     | Notes                                 |
|-----------------------|----------------------------------------------------------|---------------------------------------|
| Camera (AI-Thinker)   | 0, 5, 18, 19, 21, 22, 23, 25, 26, 27, 32, 34, 35, 36, 39 | ESP32-CAM fixed pinout                |
| DHT22 (temp/humidity) | 2                                                        |                                       |
| Water pump relay      | 12                                                       | Active HIGH                           |
| Valve relay 1 (LSB)   | 13                                                       | 3-way 2-position solenoid             |
| Valve relay 2         | 15                                                       | 3-way 2-position solenoid             |
| Valve relay 3 (MSB)   | 16                                                       | 3-way 2-position solenoid             |
| Camera LED flash      | 4                                                        |                                       |
| UART (ESP↔Nano)       | 1 (TX), 3 (RX)                                           | Shared with programming port          |

### Valve-to-Plant Mapping

3 valves form a binary cascade selecting 1 of 4 outputs:

| Plant           | V1 (GPIO13) | V2 (GPIO15) | V3 (GPIO16) | Path          |
|-----------------|-------------|-------------|-------------|---------------|
| Habanero        | OFF         | OFF         | OFF         | V1→V2→plant 0 |
| Naga Morich     | OFF         | ON          | OFF         | V1→V2→plant 1 |
| Carolina Reaper | ON          | OFF         | OFF         | V1→V3→plant 0 |
| Rosmarino       | ON          | OFF         | ON          | V1→V3→plant 1 |

V1 selects which second-level valve (V2 or V3) receives water; the selected valve then routes to one of its 2 plants. The non-selected valve is kept OFF since no water reaches its branch. Plumbing: common water input → V1 input; V1 OFF output → V2 input; V1 ON output → V3 input; each V2/V3 output → one plant's drip line.

### Arduino Nano — 4-Channel Soil Moisture Hub

The ESP32-CAM has no free GPIOs for extra ADCs, so an Arduino Nano acts as a dedicated sensor co-processor.
It reads 4 HW-390 sensors and sends the values over UART on request.

#### Wiring

| Nano   | ESP32-CAM       | Sensor        |
|--------|-----------------|---------------|
| D0 RX  | GPIO 1 (TX)     |               |
| D1 TX  | GPIO 3 (RX)     |               |
| GND    | GND             |               |
| 5V     | 5V rail         |               |
| A0     |                 | HW-390 #1 (Habanero)      |
| A1     |                 | HW-390 #2 (Naga Morich)   |
| A2     |                 | HW-390 #3 (Carolina R.)   |
| A3     |                 | HW-390 #4 (Rosmarino)     |

UART is shared with the ESP32 programming port (FTDI adapter). During normal operation the FTDI is disconnected, so the Nano has exclusive use of the line. During ESP32 programming, disconnect Nano D1 from GPIO 3 to avoid TX contention.

#### Protocol

Request-response over Serial at 115200 baud:

1. ESP32 flushes RX, sends byte `'S'` (0x53)
2. Nano reads all 4 ADCs, responds with `"<a0>,<a1>,<a2>,<a3>\n"`
3. ESP32 parses the CSV line, stores raw values, and computes `soil_moisture` as the average percentage (same 0–1023 → 0–100% mapping as the original single-sensor code)

If the Nano does not respond within 100 ms, `nano_available` is set to `false` and the last known values are retained.

#### Build & upload

```bash
# ESP32 firmware (default)
pio run --target upload -e esp32

# Arduino Nano firmware
pio run --target upload -e nano --upload-port /dev/ttyUSB0
```

Replace `/dev/ttyUSB0` with the Nano's actual serial port (e.g. `/dev/cu.usbserial-*` on macOS).

#### Sensor mapping in `/status`

Each Nano ADC channel appears as a separate field in the `/status` response:

```json
{
    "soil_moisture_0": "412",
    "soil_moisture_1": "380",
    "soil_moisture_2": "501",
    "soil_moisture_3": "290"
}
```

The legacy `soil_moisture` field still reports the average percentage for backward compatibility with the Bayesian server.

## API endpoints (Mongoose, port 80)

### `GET /status`

Returns current sensor readings, valve states, and active plant:

```json
{
    "status": "ok",
    "air_temperature": "25.30",
    "air_humidity": "60.50",
    "soil_moisture": "42.00",
    "soil_moisture_0": "412",
    "soil_moisture_1": "380",
    "soil_moisture_2": "501",
    "soil_moisture_3": "290",
    "water_pump": "off",
    "valve_1": "off",
    "valve_2": "off",
    "valve_3": "off",
    "active_plant": "null"
}
```

`active_plant` contains the target name (e.g. `"NAGA_MORICH"`) when the pump is running, `"null"` when idle.

### `POST /command`

Controls the pump and valve routing:

```json
{"action": "START", "target": "NAGA_MORICH", "amount": 0}
{"action": "STOP",  "target": "NAGA_MORICH", "amount": 0}
{"action": "DISPENSE_SPECIFIC_AMOUNT", "target": "HABANERO", "amount": 500}
```

| Field | Values |
|---|---|
| `action` | `START`, `STOP`, `DISPENSE_SPECIFIC_AMOUNT` |
| `target` | `NAGA_MORICH`, `ROSMARINO`, `HABANERO`, `CAROLINA_REAPER` |
| `amount` | ml (only for `DISPENSE_SPECIFIC_AMOUNT`) |

`DISPENSE_SPECIFIC_AMOUNT` opens the valve for the selected target, turns on the pump, waits `amount / FLOW_RATE_ML_PER_MIN * 60` seconds, then stops the pump and closes the valve.

### `GET /health`

Returns `{"status":"ok"}`.

## Targets (`Target` enum)

Defined in `src/model/command.h`:

```cpp
enum Target { NAGA_MORICH=0, ROSMARINO=1, HABANERO=2, CAROLINA_REAPER=3 };
```

## Flow Rate Calibration

The default `FLOW_RATE_ML_PER_MIN` is 6000 (6 L/min). To calibrate:

1. Run `DISPENSE_SPECIFIC_AMOUNT` with a known amount (e.g. 1000 ml)
2. Measure actual dispensed water with a graduated cylinder
3. Adjust in `src/esp32/main.cpp`:
   ```cpp
   #define FLOW_RATE_ML_PER_MIN <your_value>
   ```

## Build & deploy

```bash
pio run --target upload
pio device monitor  # serial console at 115200 baud
```

WiFi credentials are hardcoded in `src/esp32/main.cpp`.
