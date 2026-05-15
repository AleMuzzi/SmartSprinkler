# SmartSprinkler — Mobile App

Flutter app for manual irrigation control and real-time sensor monitoring.

## Features

- **Sensor dashboard** — polls `GET /status` from the ESP every 2s and displays temperature, humidity, soil moisture, and pump state
- **Plant dropdown** — select which plant to irrigate
- **Start / Stop irrigation** — sends `POST /command` to the ESP with the selected plant and action
- **Bayesian routing toggle** — when ON, watering is routed through the BayesianSprinkler server which logs the event and then triggers the ESP; when OFF, the command goes directly to the ESP
- **Settings page** — configure both the ESP URL and the Bayesian server URL

## How routing works

```
Toggle ON  →  POST /api/plants/manual-water  →  Bayesian server reads sensors,
              logs snapshot (need_water=yes), then calls ESP's POST /command

Toggle OFF →  POST /command directly to ESP  →  no logging, no Bayesian involvement
```

The Bayesian server URL is configured independently from the ESP URL, so the Bayesian server can run on a different machine (e.g., a local server or Raspberry Pi).

## Model

### `Command`

```dart
Command(target: Target.PEPERONCINO, action: Action.START)
// → {"action": "START", "target": "PEPERONCINO", "amount": 0}
```

| Enum | Values |
|---|---|
| `Action` | `STOP`, `START`, `DISPENSE_SPECIFIC_AMOUNT` |
| `Target` | `PEPERONCINO`, `ROSMARINO` (add more to match firmware) |

### `Settings` (singleton)

- `apiUrl` — ESP base URL (default `http://192.168.1.10`)
- `bayesianUrl` — Bayesian server base URL (default `http://192.168.1.11:8080`)

## Run

```bash
flutter run
```

Requires Flutter SDK and the `http` + `fluttertoast` packages (see `pubspec.yaml`).
