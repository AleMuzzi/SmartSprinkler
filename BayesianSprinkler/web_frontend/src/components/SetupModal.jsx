import React, { useState } from 'react'
import { saveSettings } from '../services/settings.js'
import { LOCATION_OPTIONS, WATERING_OPTIONS, THEME_OPTIONS } from './setupOptions.js'

function OptionGroup({ title, options, value, onChange, columns = 2 }) {
  return (
    <div>
      <p className="text-sm font-semibold text-gray-700 mb-2">{title}</p>
      <div className={`grid gap-2 ${columns === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
        {options.map((opt) => {
          const selected = value === opt.value
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange(opt.value)}
              className={`text-left px-3 py-3 rounded-xl border-2 transition-all ${
                selected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 bg-white'
              }`}
            >
              <span className="block text-base leading-none mb-1">{opt.icon}</span>
              <span className={`block text-sm font-medium ${selected ? 'text-blue-600' : 'text-gray-700'}`}>
                {opt.label}
              </span>
              {opt.hint && (
                <span className="block text-xs text-gray-400 mt-0.5 leading-snug">{opt.hint}</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function SetupModal({ onComplete, onPreview }) {
  const [useLocation, setUseLocation] = useState('indoor')
  const [wateringMode, setWateringMode] = useState('automatic')
  const [theme, setTheme] = useState('system')

  const handleTheme = (t) => {
    setTheme(t)
    onPreview?.(t)
  }

  const handleComplete = () => {
    saveSettings({
      setupCompleted: true,
      useLocation,
      wateringMode,
      theme,
    })
    onComplete()
  }

  return (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md space-y-5 max-h-[90vh] overflow-y-auto">
        <div className="text-center">
          <div className="text-3xl mb-2">🌱</div>
          <h2 className="text-xl font-bold text-gray-800">Setup iniziale</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configura le preferenze base. Potrai modificarle in ogni momento dalle impostazioni.
          </p>
        </div>

        <OptionGroup
          title="Ambiente di utilizzo"
          options={LOCATION_OPTIONS}
          value={useLocation}
          onChange={setUseLocation}
        />

        <OptionGroup
          title="Modalità di innaffiatura"
          options={WATERING_OPTIONS}
          value={wateringMode}
          onChange={setWateringMode}
        />

        <OptionGroup
          title="Tema"
          options={THEME_OPTIONS}
          value={theme}
          onChange={handleTheme}
          columns={3}
        />

        <button
          type="button"
          onClick={handleComplete}
          className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition-colors"
        >
          Inizia
        </button>
      </div>
    </div>
  )
}
