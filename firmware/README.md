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
| ADS1115 SCL           | 4                                                        | Software I2C (camera LED repurposed)  |
| ADS1115 SDA           | 14                                                       | Software I2C                          |

### Valve-to-Plant Mapping

3 valves form a binary cascade selecting 1 of 4 outputs:

| Plant           | V1 (GPIO13) | V2 (GPIO15) | V3 (GPIO16) | Path          |
|-----------------|-------------|-------------|-------------|---------------|
| Habanero        | OFF         | OFF         | OFF         | V1→V2→plant 0 |
| Naga Morich     | OFF         | ON          | OFF         | V1→V2→plant 1 |
| Carolina Reaper | ON          | OFF         | OFF         | V1→V3→plant 0 |
| Rosmarino       | ON          | OFF         | ON          | V1→V3→plant 1 |

V1 selects which second-level valve (V2 or V3) receives water; the selected valve then routes to one of its 2 plants. The non-selected valve is kept OFF since no water reaches its branch. Plumbing: common water input → V1 input; V1 OFF output → V2 input; V1 ON output → V3 input; each V2/V3 output → one plant's drip line.

### ADS1115 — 4-Channel 16-bit Soil Moisture ADC

The ESP32-CAM has no free GPIOs for extra ADCs and its ADC2 conflicts with WiFi.
An external ADS1115 (I2C, 4-channel, 16-bit) provides clean isolated readings via software I2C on GPIO 14 (SDA) and GPIO 4 (SCL, camera LED repurposed).

#### Wiring

| ADS1115 | ESP32-CAM       | Sensor        |
|---------|-----------------|---------------|
| VDD     | 3.3V            |               |
| GND     | GND             |               |
| SCL     | GPIO 4          | Camera LED flash repurposed as I2C clock |
| SDA     | GPIO 14         |                                               |
| AIN0    |                 | HW-390 #1 (Habanero)      |
| AIN1    |                 | HW-390 #2 (Naga Morich)   |
| AIN2    |                 | HW-390 #3 (Carolina R.)   |
| AIN3    |                 | HW-390 #4 (Rosmarino)     |

GPIO 14 is used as digital I2C data (not analog), so the ADC2 WiFi conflict does not apply.
GPIO 4 (camera LED flash) is sacrificed because no free GPIOs remain on the ESP32-CAM.

#### Optional: AMS1117 for clean 3.3V power

For the lowest noise on ADC readings, power the ADS1115 and HW-390 sensors from an external AMS1117 5→3.3V regulator instead of the ESP32-CAM's onboard regulator:

```
5V rail → AMS1117 VIN → 3.3V → ADS1115 VDD + HW-390 VCC
```

#### Sensor mapping in `/status`

Each ADS1115 channel appears as a separate field in the `/status` response:

```json
{
    "soil_moisture_0": "412",
    "soil_moisture_1": "380",
    "soil_moisture_2": "501",
    "soil_moisture_3": "290"
}
```

The legacy `soil_moisture` field still reports the average percentage (map: 26400→0%, 0→100%) for backward compatibility with the Bayesian server.

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
pio run --target upload -e esp32
pio device monitor  # serial console at 115200 baud
```

## Unused Components

- **74HC4051 (×3)** — 8-channel analog muxes. Not needed; the ADS1115 provides 4 dedicated ADC channels. Available for future expansion (e.g. additional environmental sensors).
- **AMS1117 (×4 remaining)** — 5→3.3V regulators. One can be used for clean analog power (see above); the rest are spares.

WiFi credentials are hardcoded in `src/esp32/main.cpp`.
