import React, { useState, useEffect } from 'react'
import { loadSettings, saveSettings } from '../services/settings.js'
import { fetchServiceConfig, setServicePaused } from '../services/api.js'

export function SettingsPanel({ onSave }) {
  const [espUrl, setEspUrl] = useState('')
  const [bayesianUrl, setBayesianUrl] = useState('')
  const [pollingInterval, setPollingInterval] = useState(2000)
  const [saved, setSaved] = useState(false)
  const [servicePaused, setServicePausedState] = useState(false)
  const [serviceLoading, setServiceLoading] = useState(false)
  const [serviceError, setServiceError] = useState(null)

  useEffect(() => {
    const s = loadSettings()
    setEspUrl(s.espUrl)
    setBayesianUrl(s.bayesianUrl)
    setPollingInterval(s.pollingInterval)
  }, [])

  useEffect(() => {
    fetchServiceConfig()
      .then((data) => setServicePausedState(data.config?.paused === '1'))
      .catch((e) => setServiceError(e.message))
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
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Polling Interval (ms)</p>
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

        <div className="border-t border-gray-100 pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Servizio di inferenza</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {servicePaused
                  ? '⏸ In pausa — il ciclo orario è fermo (weather e azioni manuali restano attivi)'
                  : '⚪ Attivo — inferenza ogni ora (al minuto 4)'}
              </p>
              {serviceError && (
                <p className="text-xs text-red-500 mt-1">Errore: {serviceError}</p>
              )}
            </div>
            <button
              onClick={async () => {
                setServiceLoading(true)
                setServiceError(null)
                try {
                  const res = await setServicePaused(!servicePaused)
                  setServicePausedState(res.paused)
                } catch (e) {
                  setServiceError(e.message)
                } finally {
                  setServiceLoading(false)
                }
              }}
              disabled={serviceLoading}
              className={`shrink-0 px-4 py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-50 ${
                servicePaused
                  ? 'bg-green-500 hover:bg-green-600 text-white'
                  : 'bg-red-500 hover:bg-red-600 text-white'
              }`}
            >
              {serviceLoading ? '…' : servicePaused ? '▶ Riprendi' : '⏸ Metti in pausa'}
            </button>
          </div>
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