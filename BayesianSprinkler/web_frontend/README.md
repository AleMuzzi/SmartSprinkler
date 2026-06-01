# SmartSprinkler — Web Frontend

React-based web dashboard for monitoring and controlling the SmartSprinkler irrigation system. Runs in any modern browser with no native app installation required.

## Quick start

```bash
npm install
npm run dev       # http://localhost:3000
npm run build     # production build → dist/
```

Or with Docker:

```bash
docker compose up web-frontend
# → http://localhost:3000
```

## Features

### Dashboard tab
- **Telemetry**: Live ESP32 sensor readings (air temperature, humidity, soil moisture, pump status, rotary position, water level alert) auto-polled every 2s
- **Weather context**: Cloud cover % and rain forecast from Open-Meteo (via Bayesian server)
- **Bayesian insights**: Per-plant `probability_of_need` (0–1 scale) displayed as color-coded progress bars

### Control tab
- **Plant selector**: 4 plant cards (Habanero, Naga Morich, Carolina Reaper, Rosmarino)
- **Routing mode toggle**:
  - **Direct ESP**: sends `POST /command` to ESP32 directly
  - **Via Bayesian**: sends `POST /api/plants/manual-water` to log event + water
- **Amount presets**: 100ml / 250ml / 500ml / 1000ml or continuous watering (for Direct ESP mode)
- **Start / Stop** buttons with loading spinners to prevent double-triggers

### Settings tab
- **ESP32 URL**: e.g. `http://192.168.1.50:80`
- **Bayesian Server URL**: e.g. `http://192.168.1.7:8080`
- **Polling interval**: in ms (default 2000ms)
- All settings persisted to browser `localStorage`

## Tech stack

| Layer | Choice |
|---|---|
| Framework | React 18 + Vite 6 |
| Styling | Tailwind CSS 3 |
| HTTP | Native Fetch API with 5s timeout |
| State | React hooks (`useState`, `useEffect`, `useCallback`) |
| Persistence | Browser `localStorage` |
| Container | nginx:alpine (multi-stage build) |

## CORS

The Bayesian server (`FastAPI`) has `CORSMiddleware(allow_origins=["*"])` enabled so the browser can call it directly. The ESP32 Mongoose server also permits cross-origin simple requests by default.

## API mapping

| Action | Endpoint | Method | Payload |
|---|---|---|---|
| Poll ESP status | `{espUrl}/status` | GET | — |
| ESP health check | `{espUrl}/health` | GET | — |
| Send ESP command | `{espUrl}/command` | POST | `{"action": "START\|STOP\|DISPENSE_SPECIFIC_AMOUNT", "target": "PLANT", "amount"?: ml}` |
| Poll plant probabilities | `{bayesianUrl}/api/plants/status` | GET | — |
| Poll weather | `{bayesianUrl}/api/weather/status` | GET | — |
| Bayesian health | `{bayesianUrl}/api/health` | GET | — |
| Log manual water event | `{bayesianUrl}/api/plants/manual-water` | POST | `{"plant_type": "habanero\|..."}` |