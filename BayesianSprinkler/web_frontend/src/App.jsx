import React, { useState, useCallback } from 'react'
import { useEspData, usePlantStatuses } from './hooks/usePolling.js'
import { TelemetryPanel } from './components/TelemetryPanel.jsx'
import { BayesianInsights } from './components/BayesianInsights.jsx'
import { ControlPanel } from './components/ControlPanel.jsx'
import { SettingsPanel } from './components/SettingsPanel.jsx'
import { CameraPanel } from './components/CameraPanel.jsx'
import { AuditLog } from './components/AuditLog.jsx'
import { HealthBar } from './components/StatusBadge.jsx'
import { SimulationView } from './components/SimulationView.jsx'

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
  const { espData, espHealthy, waterLowAlert, error, loading } = useEspData()
  const { plantStatuses } = usePlantStatuses()

  const showToast = useCallback((msg, type = 'info') => {
    setToast({ message: msg, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  return (
    <div className="min-h-screen bg-smart-light">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🌿</span>
            <h1 className="text-xl font-bold text-gray-800">SmartSprinkler</h1>
          </div>
          <HealthBar espOnline={espHealthy} bayesianOnline={!error} waterLowAlert={waterLowAlert} />
        </div>
        {/* Nav tabs */}
        <div className="max-w-6xl mx-auto px-4 flex gap-1">
          {['dashboard', 'control', 'simulation', 'camera', 'logs', 'settings'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium capitalize rounded-t-lg transition-all ${
                activeTab === tab
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-500 hover:bg-gray-100'
              }`}
            >
              {tab === 'dashboard' ? 'Dashboard' : tab === 'control' ? 'Control' : tab === 'simulation' ? 'Simulation' : tab === 'camera' ? 'Camera' : tab === 'logs' ? 'Logs' : 'Settings'}
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
              <TelemetryPanel espData={espData} />
            )}

            {/* Bayesian insights */}
            {error ? null : (
              <BayesianInsights plantStatuses={plantStatuses} />
            )}
          </>
        )}

        {activeTab === 'control' && (
          <ControlPanel onMessage={showToast} />
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
          <SettingsPanel onSave={() => showToast('Settings saved', 'success')} />
        )}
      </main>

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}