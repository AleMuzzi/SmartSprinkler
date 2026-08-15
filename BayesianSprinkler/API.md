# Bayesian Sprinkler API Documentation

## Overview

The Bayesian Sprinkler server is a FastAPI application that:
- Queries a Bayesian network to compute plant watering probability
- Logs sensor data to a SQLite database
- Interfaces with an ESP32 controller and Open-Meteo weather API

## Base URL

```
http://<host>:8080
```

Interactive documentation available at:
- **Swagger UI**: `http://<host>:8080/docs`
- **ReDoc**: `http://<host>:8080/redoc`

---

## Endpoints

### `GET /api/plants/status`

Returns the current probability of need for all plants along with weather data and evidence nodes.

**Tags:** `Plants`

**Response** `200 OK`

```json
{
  "weather": {
    "temperature": 25.5,
    "humidity": 60.0,
    "cloud_cover": "clear",
    "rain_forecast": "no"
  },
  "plants": [
    {
      "plant_id": "habanero",
      "probability_of_need": 0.72,
      "evidence_nodes": [
        {"label": "Soil Moisture", "score": 100, "icon": "water_drop"},
        {"label": "Temperature", "score": 70, "icon": "thermostat"},
        {"label": "Humidity", "score": 55, "icon": "air"},
        {"label": "Cloud Cover", "score": 0, "icon": "cloud"},
        {"label": "Rain Forecast", "score": -10, "icon": "cloudy_snowing"}
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `weather.temperature` | `float \| null` | Current air temperature in °C |
| `weather.humidity` | `float \| null` | Current air humidity in % |
| `weather.cloud_cover` | `string` | `"clear"` \| `"cloudy"` |
| `weather.rain_forecast` | `string` | `"yes"` \| `"no"` |
| `plants[].plant_id` | `string` | Plant identifier (e.g. `"habanero"`) |
| `plants[].probability_of_need` | `float` | Probability from 0.0 to 1.0 |
| `plants[].evidence_nodes[].label` | `string` | Factor label |
| `plants[].evidence_nodes[].score` | `int` | Impact score (-100 to +100) |
| `plants[].evidence_nodes[].icon` | `string` | Icon identifier |

**Evidence Node Score Semantics**

| Icon | Label | +Score Meaning | -Score Meaning |
|------|-------|----------------|---------------|
| `water_drop` | Soil Moisture | Soil is dry, needs water | Soil is wet |
| `thermostat` | Temperature | High evaporation risk | Low temperature |
| `air` | Humidity | Low humidity = high evaporation | High humidity |
| `cloud` | Cloud Cover | Clear sky = more evaporation | Cloudy reduces evaporation |
| `cloudy_snowing` | Rain Forecast | No rain forecast | Rain expected soon |

---

### `POST /api/plants/manual-water`

Triggers manual watering for a specified plant. Logs a sensor snapshot to the database with `need_water=yes` for the target plant and `need_water=no` for all others.

**Tags:** `Plants`

**Request Body**

```json
{
  "plant_type": "habanero"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plant_type` | `string` | Yes | Plant identifier |

**Responses**

`200 OK`
```json
{
  "status": "ok",
  "plant": "habanero"
}
```

`422 Unprocessable Entity`
```json
{
  "detail": "Unknown plant: invalid_plant"
}
```

`503 Service Unavailable`
```json
{
  "detail": "Water level low — blocked. Use force=true to override."
}
```

---

### `GET /api/health`

Health check endpoint.

**Tags:** `System`

**Response** `200 OK`
```json
{
  "status": "ok"
}
```

---

## Internal Data Flow

### Sensor Discretization

Raw sensor values from the ESP32 are discretized before inference:

| Sensor | Raw Range | Discretized State |
|--------|----------|-------------------|
| Soil Moisture | ≤35 | `"dry"` |
| Soil Moisture | 36–65 | `"moist"` |
| Soil Moisture | >65 | `"wet"` |
| Temperature | ≤16°C | `"low"` |
| Temperature | 17–29°C | `"medium"` |
| Temperature | >29°C | `"high"` |
| Humidity | ≤45% | `"low"` |
| Humidity | 46–70% | `"medium"` |
| Humidity | >70% | `"high"` |

### Bayesian Network Structure

```
AirTemperature ──┐
AirHumidity   ───┼──→ EvaporationRisk ──→
CloudCover    ──┘                      │
                                     │   ┌──→ NeedWater
                                     │   │
SoilMoisture ─────────────────────────┤   │
                                     │   │
PlantType ────────────────────────────┴──→┘
                                     │
RainForecast ────────────────────────────→┘
```

### Evidence Computation

Evidence node scores are derived from discretized sensor states:

| Factor | State → Score |
|--------|---------------|
| Soil Moisture | `"dry"` → +100, `"moist"` → +30, `"wet"` → 0 |
| Temperature | `"high"` → +80, `"medium"` → +40, `"low"` → 0 |
| Humidity | `"low"` → +60, `"medium"` → +30, `"high"` → 0 |
| Cloud Cover | `"clear"` → +50, `"cloudy"` → 0 |
| Rain Forecast | `"no"` → +20, `"yes"` → -60 |

---

## Database Schema

**Table: `sensor_history`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key, autoincrement |
| `timestamp` | TEXT | ISO 8601 datetime |
| `plant_type` | TEXT | Plant identifier |
| `soil_moisture` | TEXT | `"dry"` \| `"moist"` \| `"wet"` |
| `air_temperature` | TEXT | `"low"` \| `"medium"` \| `"high"` |
| `air_humidity` | TEXT | `"low"` \| `"medium"` \| `"high"` |
| `cloud_cover` | TEXT | `"clear"` \| `"cloudy"` |
| `rain_forecast` | TEXT | `"yes"` \| `"no"` |
| `need_water` | TEXT | `"yes"` \| `"no"` |

---

## Plant Configuration

Each plant is defined in `config.yaml` under `plants`:

```yaml
plants:
  habanero:
    display_name: "Habanero"
    esp_target: "habanero_pump"
    threshold: 0.65
    base_need: 0.60
    watering_duration: 15
  naga_morich:
    display_name: "Naga Morich"
    esp_target: "naga_pump"
    threshold: 0.65
    base_need: 0.55
    watering_duration: 18
```

| Field | Type | Description |
|-------|------|-------------|
| `display_name` | `string` | Human-readable name |
| `esp_target` | `string` | ESP32 pump target identifier |
| `threshold` | `float` | Probability threshold to trigger watering (0.0–1.0) |
| `base_need` | `float` | Base prior probability of needing water (0.0–1.0) |
| `watering_duration` | `int` | Duration in seconds |

---

## Background Jobs

### Inference Cycle

Runs on the configured `esp.poll_interval` (default 1800s / 30 minutes). This is the only job that touches the ESP — no separate hourly poll:

1. Fetches ESP32 `/status`
2. Fetches weather data
3. Computes P(NeedWater=yes) for each plant and logs every snapshot (`need_water=yes/no`) to SQLite — plants outside the watering hour window are still logged
4. Triggers watering if probability > threshold and pump is not already running (respecting the hour window)
