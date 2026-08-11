import React, { useEffect, useMemo, useRef, useState } from 'react'

const BAYESIAN_API = (import.meta.env.VITE_BAYESIAN_API || 'http://localhost:8080').replace(/\/$/, '')

// ── Plant soil card ──────────────────────────────────────────────────────


function PlantCard({ plant, soil, justWatered, doseMl, flowRateMlPerMin }) {
  const pct = Math.max(0, Math.min(100, soil))
  const colour =
    pct < 35 ? 'from-red-400 to-red-600'
    : pct < 65 ? 'from-yellow-300 to-yellow-500'
    : 'from-emerald-400 to-emerald-600'
  const doseSeconds = flowRateMlPerMin && doseMl
    ? (doseMl * 60 / flowRateMlPerMin).toFixed(1)
    : null

  const label =
    pct < 35 ? 'dry' : pct < 65 ? 'moist' : 'wet'

  return (
    <div
      className={`relative bg-white rounded-2xl shadow-sm border p-4 transition-all ${
        justWatered ? 'ring-2 ring-blue-400 scale-[1.02]' : 'border-gray-200'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-800 capitalize">{plant}</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
          pct < 35 ? 'bg-red-100 text-red-700'
          : pct < 65 ? 'bg-yellow-100 text-yellow-700'
          : 'bg-emerald-100 text-emerald-700'
        }`}>
          {label}
        </span>
      </div>

      <div className="h-32 bg-gray-100 rounded-lg overflow-hidden relative">
        <div
          className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t ${colour} transition-all duration-500 ease-out`}
          style={{ height: `${pct}%` }}
        />
        <div className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-gray-700 mix-blend-overlay">
          {pct.toFixed(0)}%
        </div>
      </div>

      <div className="mt-2 flex justify-between text-xs text-gray-500">
        <span>0%</span>
        <span>soil moisture</span>
        <span>100%</span>
      </div>

      {justWatered && (
        <div className="absolute top-2 right-2 bg-blue-500 text-white text-xs px-2 py-1 rounded-full animate-pulse">
          💧 {doseMl !== undefined
            ? `${doseMl.toFixed(0)}mL${doseSeconds ? ` · ${doseSeconds}s` : ''}`
            : 'watering'}
        </div>
      )}
    </div>
  )
}


// ── Weather strip ────────────────────────────────────────────────────────


function WeatherStrip({ temperature, humidity, rainEvent }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
        <p className="text-xs uppercase text-orange-600 tracking-wide">Temperature</p>
        <p className="text-2xl font-bold text-orange-700">{temperature?.toFixed(1) ?? '--'}°C</p>
      </div>
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p className="text-xs uppercase text-blue-600 tracking-wide">Humidity</p>
        <p className="text-2xl font-bold text-blue-700">{humidity?.toFixed(0) ?? '--'}%</p>
      </div>
      <div className={`rounded-xl p-4 border ${
        rainEvent
          ? 'bg-indigo-50 border-indigo-200'
          : 'bg-gray-50 border-gray-200'
      }`}>
        <p className="text-xs uppercase tracking-wide text-gray-600">Sky</p>
        <p className="text-2xl">{rainEvent ? '🌧️ Rain' : '☀️ Clear'}</p>
      </div>
    </div>
  )
}


// ── Controls ─────────────────────────────────────────────────────────────


function ControlBar({
  running, paused, hour, speed, onPlayPause, onReset, onStep, onSpeed, onStop,
  configs, currentConfig, onConfigChange, onStart,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={currentConfig || ''}
          onChange={(e) => onConfigChange(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm bg-white"
        >
          <option value="" disabled>Select scenario…</option>
          {configs.map((c) => (
            <option key={c.name} value={c.name}>{c.name}</option>
          ))}
        </select>
        <button
          onClick={onStart}
          disabled={!currentConfig}
          className="px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm font-medium hover:bg-emerald-600 disabled:bg-gray-300"
        >
          ▶ Load &amp; Start
        </button>
        <div className="w-px h-6 bg-gray-300 mx-1" />
        <button
          onClick={onPlayPause}
          disabled={hour === null}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:bg-gray-300"
        >
          {paused ? '▶ Resume' : running ? '⏸ Pause' : '▶ Play'}
        </button>
        <button
          onClick={onStep}
          disabled={hour === null}
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg text-sm font-medium hover:bg-gray-300 disabled:opacity-50"
          title="Advance one simulated hour"
        >
          ⏭ Step
        </button>
        <button
          onClick={onReset}
          disabled={hour === null}
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg text-sm font-medium hover:bg-gray-300 disabled:opacity-50"
        >
          ⟲ Reset
        </button>
        <button
          onClick={onStop}
          disabled={hour === null}
          className="px-4 py-2 bg-red-100 text-red-700 rounded-lg text-sm font-medium hover:bg-red-200 disabled:opacity-50"
        >
          ⏹ Stop
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-gray-600">Speed:</label>
        <input
          type="range"
          min="1"
          max="600"
          step="1"
          value={speed}
          onChange={(e) => onSpeed(Number(e.target.value))}
          className="flex-1 max-w-xs"
        />
        <span className="text-sm font-medium text-gray-700 w-32">
          {speed} min / sec
        </span>
        <span className="text-xs text-gray-500">
          ({speed >= 60 ? `${(speed / 60).toFixed(1)} h/s` : `${(60 / speed).toFixed(1)} s/h`})
        </span>
        {hour !== null && (
          <span className="ml-auto text-sm text-gray-500">
            Sim hour <span className="font-mono font-semibold">{hour}</span>
            {' · '}
            <span className="font-mono">{(hour % 24).toString().padStart(2, '0')}:00</span>
          </span>
        )}
      </div>
    </div>
  )
}


// ── Weather knobs ────────────────────────────────────────────────────────


function WeatherKnobs({
  temperatureOffset, baseLossOverride, rainProbOverride,
  onTempOffset, onBaseLoss, onRainProb, onTriggerRain,
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
        Weather overrides
      </h3>

      <div>
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Temperature offset</span>
          <span className="font-mono">{(temperatureOffset ?? 0).toFixed(1)}°C</span>
        </div>
        <input
          type="range" min="-15" max="15" step="0.5"
          value={temperatureOffset ?? 0}
          onChange={(e) => onTempOffset(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div>
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Evaporation base</span>
          <span className="font-mono">{baseLossOverride?.toFixed(2) ?? 'config'}%/h</span>
        </div>
        <input
          type="range" min="0" max="10" step="0.1"
          value={baseLossOverride ?? -1}
          onChange={(e) => onBaseLoss(Number(e.target.value))}
          className="w-full"
        />
        {baseLossOverride !== null && baseLossOverride !== undefined && (
          <button
            onClick={() => onBaseLoss(null)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            ↺ reset to config
          </button>
        )}
      </div>

      <div>
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Rain probability</span>
          <span className="font-mono">
            {rainProbOverride !== null && rainProbOverride !== undefined
              ? `${(rainProbOverride * 100).toFixed(0)}%`
              : 'config'}
          </span>
        </div>
        <input
          type="range" min="0" max="1" step="0.05"
          value={rainProbOverride ?? -0.01}
          onChange={(e) => onRainProb(Number(e.target.value))}
          className="w-full"
        />
        {(rainProbOverride !== null && rainProbOverride !== undefined) && (
          <button
            onClick={() => onRainProb(null)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            ↺ reset to config
          </button>
        )}
      </div>

      <button
        onClick={onTriggerRain}
        className="w-full px-3 py-2 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-medium hover:bg-indigo-200"
      >
        🌧️ Trigger rain on next step
      </button>
    </div>
  )
}


// ── Event log ────────────────────────────────────────────────────────────


function EventLog({ events, plantIds }) {
  const ref = useRef(null)
  useEffect(() => {
    // Newest at top: pin scroll to the top so the user always sees the
    // most recent event without having to scroll down.
    if (ref.current) ref.current.scrollTop = 0
  }, [events.length])

  // Stable ordering for plant columns (use plantIds prop when present).
  const columns = plantIds && plantIds.length > 0
    ? plantIds
    : Array.from(new Set(events.flatMap((e) => Object.keys(e.soil_by_plant || {}))))

  // Render newest first.
  const ordered = [...events].reverse()

  return (
    <div className="bg-gray-900 text-gray-100 rounded-2xl p-4 font-mono text-xs">
      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <span className="text-gray-400 uppercase tracking-wide text-sm">Event log</span>
        <span className="text-gray-500">{events.length} events · {columns.length} plants</span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-gray-500 mb-2 uppercase tracking-wide">
        <span><span className="inline-block w-2 h-2 bg-emerald-400/70 mr-1 align-middle" />watered</span>
        <span><span className="inline-block w-2 h-2 bg-orange-500/60 mr-1 align-middle" />partial block</span>
        <span><span className="inline-block w-2 h-2 bg-yellow-500/70 mr-1 align-middle" />midday (11-17)</span>
        <span><span className="inline-block w-2 h-2 bg-gray-700 mr-1 align-middle" />idle</span>
      </div>
      <div ref={ref} className="h-[32rem] overflow-y-auto space-y-2 pr-1">
        {events.length === 0 && (
          <p className="text-gray-500">no events yet — load a scenario to begin…</p>
        )}
        {ordered.map((e, i) => {
          const hour = e.hour_of_day ?? (e.hour % 24)
          const isMidday = hour >= 11 && hour < 17
          const triggered = e.triggered || {}
          const blocked = e.hour_blocked || []
          const soil = e.soil_by_plant || {}
          const isNewest = i === 0
          return (
            <div
              key={`${e.hour}-${i}`}
              className={`relative border-l-2 pl-3 py-1 ${
                isMidday ? 'border-yellow-500/70 bg-yellow-500/5'
                : blocked.length > 0 ? 'border-orange-500/60 bg-orange-500/5'
                : Object.keys(triggered).length > 0 ? 'border-emerald-400/70 bg-emerald-400/5'
                : 'border-gray-700'
              }`}
            >
              {/* Header line */}
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="text-gray-500 w-16">
                  h{String(e.hour).padStart(3, ' ')}
                </span>
                <span className={`w-14 ${isMidday ? 'text-yellow-300 font-bold' : 'text-gray-300'}`}>
                  {String(hour).padStart(2, '0')}:00
                </span>
                <span className="text-orange-300">
                  {(e.temperature ?? 0).toFixed(1)}°C
                </span>
                <span className="text-blue-300">
                  {(e.humidity ?? 0).toFixed(0)}%RH
                </span>
                {e.rain_event && (
                  <span className="text-indigo-300">🌧 rain</span>
                )}
                {Object.keys(triggered).length > 0 && (
                  <span className="text-emerald-300">
                    💧 {Object.keys(triggered).length} watered
                  </span>
                )}
                {blocked.length > 0 && (
                  <span className="text-yellow-300">
                    🚫 {blocked.length} blocked-by-hour
                  </span>
                )}
                {isNewest && (
                  <span className="ml-auto text-[10px] uppercase tracking-wider text-cyan-300 border border-cyan-500/40 rounded px-1.5 py-0.5">
                    new
                  </span>
                )}
              </div>

              {/* Plant row: soil% + dose per plant */}
              <div className="mt-1 ml-16 flex flex-wrap gap-x-4 gap-y-1">
                {columns.map((pid) => {
                  const soilPct = soil[pid]
                  const doseMl = triggered[pid]
                  const doseS = e.dose_seconds_by_plant?.[pid]
                  const isBlocked = blocked.includes(pid)
                  let cls = 'text-gray-400'
                  if (doseMl !== undefined) cls = 'text-emerald-300'
                  else if (isBlocked) cls = 'text-yellow-300 line-through'
                  else if (soilPct !== undefined) cls = 'text-gray-300'
                  return (
                    <span key={pid} className={cls}>
                      <span className="text-gray-500">{pid}:</span>{' '}
                      {soilPct !== undefined ? (
                        <span>{soilPct.toFixed(0)}%</span>
                      ) : '—'}
                      {doseMl !== undefined && (
                        <span className="text-emerald-400">
                          {' '}+{doseMl.toFixed(0)}mL
                          {doseS !== undefined && (
                            <span className="text-cyan-300/80"> ({doseS.toFixed(1)}s)</span>
                          )}
                        </span>
                      )}
                      {isBlocked && doseMl === undefined && (
                        <span className="text-yellow-400/70"> ⏸</span>
                      )}
                    </span>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}


// ── Hook ─────────────────────────────────────────────────────────────────


function useSimulation(baseUrl) {
  const [configs, setConfigs] = useState([])
  const [currentConfig, setCurrentConfig] = useState('')
  const [state, setState] = useState({
    loaded: false, hour: null, running: false, paused: false,
    plants: [], temperature: null, humidity: null,
    water_low_alert: 'off', watering_count: 0,
  })
  const [overrides, setOverrides] = useState({
    temperatureOffset: 0,
    baseLossOverride: null,
    rainProbOverride: null,
  })
  const [speed, setSpeed] = useState(60)
  const [recentWatered, setRecentWatered] = useState({})
  const [events, setEvents] = useState([])

  // Load configs list on mount.
  useEffect(() => {
    fetch(`${baseUrl}/api/simulation/configs`)
      .then((r) => r.json())
      .then(setConfigs)
      .catch(() => setConfigs([]))
  }, [baseUrl])

  // Pull snapshot on demand (initial state).
  const refreshState = async () => {
    const r = await fetch(`${baseUrl}/api/simulation/state`)
    if (r.ok) setState(await r.json())
  }

  // SSE stream.
  useEffect(() => {
    const es = new EventSource(`${baseUrl}/api/simulation/events/stream`)
    es.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data)
        if (payload.type === 'hello') return
        if (payload.type !== 'event') return
        const ev = payload
        // Update snapshot from event.
        setState((s) => ({
          ...s,
          loaded: true,
          hour: ev.hour,
          temperature: ev.temperature,
          humidity: ev.humidity,
          plants: Object.entries(ev.soil_by_plant || {}).map(([id, soil]) => ({ id, soil })),
          watering_count: s.watering_count + Object.keys(ev.triggered || {}).length,
        }))
        // Highlight watered plants for 1.5 s.
        const watered = Object.keys(ev.triggered || {})
        if (watered.length > 0) {
          const doses = ev.triggered
          setRecentWatered((prev) => {
            const next = { ...prev }
            watered.forEach((p) => { next[p] = doses[p] })
            return next
          })
          setTimeout(() => {
            setRecentWatered((prev) => {
              const next = { ...prev }
              watered.forEach((p) => { delete next[p] })
              return next
            })
          }, 1500)
        }
        // Track last 200 events for the log.
        setEvents((prev) => {
          const next = [...prev, ev]
          return next.length > 200 ? next.slice(-200) : next
        })
      } catch (e) {
        // ignore malformed
      }
    }
    es.onerror = () => {
      // Server may have restarted; EventSource will retry automatically.
    }
    return () => es.close()
  }, [baseUrl])

  // ── Actions ─────────────────────────────────────────────────────

  const start = async (configName) => {
    const r = await fetch(`${baseUrl}/api/simulation/start`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config: configName }),
    })
    if (!r.ok) throw new Error(`start failed: ${r.status}`)
    setCurrentConfig(configName)
    setEvents([])
    const data = await r.json()
    setState((s) => ({ ...s, ...data }))
  }

  const pause = async () => {
    const r = await fetch(`${baseUrl}/api/simulation/pause`, { method: 'POST' })
    if (r.ok) setState(await r.json())
  }
  const resume = async () => {
    const r = await fetch(`${baseUrl}/api/simulation/resume`, { method: 'POST' })
    if (r.ok) setState(await r.json())
  }
  const playPause = () => (state.paused ? resume() : pause())

  const reset = async () => {
    const r = await fetch(`${baseUrl}/api/simulation/reset`, { method: 'POST' })
    if (r.ok) {
      setEvents([])
      setState(await r.json())
    }
  }

  const stop = async () => {
    await fetch(`${baseUrl}/api/simulation/stop`, { method: 'POST' })
    setState({
      loaded: false, hour: null, running: false, paused: false,
      plants: [], temperature: null, humidity: null,
      water_low_alert: 'off', watering_count: 0,
    })
    setEvents([])
  }

  const step = async () => {
    const r = await fetch(`${baseUrl}/api/simulation/step`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count: 1 }),
    })
    if (r.ok) {
      const data = await r.json()
      // Backend already publishes events via SSE; just keep state fresh.
      if (data.state) setState((s) => ({ ...s, ...data.state }))
    }
  }

  const changeSpeed = async (mps) => {
    setSpeed(mps)
    await fetch(`${baseUrl}/api/simulation/speed`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ minutes_per_second: mps }),
    })
  }

  const applyOverride = async (overrides) => {
    const r = await fetch(`${baseUrl}/api/simulation/override`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(overrides),
    })
    if (r.ok) {
      const data = await r.json()
      setState((s) => ({ ...s, ...data }))
    }
  }

  const setTempOffset = (v) => {
    setOverrides((o) => ({ ...o, temperatureOffset: v }))
    applyOverride({ temperature_offset: v })
  }
  const setBaseLoss = (v) => {
    setOverrides((o) => ({ ...o, baseLossOverride: v < 0 ? null : v }))
    applyOverride({ base_loss_override: v < 0 ? null : v })
  }
  const setRainProb = (v) => {
    setOverrides((o) => ({ ...o, rainProbOverride: v < 0 ? null : v }))
    applyOverride({ rain_probability_override: v < 0 ? null : v })
  }
  const triggerRain = async () => {
    await fetch(`${baseUrl}/api/simulation/trigger-rain`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount_percent: null }),
    })
  }

  return {
    configs, currentConfig, state, speed, overrides, events, recentWatered,
    start, playPause, reset, stop, step, changeSpeed,
    setTempOffset, setBaseLoss, setRainProb, triggerRain,
    refreshState,
  }
}


// ── Main view ────────────────────────────────────────────────────────────


export function SimulationView() {
  const sim = useSimulation(BAYESIAN_API)

  const soilById = useMemo(() => {
    const m = {}
    sim.state.plants.forEach((p) => { m[p.id] = p.soil })
    return m
  }, [sim.state.plants])

  return (
    <div className="space-y-4">
      <ControlBar
        running={sim.state.running}
        paused={sim.state.paused}
        hour={sim.state.hour}
        speed={sim.speed}
        configs={sim.configs}
        currentConfig={sim.currentConfig}
        onConfigChange={sim.start}
        onStart={() => sim.start(sim.currentConfig || (sim.configs[0]?.name))}
        onPlayPause={sim.playPause}
        onReset={sim.reset}
        onStep={sim.step}
        onSpeed={sim.changeSpeed}
        onStop={sim.stop}
      />

      <WeatherStrip
        temperature={sim.state.temperature}
        humidity={sim.state.humidity}
        rainEvent={sim.events.length > 0 && sim.events[sim.events.length - 1].rain_event}
      />

      {!sim.state.loaded && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-center text-yellow-700">
          ⚠️ No simulation loaded. Pick a scenario above and hit <strong>Load &amp; Start</strong>.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {sim.state.plants.map((p) => (
          <PlantCard
            key={p.id}
            plant={p.id}
            soil={p.soil}
            justWatered={Boolean(sim.recentWatered[p.id])}
            doseMl={sim.recentWatered[p.id]}
            flowRateMlPerMin={sim.events[sim.events.length - 1]?.flow_rate_ml_per_min ?? null}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WeatherKnobs
          temperatureOffset={sim.overrides.temperatureOffset}
          baseLossOverride={sim.overrides.baseLossOverride}
          rainProbOverride={sim.overrides.rainProbOverride}
          onTempOffset={sim.setTempOffset}
          onBaseLoss={sim.setBaseLoss}
          onRainProb={sim.setRainProb}
          onTriggerRain={sim.triggerRain}
        />
        <EventLog events={sim.events} plantIds={sim.state.plants.map((p) => p.id)} />
      </div>

      {sim.state.loaded && (
        <div className="text-xs text-gray-500 text-center">
          Watering events so far: <span className="font-mono font-semibold">{sim.state.watering_count}</span>
        </div>
      )}
    </div>
  )
}