import React, { useState, useEffect, useMemo, useCallback } from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  Line,
  Area,
  Bar,
  BarChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { fetchCharts } from '../services/api.js'

const PLANT_COLORS = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#f59e0b']

const BUCKETS = [
  { value: '15m', label: '15 min' },
  { value: '30m', label: '30 min' },
  { value: '1h', label: '1 hour' },
  { value: '6h', label: '6 hours' },
  { value: '1d', label: '1 day' },
]

function formatAxisTs(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString(undefined, {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

function mergeContinuous(payload) {
  // Merge the per-series arrays into one point-per-timestamp grid so the
  // charts share a single x-axis. Missing values stay undefined (gaps).
  const byTs = new Map()
  const push = (timestamp, key, value) => {
    if (timestamp == null) return
    let point = byTs.get(timestamp)
    if (!point) {
      point = { timestamp }
      byTs.set(timestamp, point)
    }
    point[key] = value
  }
  for (const [plant, points] of Object.entries(payload.soil_moisture || {})) {
    for (const p of points) push(p.timestamp, `soil_${plant}`, p.value)
  }
  for (const p of payload.temperature || []) push(p.timestamp, 'temperature', p.value)
  for (const p of payload.humidity || []) push(p.timestamp, 'humidity', p.value)
  for (const p of payload.cistern || []) push(p.timestamp, 'cistern', p.value)
  return [...byTs.values()].sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1))
}

function mergeWaterings(payload) {
  // Group waterings by timestamp+plant so the bar chart has one datum per
  // (bucket, plant) with a ``w_<plant>`` key.
  const byTs = new Map()
  for (const w of payload.waterings || []) {
    const key = w.timestamp
    let point = byTs.get(key)
    if (!point) {
      point = { timestamp: key }
      byTs.set(key, point)
    }
    point[`w_${w.plant}`] = (point[`w_${w.plant}`] || 0) + w.dose_ml
  }
  return [...byTs.values()].sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1))
}

function EmptyNote() {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
      No data in this range. Raw per-plant telemetry is recorded by the hourly
      inference from now on; temperature/humidity and cistern also cover the
      historical log.
    </div>
  )
}

export function ChartsView() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [bucket, setBucket] = useState('1h')
  const [payload, setPayload] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hidden, setHidden] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchCharts({
        startDate: startDate || null,
        endDate: endDate || null,
        bucket,
      })
      setPayload(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, bucket])

  useEffect(() => {
    load()
  }, [load])

  const continuous = useMemo(() => (payload ? mergeContinuous(payload) : []), [payload])
  const waterings = useMemo(() => (payload ? mergeWaterings(payload) : []), [payload])

  const plants = payload?.plants || []
  const toggle = (key) => setHidden((h) => ({ ...h, [key]: !h[key] }))
  const isVisible = (key) => !hidden[key]

  const soilVisible = plants.some((p) => isVisible(`soil_${p}`))
  const ambientVisible = isVisible('temperature') || isVisible('humidity')
  const cisternVisible = isVisible('cistern')
  const wateringVisible = plants.some((p) => isVisible(`w_${p}`))

  const plantName = (id) => {
    const known = { habanero: 'Habanero', naga_morich: 'Naga Morich', carolina_reaper: 'Carolina Reaper', rosmarino: 'Rosmarino' }
    return known[id] || id
  }

  return (
    <div className="space-y-5">
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
          <h3 className="text-base font-semibold text-gray-700 flex items-center gap-2">
            <span>📈</span> Statistics
          </h3>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="flex items-center gap-1.5 text-xs text-gray-500">
              From
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg bg-white"
              />
            </label>
            <label className="flex items-center gap-1.5 text-xs text-gray-500">
              To
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg bg-white"
              />
            </label>
            <select
              value={bucket}
              onChange={(e) => setBucket(e.target.value)}
              className="px-2 py-1.5 text-sm border border-gray-300 rounded-lg bg-white"
              title="Timeslot size (aggregation)"
            >
              {BUCKETS.map((b) => (
                <option key={b.value} value={b.value}>{b.label}</option>
              ))}
            </select>
            <button
              onClick={() => { setStartDate(''); setEndDate(''); setBucket('1h'); setHidden({}) }}
              className="text-xs px-3 py-2 rounded bg-gray-100 hover:bg-gray-200 text-gray-600"
              title="Clear all filters"
            >
              ✕ Clear
            </button>
          </div>
        </div>

        {error && <div className="text-red-600 text-sm mb-3">⚠️ {error}</div>}

        <div className="space-y-6">
          {/* Soil moisture: header with plant toggles always visible, chart only when at least one plant enabled. */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-gray-600">Soil moisture (%)</h4>
            <div className="flex flex-wrap items-center gap-3">
              {plants.map((p, i) => (
                <label key={p} className="flex items-center gap-1.5 text-xs cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isVisible(`soil_${p}`)}
                    onChange={() => toggle(`soil_${p}`)}
                    className="accent-blue-600"
                  />
                  <span style={{ color: PLANT_COLORS[i % PLANT_COLORS.length] }} className="font-medium">
                    {plantName(p)}
                  </span>
                </label>
              ))}
            </div>
          </div>
          {soilVisible && (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={continuous}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="timestamp" tickFormatter={formatAxisTs} tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip labelFormatter={formatAxisTs} />
                <Legend />
                {plants.map((p, i) => isVisible(`soil_${p}`) && (
                  <Line
                    key={p}
                    type="monotone"
                    dataKey={`soil_${p}`}
                    name={plantName(p)}
                    stroke={PLANT_COLORS[i % PLANT_COLORS.length]}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}

          {/* Environment (temperature + humidity): toggles always visible. */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-gray-600">Environment</h4>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs cursor-pointer select-none">
                <input type="checkbox" checked={isVisible('temperature')} onChange={() => toggle('temperature')} className="accent-red-600" />
                <span className="font-medium text-red-600">Temperature</span>
              </label>
              <label className="flex items-center gap-1.5 text-xs cursor-pointer select-none">
                <input type="checkbox" checked={isVisible('humidity')} onChange={() => toggle('humidity')} className="accent-cyan-600" />
                <span className="font-medium text-cyan-600">Air humidity</span>
              </label>
            </div>
          </div>
          {ambientVisible && (
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={continuous}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="timestamp" tickFormatter={formatAxisTs} tick={{ fontSize: 11 }} />
                <YAxis yAxisId="temp" tick={{ fontSize: 11 }} unit="°C" />
                <YAxis yAxisId="hum" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip labelFormatter={formatAxisTs} />
                <Legend />
                {isVisible('temperature') && (
                  <Line
                    yAxisId="temp"
                    type="monotone"
                    dataKey="temperature"
                    name="Temperature"
                    stroke="#dc2626"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                )}
                {isVisible('humidity') && (
                  <Line
                    yAxisId="hum"
                    type="monotone"
                    dataKey="humidity"
                    name="Air humidity"
                    stroke="#0891b2"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          )}

          {/* Cistern: toggle always visible. */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-gray-600">Cistern level (mL)</h4>
            <label className="flex items-center gap-1.5 text-xs cursor-pointer select-none">
              <input type="checkbox" checked={isVisible('cistern')} onChange={() => toggle('cistern')} className="accent-indigo-600" />
              <span className="font-medium text-indigo-600">Show cistern</span>
            </label>
          </div>
          {cisternVisible && (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={continuous}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="timestamp" tickFormatter={formatAxisTs} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip labelFormatter={formatAxisTs} />
                {isVisible('cistern') && (
                  <Area
                    type="stepAfter"
                    dataKey="cistern"
                    name="Cistern"
                    stroke="#4f46e5"
                    fill="#6366f1"
                    fillOpacity={0.15}
                    strokeWidth={2}
                    connectNulls={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          )}

          {/* Waterings: per-plant toggles always visible. */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-gray-600">Waterings (mL dispensed)</h4>
            <div className="flex flex-wrap items-center gap-3">
              {plants.map((p, i) => (
                <label key={`w_${p}`} className="flex items-center gap-1.5 text-xs cursor-pointer select-none">
                  <input type="checkbox" checked={isVisible(`w_${p}`)} onChange={() => toggle(`w_${p}`)} className="accent-green-600" />
                  <span style={{ color: PLANT_COLORS[i % PLANT_COLORS.length] }} className="font-medium">
                    {plantName(p)}
                  </span>
                </label>
              ))}
            </div>
          </div>
          {wateringVisible && (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={waterings}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="timestamp" tickFormatter={formatAxisTs} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip labelFormatter={formatAxisTs} />
                <Legend />
                {plants.map((p, i) => isVisible(`w_${p}`) && (
                  <Bar
                    key={`w_${p}`}
                    dataKey={`w_${p}`}
                    name={plantName(p)}
                    stackId="a"
                    fill={PLANT_COLORS[i % PLANT_COLORS.length]}
                    radius={[0, 0, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          )}

          {!loading && continuous.length === 0 && waterings.length === 0 && <EmptyNote />}
          {loading && (
            <div className="flex justify-center py-8">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full spinner" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
