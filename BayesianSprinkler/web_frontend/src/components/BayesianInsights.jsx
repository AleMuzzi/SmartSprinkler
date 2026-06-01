import React from 'react'

const PLANT_LABELS = {
  habanero: 'Habanero',
  naga_morich: 'Naga Morich',
  carolina_reaper: 'Carolina Reaper',
  rosmarino: 'Rosmarino',
}

function ProbabilityBar({ value, threshold = 0.5 }) {
  const pct = Math.round(value * 100)
  const color = pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Need probability</span>
        <span className="font-bold">{pct}%</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden relative">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex justify-end mt-0.5">
        <span className="text-xs text-gray-400">| threshold {Math.round(threshold * 100)}%</span>
      </div>
    </div>
  )
}

export function BayesianInsights({ plantStatuses }) {
  if (!plantStatuses || plantStatuses.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-400">
        No plant status data available
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-base font-semibold text-gray-700 mb-4 flex items-center gap-2">
        <span>🌿</span> Bayesian Watering Insights
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {plantStatuses.map((status) => {
          const label = PLANT_LABELS[status.plant_id] || status.plant_id
          const prob = status.probability_of_need ?? 0
          const needs = prob >= 0.5
          return (
            <div key={status.plant_id} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold text-gray-700">{label}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${needs ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                  {needs ? 'Needs water' : 'OK'}
                </span>
              </div>
              <ProbabilityBar value={prob} />
            </div>
          )
        })}
      </div>
    </div>
  )
}