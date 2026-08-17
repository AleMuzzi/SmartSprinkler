import React, { useState, useCallback } from 'react'
import { useEspData, usePlantStatuses, useCisternStatus } from './hooks/usePolling.js'
import { TelemetryPanel } from './components/TelemetryPanel.jsx'
import { BayesianInsights } from './components/BayesianInsights.jsx'
import { ControlPanel } from './components/ControlPanel.jsx'
import { SettingsPanel } from './components/SettingsPanel.jsx'
import { FirmwareUpdatePanel } from './components/FirmwareUpdatePanel.jsx'
import { CameraPanel } from './components/CameraPanel.jsx'
import { AuditLog } from './components/AuditLog.jsx'
import { ChartsView } from './components/ChartsView.jsx'
import { HealthBar } from './components/StatusBadge.jsx'
import { SimulationView } from './components/SimulationView.jsx'
import { CisternCard, CisternWidget } from './components/SimulationView.jsx'
import { getSettings, runInference } from './services/api.js'

function Toast({ message, type }) {
  const bg = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-600' : 'bg-gray-700'
  return (
    <div className={`fixed bottom-4 right-4 ${bg} text-white px-4 py-2 rounded-lg shadow-lg text-sm z-50`}>
      {message}
    </div>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [toast, setToast] = useState(null)
  const { espData, weather, espHealthy, waterLowAlert, error, loading } = useEspData()
  const { plantStatuses, refetch: refetchPlantStatuses } = usePlantStatuses()
  const { cistern, refill: refillCistern, refetch: refetchCistern, cisternError } = useCisternStatus(getSettings().bayesianUrl)

  const showToast = useCallback((msg, type = 'info') => {
    setToast({ message: msg, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  const handleCisternRefill = useCallback(async () => {
    try {
      await refillCistern()
      showToast('Cisterna riempita', 'success')
    } catch (e) {
      showToast(`Refill fallito: ${e.message}`, 'error')
    }
  }, [refillCistern, showToast])

  const [inferenceRunning, setInferenceRunning] = useState(false)
  const handleRunInference = useCallback(async () => {
    setInferenceRunning(true)
    try {
      const res = await runInference()
      const watered = Object.keys(res.watered || {})
      showToast(
        watered.length
          ? `Inferenza eseguita — ${watered.join(', ')} annaffiate`
          : 'Inferenza eseguita — nessuna pianta da annaffiare',
        'success',
      )
      refetchPlantStatuses()
    } catch (e) {
      showToast(`Inferenza fallita: ${e.message}`, 'error')
    } finally {
      setInferenceRunning(false)
    }
  }, [refetchPlantStatuses, showToast])

  return (
    <div className="min-h-screen bg-smart-light">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <img src="/favicon.png" alt="SmartSprinkler" className="w-7 h-7" />
            <h1 className="text-xl font-bold text-gray-800">SmartSprinkler</h1>
          </div>
          <div className="flex items-center gap-3">
            <CisternWidget
              levelMl={cistern.levelMl}
              capacityMl={cistern.capacityMl}
              lowAlert={cistern.waterLowAlert}
              onRefill={handleCisternRefill}
              onExpand={() => setActiveTab('dashboard')}
            />
            <HealthBar espOnline={espHealthy} bayesianOnline={!error} waterLowAlert={waterLowAlert} />
          </div>
        </div>
        {/* Nav tabs */}
        <div className="max-w-6xl mx-auto px-4 flex gap-1">
          {['dashboard', 'control', 'charts', 'simulation', 'camera', 'logs', 'settings'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium capitalize rounded-t-lg transition-all ${
                activeTab === tab
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              {tab === 'dashboard' ? 'Dashboard' : tab === 'control' ? 'Control' : tab === 'charts' ? 'Statistics' : tab === 'simulation' ? 'Simulation' : tab === 'camera' ? 'Camera' : tab === 'logs' ? 'Logs' : 'Settings'}
            </button>
          ))}
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {activeTab === 'dashboard' && (
          <>
            {/* Telemetry */}
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full spinner" />
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-600 text-center">
                ⚠️ ESP32 unreachable — check wiring and IP address
              </div>
            ) : (
              <TelemetryPanel espData={espData} weather={weather} />
            )}

            {/* Cistern — production status, always shown outside the simulator */}
            <CisternCard
              levelMl={cistern.levelMl}
              capacityMl={cistern.capacityMl}
              lowAlert={cistern.waterLowAlert}
              onRefill={handleCisternRefill}
              error={cisternError}
            />

            {/* Bayesian insights */}
            {error ? null : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Ciclo di inferenza: ogni ora (al minuto 4); qui puoi forzarlo subito</span>
                  <button
                    onClick={handleRunInference}
                    disabled={inferenceRunning}
                    className="px-3 py-1.5 rounded-lg text-sm font-semibold text-white bg-blue-500 hover:bg-blue-600 disabled:opacity-50 flex items-center gap-2 transition-all"
                  >
                    {inferenceRunning ? (
                      <>
                        <svg className="w-4 h-4 spinner" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Esecuzione…
                      </>
                    ) : (
                      <>▶ Inferenza ora</>
                    )}
                  </button>
                </div>
                <BayesianInsights plantStatuses={plantStatuses} />
              </>
            )}
          </>
        )}

        {activeTab === 'control' && (
          <ControlPanel onMessage={showToast} />
        )}

        {activeTab === 'charts' && (
          <ChartsView />
        )}

        {activeTab === 'simulation' && (
          <SimulationView />
        )}

        {activeTab === 'camera' && (
          <CameraPanel />
        )}

        {activeTab === 'logs' && (
          <AuditLog />
        )}

        {activeTab === 'settings' && (
          <div className="grid md:grid-cols-2 gap-6">
            <SettingsPanel onSave={() => showToast('Settings saved', 'success')} />
            <FirmwareUpdatePanel onMessage={showToast} />
          </div>
        )}
      </main>

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}