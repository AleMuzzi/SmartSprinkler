import React, { useState, useEffect } from 'react'
import { loadSettings, saveSettings } from '../services/settings.js'

export function SettingsPanel({ onSave }) {
  const [espUrl, setEspUrl] = useState('')
  const [bayesianUrl, setBayesianUrl] = useState('')
  const [pollingInterval, setPollingInterval] = useState(2000)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const s = loadSettings()
    setEspUrl(s.espUrl)
    setBayesianUrl(s.bayesianUrl)
    setPollingInterval(s.pollingInterval)
  }, [])

  const handleSave = () => {
    saveSettings({ espUrl, bayesianUrl, pollingInterval })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    onSave?.()
  }

  const hasChanges = () => {
    const s = loadSettings()
    return s.espUrl !== espUrl || s.bayesianUrl !== bayesianUrl || s.pollingInterval !== pollingInterval
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-base font-semibold text-gray-700 mb-4 flex items-center gap-2">
        <span>⚙️</span> Settings
      </h3>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">ESP32 URL</label>
          <input
            type="url"
            value={espUrl}
            onChange={(e) => { setEspUrl(e.target.value); setSaved(false) }}
            placeholder="http://192.168.1.50:80"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">Bayesian Server URL</label>
          <input
            type="url"
            value={bayesianUrl}
            onChange={(e) => { setBayesianUrl(e.target.value); setSaved(false) }}
            placeholder="http://localhost:8080"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">Polling Interval (ms)</label>
          <input
            type="number"
            value={pollingInterval}
            onChange={(e) => { setPollingInterval(parseInt(e.target.value) || 2000); setSaved(false) }}
            min={1000}
            max={30000}
            step={500}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <p className="text-xs text-gray-400 mt-1">Default: 2000ms (matches mobile app)</p>
        </div>

        <button
          onClick={handleSave}
          disabled={!hasChanges()}
          className={`w-full py-2.5 rounded-lg font-semibold transition-all ${
            hasChanges()
              ? 'bg-blue-500 hover:bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
        >
          {saved ? '✓ Saved!' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}