import React from 'react'

function SensorCard({ label, value, unit, icon, color = 'blue' }) {
  const colorMap = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    orange: 'bg-orange-50 border-orange-200 text-orange-700',
    gray: 'bg-gray-50 border-gray-200 text-gray-700',
  }
  const iconBgMap = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    orange: 'bg-orange-100 text-orange-600',
    gray: 'bg-gray-100 text-gray-600',
  }
  return (
    <div className={`rounded-xl p-4 border ${colorMap[color]}`}>
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconBgMap[color]}`}>
          {icon}
        </div>
        <div>
          <p className="text-xs opacity-75 uppercase tracking-wide">{label}</p>
          <p className="text-xl font-bold">{value ?? '--'}<span className="text-sm ml-1 opacity-75">{unit}</span></p>
        </div>
      </div>
    </div>
  )
}

function PumpStatus({ isOn, plant }) {
  return (
    <div className={`rounded-xl p-4 border ${isOn ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'}`}>
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isOn ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-400'}`}>
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 3.5a1.5 1.5 0 013 0v4.586l2.707 2.707a1.5 1.5 0 01-1.414 2.5h-7.172a1.5 1.5 0 01-1.414-2.5L7 7.5V3.5a1.5 1.5 0 013 0z"/>
          </svg>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Water Pump</p>
          <p className={`text-lg font-bold ${isOn ? 'text-blue-600' : 'text-gray-400'}`}>
            {isOn ? `ON — ${plant || 'Unknown'}` : 'OFF'}
          </p>
        </div>
      </div>
    </div>
  )
}

export function TelemetryPanel({ espData }) {
  const parse = (v) => {
    if (v === null || v === undefined || v === 'nan') return null
    const n = parseFloat(v)
    return isNaN(n) ? null : n
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <SensorCard
        label="Air Temperature"
        value={parse(espData?.air_temperature)?.toFixed(1)}
        unit="°C"
        icon={
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m8-9H5m14 6h-4m-5-8a4 4 0 100-8 4 4 0 000 8z"/>
          </svg>
        }
        color="orange"
      />
      <SensorCard
        label="Air Humidity"
        value={parse(espData?.air_humidity)?.toFixed(1)}
        unit="%"
        icon={
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.9 2.999z"/>
          </svg>
        }
        color="blue"
      />
      <SensorCard
        label="Soil Moisture"
        value={parse(espData?.soil_moisture)?.toFixed(1)}
        unit="%"
        icon={
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v18m9-9l-9 9-9-9"/>
          </svg>
        }
        color="green"
      />
      <SensorCard
        label="Rotary Position"
        value={espData?.rotary_position ?? '--'}
        unit=""
        icon={
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        }
        color="gray"
      />
      <SensorCard
        label="Water Level Alert"
        value={espData?.water_low_alert === 'on' ? 'LOW' : 'OK'}
        unit=""
        icon={
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M5.07 19h13.86a2 2 0 001.73-3l-6.93-12a2 2 0 00-3.46 0L3.34 16a2 2 0 001.73 3z"/>
          </svg>
        }
        color={espData?.water_low_alert === 'on' ? 'red' : 'green'}
      />
      <PumpStatus
        isOn={espData?.water_pump === 'on'}
        plant={espData?.active_plant && espData.active_plant !== 'null' ? espData.active_plant.replace('_', ' ') : null}
      />
    </div>
  )
}

export function WeatherPanel({ weather }) {
  if (!weather) return null
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Weather Context</h3>
      <div className="flex gap-6 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-2xl">☁️</span>
          <div>
            <p className="text-xs text-gray-400">Cloud Cover</p>
            <p className="font-bold text-gray-700">{weather.cloud_cover ?? '--'}%</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{weather.rain_forecast === 'yes' ? '🌧️' : '🌤️'}</span>
          <div>
            <p className="text-xs text-gray-400">Rain Forecast</p>
            <p className="font-bold text-gray-700 capitalize">{weather.rain_forecast ?? '--'}</p>
          </div>
        </div>
        {weather.temperature !== undefined && (
          <div className="flex items-center gap-2">
            <span className="text-2xl">🌡️</span>
            <div>
              <p className="text-xs text-gray-400">Temperature</p>
              <p className="font-bold text-gray-700">{weather.temperature?.toFixed(1)}°C</p>
            </div>
          </div>
        )}
        {weather.humidity !== undefined && (
          <div className="flex items-center gap-2">
            <span className="text-2xl">💧</span>
            <div>
              <p className="text-xs text-gray-400">Humidity</p>
              <p className="font-bold text-gray-700">{weather.humidity?.toFixed(1)}%</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}