# SmartSprinkler — Firmware

PlatformIO project for the ESP32-CAM board that controls the irrigation pump, routes water via a rotary selector (SG90 servo) to 4 plants, and exposes sensor readings via HTTP.

## Hardware
![ESP32-CAM-Pinout.png](res/ESP32-CAM-Pinout.png)

### Pinout

| Component             | GPIO       | Notes                                              |
|-----------------------|------------|----------------------------------------------------|
| Camera (AI-Thinker)   | 0, 5, 18, 19, 21, 22, 23, 25, 26, 27, 32, 34, 35, 36, 39 | ESP32-CAM fixed pinout  |
| DHT22 (temp/humidity) | 2          |                                                    |
| Water pump relay      | 12         | Active HIGH                                        |
| SG90 rotary servo     | 13         | PWM signal (50Hz, 500–2500 µs pulse width)        |
| ADS1115 SCL          | 4          | Software I2C (camera LED repurposed)                |
| ADS1115 SDA          | 14         | Software I2C                                       |

> **GPIO 15 and 16 are free** — previously used for valve relays 2 and 3.

### Wiring Diagram

```mermaid
graph TB
    subgraph ESP32["🟡 ESP32-CAM (Main Controller)"]
        GPIO2["🔌 GPIO 2<br>DHT22 DATA"]
        GPIO12["🔌 GPIO 12<br>Pump Relay IN"]
        GPIO13["🔌 GPIO 13<br>Servo PWM"]
        GPIO4["🔌 GPIO 4<br>ADS1115 SCL"]
        GPIO14["🔌 GPIO 14<br>ADS1115 SDA"]
        5V["🔌 5V rail"]
        GND["🔌 GND"]
    end

    subgraph Required["✅ Required Components"]
        DHT22["🌡️ DHT22<br>Temp + Humidity<br><small>┬ VCC (1)<br>├ DATA (2)<br>├ NC (3)<br>└ GND (4)</small>"]
        PUMP_RELAY["⚡ Pump Relay Module<br>(Active HIGH)<br><small>┬ VCC (1)<br>├ IN (2) → GPIO12<br>├ GND (3)<br>└ NO/COM (pump)</small>"]
        SERVO["🔄 SG90 Servo<br>Rotary Selector<br><small>┬ VCC (1) → 5V<br>├ GND (2) → GND<br>└ PWM (3) → GPIO13</small>"]
        ADS1115["📊 ADS1115<br>4-Ch 16-bit ADC<br><small>┬ VDD (1) → 3.3V<br>├ GND (2) → GND<br>├ SCL (3) → GPIO4<br>├ SDA (4) → GPIO14<br>├ AIN0 (5) → SM1<br>├ AIN1 (6) → SM2<br>├ AIN2 (7) → SM3<br>└ AIN3 (8) → SM4</small>"]
    end

    subgraph SoilSensors["🌱 Soil Moisture Sensors (×4)"]
        SM1["💧 HW-390 #1<br>Habanero<br><small>┬ VCC → 3.3V<br>├ GND → GND<br>└ OUT → ADS1115 AIN0</small>"]
        SM2["💧 HW-390 #2<br>Naga Morich<br><small>┬ VCC → 3.3V<br>├ GND → GND<br>└ OUT → ADS1115 AIN1</small>"]
        SM3["💧 HW-390 #3<br>Carolina Reaper<br><small>┬ VCC → 3.3V<br>├ GND → GND<br>└ OUT → ADS1115 AIN2</small>"]
        SM4["💧 HW-390 #4<br>Rosmarino<br><small>┬ VCC → 3.3V<br>├ GND → GND<br>└ OUT → ADS1115 AIN3</small>"]
    end

    subgraph Optional["⚪ Optional Components"]
        AMS1117["🔌 AMS1117<br>5→3.3V Regulator<br><small>┬ VIN → 5V rail<br>├ GND → GND<br>└ VOUT → 3.3V</small>"]
        WATER_LEVEL["💧 Water Level<br>Float Switch<br><small>┬ VCC<br>├ GND<br>└ SIG → ESP GPIO? (TBD)</small>"]
        FLOW_METER["📏 YF-S401 Flow Meter<br><small>┬ VCC (red)<br>├ GND (black)<br>└ SIG (yellow) → ESP GPIO? (TBD)</small>"]
    end

    GPIO2 ==> DHT22
    GPIO12 ==> PUMP_RELAY
    GPIO13 ==> SERVO
    GPIO4 ==>|"SCL"| ADS1115
    GPIO14 ==>|"SDA"| ADS1115
    5V ==>|"5V"| PUMP_RELAY
    5V ==>|"5V"| SERVO
    5V ==>|"5V"| DHT22
    GND ==>|"GND"| DHT22
    GND ==>|"GND"| PUMP_RELAY
    GND ==>|"GND"| SERVO
    GND ==>|"GND"| ADS1115
    ADS1115 ==>|"AIN0"| SM1
    ADS1115 ==>|"AIN1"| SM2
    ADS1115 ==>|"AIN2"| SM3
    ADS1115 ==>|"AIN3"| SM4

    AMS1117 -.->|"optional<br>3.3V power"| ADS1115
    AMS1117 -.->|"optional<br>3.3V power"| SM1
    AMS1117 -.->|"optional<br>3.3V power"| SM2
    AMS1117 -.->|"optional<br>3.3V power"| SM3
    AMS1117 -.->|"optional<br>3.3V power"| SM4
    WATER_LEVEL -.->|"signal"| ESP32
    FLOW_METER -.->|"signal"| ESP32

    classDef esp32 fill:#FFF9C4,stroke:#F9A825
    classDef required fill:#E8F5E9,stroke:#2E7D32
    classDef sensor fill:#E3F2FD,stroke:#1565C0
    classDef optional fill:#F5F5F5,stroke:#9E9E9E,stroke-dasharray:5 5
    classDef gpio fill:#FCE4EC,stroke:#AD1457
    classDef pwr fill:#FFEBEE,stroke:#C62828
    classDef gnd fill:#ECEFF1,stroke:#607D8B

    class GPIO2,GPIO12,GPIO13,GPIO4,GPIO14,5V,GND esp32
    class DHT22,PUMP_RELAY,SERVO,ADS1115 required
    class SM1,SM2,SM3,SM4 sensor
    class AMS1117,WATER_LEVEL,FLOW_METER optional
```

**Legend:**
- `==>` = required power + signal connection
- `-.->` = optional connection (not yet implemented in firmware)
- Pin numbers shown in `<small>` as `┬ ├ └` tree (component top = pin 1)

### Rotary Selector — Plant Mapping

The SG90 servo rotates a 3D-printed water path selector (Instructables: *Water Path Selector*) to direct water from a single input to one of 4 output ports. Each output connects to a different plant's drip line.

The servo position (angle) selects the active output (based on 3D-printed Water Path Selector from Instructables):

| Plant            | Position | Angle (18° step) |
|------------------|----------|-------------------|
| Habanero        | 0        | 52°              |
| Naga Morich     | 1        | 70°              |
| Carolina Reaper | 2        | 88°              |
| Rosmarino       | 3        | 106°             |

The step angle (`ROTARY_DELTA_DEG = 18.0°`, start `ROTARY_START_DEG = 52.0°`) can be adjusted in `src/esp32/main.cpp` once the physical positioning is calibrated. After moving to a position, the servo holds that position indefinitely (no power draw after reaching target).

### Startup Calibration

On boot, the firmware runs a calibration sweep: it visits each position sequentially, waits 800 ms, reads back the actual pulse width, and verifies the servo reached the target within ±100 µs tolerance. If any position fails, `rotary_position` in `/status` reports `"uncalibrated"` and the system falls back to software-only position tracking. Adjust `ROTARY_DELTA_DEG` if the servo doesn't reach all positions accurately.

## ADS1115 — 4-Channel 16-bit Soil Moisture ADC

The ESP32-CAM has no free GPIOs for extra ADCs and its ADC2 conflicts with WiFi.
An external ADS1115 (I2C, 4-channel, 16-bit) provides clean isolated readings via software I2C on GPIO 14 (SDA) and GPIO 4 (SCL, camera LED repurposed).

#### Wiring

| ADS1115 | ESP32-CAM     | Sensor             |
|---------|---------------|--------------------|
| VDD     | 3.3V         |                    |
| GND     | GND           |                    |
| SCL     | GPIO 4        | Camera LED flash repurposed as I2C clock |
| SDA     | GPIO 14       |                    |
| AIN0    |               | HW-390 #1 (Habanero)       |
| AIN1    |               | HW-390 #2 (Naga Morich)    |
| AIN2    |               | HW-390 #3 (Carolina Reaper) |
| AIN3    |               | HW-390 #4 (Rosmarino)      |

GPIO 14 is used as digital I2C data (not analog), so the ADC2 WiFi conflict does not apply.
GPIO 4 (camera LED flash) is sacrificed because no free GPIOs remain on the ESP32-CAM.

#### Optional: AMS1117 for clean 3.3V power

For the lowest noise on ADC readings, power the ADS1115 and HW-390 sensors from an external AMS1117 5→3.3V regulator:

```
5V rail → AMS1117 VIN → 3.3V → ADS1115 VDD + HW-390 VCC
```

## API endpoints (Mongoose, port 80)

### `GET /status`

Returns current sensor readings, rotary selector position, and active plant:

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
    "rotary_position": "1",
    "water_low_alert": "off",
    "blocked_amount_ml": "0",
    "active_plant": "null"
}
```

`rotary_position` is `0`–`3` (calibrated) or `"uncalibrated"` (calibration failed).
`active_plant` contains the target name (e.g. `"NAGA_MORICH"`) when the pump is running, `"null"` when idle.

### `POST /command`

```json
{"action": "START", "target": "NAGA_MORICH"}
{"action": "STOP",  "target": "NAGA_MORICH"}
{"action": "DISPENSE_SPECIFIC_AMOUNT", "target": "HABANERO", "amount": 500}
{"action": "START", "target": "ROSMARINO", "force": true}
```

| Field  | Values                                              |
|--------|-----------------------------------------------------|
| `action`  | `START`, `STOP`, `DISPENSE_SPECIFIC_AMOUNT`  |
| `target`   | `NAGA_MORICH`, `ROSMARINO`, `HABANERO`, `CAROLINA_REAPER` |
| `amount`   | ml (only for `DISPENSE_SPECIFIC_AMOUNT`)      |
| `force`    | `true` to bypass water-low alert (optional, default `false`) |

`DISPENSE_SPECIFIC_AMOUNT` moves the servo to the selected plant's position, turns on the pump, waits `amount / FLOW_RATE_ML_PER_MIN * 60` seconds, then stops the pump (servo stays at last position).

`START` moves the servo and turns on the pump continuously. Use `STOP` to shut off.

### `GET /health`

Returns `{"status":"ok"}`.

## Targets (`Target` enum)

Defined in `src/model/command.h`:

```cpp
enum Target { NAGA_MORICH=0, ROSMARINO=1, HABANERO=2, CAROLINA_REAPER=3 };
```

## Water Level Alert

When `water_low_alert` is `true`, the ESP blocks `START` and `DISPENSE_SPECIFIC_AMOUNT` commands unless `force: true` is set. The `blocked_amount_ml` field in `/status` records how many ml were denied in the last blocked attempt.

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

## Unused / Spare Components

- **74HC4051 (×3)** — 8-channel analog muxes. Not needed; the ADS1115 provides 4 dedicated ADC channels.
- **AMS1117 (×4 remaining)** — 5→3.3V regulators. One can be used for clean analog power (see above); the rest are spares.
- **GPIO 15, 16** — free, previously used for valve relays 2 and 3.

WiFi credentials are hardcoded in `src/esp32/main.cpp`.
