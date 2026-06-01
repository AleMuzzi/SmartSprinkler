import React, { useState } from 'react'
import { PLANTS, sendEspCommand, sendBayesianManualWater } from '../services/api.js'

function LoadingSpinner() {
  return (
    <svg className="w-5 h-5 spinner text-white" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function PlantCard({ plant, selected, onSelect }) {
  return (
    <button
      onClick={() => onSelect(plant.id)}
      className={`p-3 rounded-xl border-2 text-center transition-all ${
        selected === plant.id
          ? 'border-green-500 bg-green-50 shadow-md'
          : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      <span className="text-2xl mb-1 block">{selected === plant.id ? '✓' : ''}</span>
      <span className="text-sm font-medium">{plant.label}</span>
    </button>
  )
}

export function ControlPanel({ onMessage }) {
  const [selectedPlant, setSelectedPlant] = useState(PLANTS[0].id)
  const [viaBayesian, setViaBayesian] = useState(false)
  const [amount, setAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('start')

  const handleWater = async () => {
    if (loading) return
    setLoading(true)
    try {
      if (viaBayesian) {
        await sendBayesianManualWater(selectedPlant)
        onMessage('Watering logged via Bayesian server', 'success')
      } else {
        if (mode === 'start') {
          const extra = amount ? { amount: parseInt(amount) } : {}
          if (Object.keys(extra).length > 0) {
            await sendEspCommand('DISPENSE_SPECIFIC_AMOUNT', selectedPlant.toUpperCase(), extra)
          } else {
            await sendEspCommand('START', selectedPlant.toUpperCase())
          }
        } else if (mode === 'stop') {
          await sendEspCommand('STOP', selectedPlant.toUpperCase())
        }
        onMessage(`${mode === 'stop' ? 'Stopped' : 'Started'} watering ${selectedPlant}`, 'success')
      }
    } catch (e) {
      onMessage(`Error: ${e.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-base font-semibold text-gray-700 mb-4 flex items-center gap-2">
        <span>💧</span> Irrigation Control
      </h3>

      <div className="space-y-5">
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span className="text-sm font-medium text-gray-600">Routing Mode</span>
          <div className="flex gap-2">
            <button
              onClick={() => setViaBayesian(false)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                !viaBayesian ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}
            >
              Direct ESP
            </button>
            <button
              onClick={() => setViaBayesian(true)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                viaBayesian ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
              }`}
            >
              Via Bayesian
            </button>
          </div>
        </div>

        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Select Plant</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {PLANTS.map((p) => (
              <PlantCard key={p.id} plant={p} selected={selectedPlant} onSelect={setSelectedPlant} />
            ))}
          </div>
        </div>

        {!viaBayesian && (
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Dispense Amount (ml)</p>
            <div className="flex gap-2 flex-wrap">
              {['', 100, 250, 500, 1000].map((v) => (
                <button
                  key={v}
                  onClick={() => setAmount(v === '' ? '' : String(v))}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    amount === v ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {v === '' ? 'Continuous' : `${v}ml`}
                </button>
              ))}
            </div>
          </div>
        )}

        {!viaBayesian && (
          <div className="flex gap-2">
            <button
              onClick={() => { setMode('start'); handleWater() }}
              disabled={loading}
              className="flex-1 bg-green-500 hover:bg-green-600 disabled:opacity-50 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-all"
            >
              {loading ? <LoadingSpinner /> : 'Start Watering'}
            </button>
            <button
              onClick={() => { setMode('stop'); handleWater() }}
              disabled={loading}
              className="flex-1 bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-all"
            >
              {loading ? <LoadingSpinner /> : 'Stop Watering'}
            </button>
          </div>
        )}

        {viaBayesian && (
          <button
            onClick={handleWater}
            disabled={loading}
            className="w-full bg-green-500 hover:bg-green-600 disabled:opacity-50 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-2 transition-all"
          >
            {loading ? <LoadingSpinner /> : 'Log Water Event via Bayesian'}
          </button>
        )}
      </div>
    </div>
  )
}