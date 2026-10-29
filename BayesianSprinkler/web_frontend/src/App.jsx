import React, { useState, useCallback, useEffect } from 'react'
import { useEspData, usePlantStatuses, useCisternStatus } from './hooks/usePolling.js'
import { useNotifications } from './hooks/useNotifications.js'
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
import { SetupModal } from './components/SetupModal.jsx'
import { NotificationBell } from './components/NotificationBell.jsx'
import { WateringReportModal } from './components/WateringReportModal.jsx'
import { getSettings, runInference, fetchWateringMode } from './services/api.js'
import {
  hasNotificationApi,
  raiseBrowserNotification,
  requestNotificationPermission,
} from './services/browserNotifications.js'
import { loadSettings, saveSettings } from './services/settings.js'

function Toast({ message, type, onClick }) {
  const bg = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-600' : 'bg-gray-700'
  const className = `fixed bottom-4 right-4 ${bg} text-white px-4 py-2 rounded-lg shadow-lg text-sm z-50 ${
    onClick ? 'cursor-pointer hover:opacity-90 text-left' : ''
  }`
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {message}
      </button>
    )
  }
  return <div className={className}>{message}</div>
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [toast, setToast] = useState(null)
  const [setupCompleted, setSetupCompleted] = useState(() => loadSettings().setupCompleted)
  const [appSettings, setAppSettings] = useState(() => loadSettings())
  const { espData, weather, espHealthy, serverHealthy, waterLowAlert, error, loading } = useEspData()
  const { plantStatuses, refetch: refetchPlantStatuses } = usePlantStatuses()
  const { cistern, refill: refillCistern, refetch: refetchCistern, cisternError } = useCisternStatus(getSettings().bayesianUrl)

  // Apply theme (light/dark/system) to the document root
  useEffect(() => {
    const root = document.documentElement
    const applyTheme = () => {
      const isDark = appSettings.theme === 'dark' ||
        (appSettings.theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
      root.classList.toggle('dark', isDark)
    }
    applyTheme()
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', applyTheme)
    return () => media.removeEventListener('change', applyTheme)
  }, [appSettings.theme])

  const handleSetupComplete = useCallback(() => {
    setSetupCompleted(true)
    setAppSettings(loadSettings())
  }, [])

  const showToast = useCallback((msg, type = 'info', onClick = null) => {
    setToast({ message: msg, type, onClick })
    setTimeout(() => setToast(null), onClick ? 8000 : 3000)
  }, [])

  const [reportNotification, setReportNotification] = useState(null)

  const handleNewNotifications = useCallback((fresh) => {
    const latest = fresh[0]
    showToast(`${latest.title} — apri per i dettagli`, 'info', () => setReportNotification(latest))

    if (!hasNotificationApi()) return
    const raise = () => {
      fresh.forEach((n) => {
        raiseBrowserNotification({
          title: n.title,
          body: n.body,
          tag: `watering-${n.id}`,
          onClick: () => setReportNotification(n),
        })
      })
    }
    if (Notification.permission === 'granted') {
      raise()
    } else if (Notification.permission === 'default') {
      // Fallback for browsers that only grant permission after a user
      // gesture (the settings/setup flow requests it explicitly).
      requestNotificationPermission().then((permission) => {
        if (permission === 'granted') raise()
      })
    }
  }, [showToast])

  const {
    notifications,
    unreadCount,
    refresh: refreshNotifications,
    open: markNotificationOpen,
    readAll: markAllNotificationsRead,
  } = useNotifications({ onNew: handleNewNotifications })

  // Opening the report marks it as opened server-side, which clears the badge.
  useEffect(() => {
    if (reportNotification) {
      markNotificationOpen(reportNotification).catch(() => {})
    }
  }, [reportNotification, markNotificationOpen])

  // The server owns the watering mode: mirror it into the local settings so
  // the setup modal and the settings panel show the effective value.
  useEffect(() => {
    fetchWateringMode()
      .then((mode) => saveSettings({ wateringMode: mode }))
      .catch(() => { /* offline: keep the cached value */ })
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
      if (res.mode === 'notification') {
        if (watered.length) {
          // Dry-run: the proposal is already stored server-side, refresh so
          // the bell and the toast fire right away instead of on next poll.
          refreshNotifications()
        } else {
          showToast('Inferenza eseguita — nessuna pianta da annaffiare', 'success')
        }
      } else {
        showToast(
          watered.length
            ? `Inferenza eseguita — ${watered.join(', ')} annaffiate`
            : 'Inferenza eseguita — nessuna pianta da annaffiare',
          'success',
        )
      }
      refetchPlantStatuses()
    } catch (e) {
      showToast(`Inferenza fallita: ${e.message}`, 'error')
    } finally {
      setInferenceRunning(false)
    }
  }, [refetchPlantStatuses, refreshNotifications, showToast])

  return (
    <div className="min-h-screen bg-smart-light">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap min-w-0">
            <div className="flex items-center gap-2">
              <img src="/favicon.png" alt="SmartSprinkler" className="w-7 h-7" />
              <h1 className="text-xl font-bold text-gray-800">SmartSprinkler</h1>
            </div>
            <div className="hidden sm:block w-px h-6 bg-gray-200" aria-hidden="true" />
            <HealthBar
              espOnline={espHealthy}
              serverOnline={serverHealthy}
              waterLowAlert={waterLowAlert}
            />
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <CisternWidget
              levelMl={cistern.levelMl}
              capacityMl={cistern.capacityMl}
              lowAlert={cistern.waterLowAlert}
              onRefill={handleCisternRefill}
              onExpand={() => setActiveTab('dashboard')}
            />
            <NotificationBell
              notifications={notifications}
              unreadCount={unreadCount}
              onOpen={setReportNotification}
              onReadAll={markAllNotificationsRead}
            />
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

            {/* Bayesian insights — served by the same backend as the badge */}
            {!serverHealthy ? null : (
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
            <SettingsPanel onSave={() => { setAppSettings(loadSettings()); showToast('Settings saved', 'success') }} />
            <FirmwareUpdatePanel onMessage={showToast} />
          </div>
        )}
      </main>

      {!setupCompleted && (
        <SetupModal
          onComplete={handleSetupComplete}
          onPreview={(theme) => setAppSettings((prev) => ({ ...prev, theme }))}
        />
      )}

      <WateringReportModal
        notification={reportNotification}
        onClose={() => setReportNotification(null)}
      />

      {toast && (
        <Toast message={toast.message} type={toast.type} onClick={toast.onClick || null} />
      )}
    </div>
  )
}