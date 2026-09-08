import React, { useState, useEffect } from 'react'
import { loadSettings, saveSettings } from '../services/settings.js'
import {
  fetchServiceConfig,
  setServicePaused,
  getRefineConfig,
  setRefineConfig,
  triggerRefineNow,
  applyRefinedModel,
  deleteRefinedModel,
} from '../services/api.js'

export function SettingsPanel({ onSave }) {
  const [espUrl, setEspUrl] = useState('')
  const [bayesianUrl, setBayesianUrl] = useState('')
  const [pollingInterval, setPollingInterval] = useState(2000)
  const [saved, setSaved] = useState(false)
  const [servicePaused, setServicePausedState] = useState(false)
  const [serviceLoading, setServiceLoading] = useState(false)
  const [serviceError, setServiceError] = useState(null)

  const [refineEnabled, setRefineEnabled] = useState(false)
  const [refineSchedule, setRefineSchedule] = useState('10 * * * *')
  const [activeModel, setActiveModel] = useState('expert')
  const [availableModels, setAvailableModels] = useState([])
  const [refineLoading, setRefineLoading] = useState(false)
  const [refineError, setRefineError] = useState(null)
  const [refineResult, setRefineResult] = useState(null)

  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deleteSelected, setDeleteSelected] = useState([])

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
    getRefineConfig()
      .then((data) => {
        setRefineEnabled(data.enabled)
        setRefineSchedule(data.schedule)
        setActiveModel(data.active_model)
        setAvailableModels(data.available_models || [])
      })
      .catch((e) => setRefineError(e.message))
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

        {/* ── Bayesian Model Refinement ──────────────────────────── */}
        <div className="border-t border-gray-100 pt-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Modello Bayesiano</h4>

          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-gray-700">Auto-refinement</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {refineEnabled
                  ? `Attivo — cron: ${refineSchedule}`
                  : 'Disattivato'}
              </p>
            </div>
            <button
              onClick={async () => {
                setRefineLoading(true)
                setRefineError(null)
                try {
                  const res = await setRefineConfig({ enabled: !refineEnabled })
                  setRefineEnabled(res.enabled)
                  setRefineSchedule(res.schedule)
                } catch (e) {
                  setRefineError(e.message)
                } finally {
                  setRefineLoading(false)
                }
              }}
              disabled={refineLoading}
              className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all disabled:opacity-50 ${
                refineEnabled
                  ? 'bg-green-500 hover:bg-green-600 text-white'
                  : 'bg-gray-300 hover:bg-gray-400 text-gray-700'
              }`}
            >
              {refineLoading ? '…' : refineEnabled ? 'ON' : 'OFF'}
            </button>
          </div>

          {refineEnabled && (
            <div className="mb-3">
              <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">Cron schedule</label>
              <input
                type="text"
                value={refineSchedule}
                onChange={(e) => setRefineSchedule(e.target.value)}
                onBlur={async () => {
                  try {
                    await setRefineConfig({ schedule: refineSchedule })
                  } catch (e) {
                    setRefineError(e.message)
                  }
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <p className="text-xs text-gray-400 mt-1">es. <code>10 * * *</code> = ogni ora al minuto 10</p>
            </div>
          )}

          <div className="mb-3">
            <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">Modello attivo</label>
            <select
              value={activeModel}
              onChange={async (e) => {
                const val = e.target.value
                setRefineLoading(true)
                setRefineError(null)
                try {
                  const res = await applyRefinedModel(val)
                  setActiveModel(res.active_model)
                  setAvailableModels(res.available_models)
                } catch (err) {
                  setRefineError(err.message)
                } finally {
                  setRefineLoading(false)
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              <option value="expert">Expert (CPT originali)</option>
              {availableModels.map((m) => (
                <option key={m.path} value={m.path}>
                  {m.filename} {m.active ? '✓' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-2 mb-2">
            <button
              onClick={async () => {
                setRefineLoading(true)
                setRefineError(null)
                setRefineResult(null)
                try {
                  const res = await triggerRefineNow()
                  setRefineResult(`Fatto: ${res.result.filename || 'nessun dato'}`)
                  setAvailableModels(res.available_models)
                } catch (e) {
                  setRefineError(e.message)
                } finally {
                  setRefineLoading(false)
                }
              }}
              disabled={refineLoading}
              className="flex-1 py-2 rounded-lg text-xs font-semibold bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-50"
            >
              Refine Now
            </button>
            <button
              onClick={() => { setDeleteSelected([]); setDeleteModalOpen(true) }}
              disabled={refineLoading || availableModels.length === 0}
              className="flex-1 py-2 rounded-lg text-xs font-semibold bg-red-100 hover:bg-red-200 text-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Delete Model
            </button>
          </div>

          {refineError && <p className="text-xs text-red-500 mt-1">{refineError}</p>}
          {refineResult && <p className="text-xs text-green-600 mt-1">{refineResult}</p>}
        </div>

        {deleteModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/40" onClick={() => setDeleteModalOpen(false)} />
            <div className="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-5">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Elimina modelli</h4>
              <label className="flex items-center gap-2 text-xs text-gray-500 mb-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={deleteSelected.length === availableModels.length && availableModels.length > 0}
                  onChange={(e) => {
                    setDeleteSelected(e.target.checked ? availableModels.map((m) => m.filename) : [])
                  }}
                  className="rounded"
                />
                Seleziona tutti
              </label>
              <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-100 mb-4">
                {availableModels.map((m) => (
                  <label key={m.path} className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 select-none">
                    <input
                      type="checkbox"
                      checked={deleteSelected.includes(m.filename)}
                      onChange={(e) => {
                        setDeleteSelected((prev) =>
                          e.target.checked
                            ? [...prev, m.filename]
                            : prev.filter((f) => f !== m.filename)
                        )
                      }}
                      className="rounded"
                    />
                    <span className="flex-1 truncate">{m.filename}</span>
                    {m.active && <span className="text-xs text-green-600 font-medium shrink-0">attivo</span>}
                  </label>
                ))}
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setDeleteModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-600"
                >
                  Annulla
                </button>
                <button
                  disabled={deleteSelected.length === 0}
                  onClick={async () => {
                    setRefineLoading(true)
                    setRefineError(null)
                    try {
                      for (const fn of deleteSelected) {
                        await deleteRefinedModel(fn)
                      }
                      const data = await getRefineConfig()
                      setAvailableModels(data.available_models)
                      setActiveModel(data.active_model)
                      setDeleteModalOpen(false)
                    } catch (e) {
                      setRefineError(e.message)
                    } finally {
                      setRefineLoading(false)
                    }
                  }}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-red-500 hover:bg-red-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Elimina {deleteSelected.length > 0 && `(${deleteSelected.length})`}
                </button>
              </div>
            </div>
          </div>
        )}

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