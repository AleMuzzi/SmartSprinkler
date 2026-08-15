# SmartSprinkler — Mobile App

Flutter app for manual irrigation control and real-time sensor monitoring.

## Features

- **Dashboard tab** — polls the Bayesian server's `/api/dashboard` (the ESP's latest captured snapshot) and displays temperature, humidity, soil moisture, pump state, and a **cistern level widget**
- **Camera tab** — live view of the ESP32-CAM stream
- **Logs tab** — audit log viewer with error banner, "show errors" filter, and expandable detail rows (tracebacks)
- **System tab** — manual control panel: plant selector, Direct ESP / Via Bayesian routing, Start/Stop, dispense amount; ESP & server status/connectivity via the network monitor
- **Plant dropdown** — select which plant to irrigate (maps to servo position)
- **Start / Stop irrigation** — sends `POST /command` to the ESP with the selected plant and action
- **Bayesian routing toggle** — when ON, watering is routed through the BayesianSprinkler server which logs the event and then triggers the ESP; when OFF, the command goes directly to the ESP
- **Water-level notifications** — local notifications when the tank float switch triggers `water_low_alert` (requires notification permission)
- **Settings** — configure both the ESP URL and the Bayesian server URL

## How routing works

```
Toggle ON  →  POST /api/plants/manual-water  →  Bayesian server reads sensors,
              logs snapshot (need_water=yes), then calls ESP's POST /command

Toggle OFF →  POST /command directly to ESP  →  no logging, no Bayesian involvement
```

The Bayesian server URL is configured independently from the ESP URL, so the Bayesian server can run on a different machine (e.g., a local server or Raspberry Pi). The app polls the server's `/api/dashboard` rather than the ESP directly, so it keeps working through network paths where the ESP is only reachable by the server.

## Rotary Selector — Plant Mapping

An SG90 servo drives a 3D-printed water path selector (Instructables: *Water Path Selector*) to direct water from a single pump output to one of 4 plant drip lines. Each plant maps to a servo position (1–4):

| Plant            | Position | Angle (start 5°, step 19°) |
|------------------|----------|----------------------------|
| Rosmarino       | 1        | 24°                        |
| Carolina Reaper | 2        | 43°                        |
| Naga Morich     | 3        | 62°                        |
| Habanero        | 4        | 81°                        |

On ESP startup, the servo runs a non-blocking calibration sweep to verify all positions are reachable. If any position fails, `/status` reports `rotary_position: "uncalibrated"`.

## Model

### `Command`

```dart
Command(target: Target.NAGA_MORICH, action: Action.START)
// → {"action": "START", "target": "NAGA_MORICH", "amount": 0}
```

| Enum | Values |
|---|---|
| `Action` | `STOP`, `START`, `DISPENSE_SPECIFIC_AMOUNT` |
| `Target` | `NAGA_MORICH`, `ROSMARINO`, `HABANERO`, `CAROLINA_REAPER` |

### `Settings` (singleton)

Configured with **internal (LAN)** and **external** URL pairs. When the phone is on the home Wi-Fi (SSID match via `NetworkMonitor`) the app uses the internal URLs; otherwise it falls back to the external ones:

- `internalEspUrl` — LAN ESP base URL (default `http://192.168.1.10`)
- `internalBayesianUrl` — LAN Bayesian server base URL (default `http://192.168.1.7:8080`)
- `externalEspUrl` — ESP URL when away from home (default `http://my.home.server`)
- `externalBayesianUrl` — Bayesian server URL when away from home (default `http://my.home.server:8080`)
- `homeWifiSsid` — SSID that triggers the switch to internal URLs

## Run

```bash
flutter run
```

Requires Flutter SDK and the `http`, `shared_preferences`, `network_info_plus`, `connectivity_plus`, `flutter_local_notifications`, and `fluttertoast` packages (see `pubspec.yaml`).
