import React, { useState } from 'react'

const PLANT_LABELS = {
  habanero: 'Habanero',
  naga_morich: 'Naga Morich',
  carolina_reaper: 'Carolina Reaper',
  rosmarino: 'Rosmarino',
}

const SOIL_LABELS = { dry: 'dry', moist: 'moist', wet: 'wet' }
const TEMP_LABELS = { high: 'hot', medium: 'warm', low: 'cold' }
const HUMID_LABELS = { low: 'low', medium: 'medium', high: 'high' }
const CLOUD_LABELS = { clear: 'clear sky', cloudy: 'cloudy' }
const RAIN_LABELS = { no: 'no rain', yes: 'rain expected' }

function FactorBar({ label, score, icon, rawLabel }) {
  const color = score >= 70 ? 'bg-red-400' : score >= 40 ? 'bg-yellow-400' : 'bg-blue-400'
  const contribLabel = score >= 70 ? 'strongly suggests water' :
                       score >= 40 ? 'somewhat suggests water' :
                       score <= 0 ? 'suggests no water' : 'barely relevant'
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="text-lg" title={label}>{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-baseline mb-0.5">
          <span className="text-xs font-medium text-gray-700 truncate">{label}</span>
          <span className="text-xs text-gray-400 ml-2 shrink-0">{rawLabel}</span>
        </div>
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full ${color} rounded-full transition-all`}
            style={{ width: `${Math.abs(score)}%` }}
          />
        </div>
        <span className="text-xs text-gray-400">{contribLabel}</span>
      </div>
    </div>
  )
}

function WhySection({ status }) {
  const [open, setOpen] = useState(false)

  if (!status.evidence_nodes || status.evidence_nodes.length === 0) return null

  const nodeMap = {}
  status.evidence_nodes.forEach(n => { nodeMap[n.label] = n })

  const soil = nodeMap['Soil Moisture']
  const temp = nodeMap['Temperature']
  const humid = nodeMap['Humidity']
  const cloud = nodeMap['Cloud Cover']
  const rain = nodeMap['Rain Forecast']

  const getRawLabel = (label, value) => {
    if (label === 'Soil Moisture') return SOIL_LABELS[value] || value
    if (label === 'Temperature') return TEMP_LABELS[value] || value
    if (label === 'Humidity') return HUMID_LABELS[value] || value
    if (label === 'Cloud Cover') return CLOUD_LABELS[value] || value
    if (label === 'Rain Forecast') return RAIN_LABELS[value] || value
    return value
  }

  const getDiscreteValue = (score, label) => {
    if (label === 'Soil Moisture') return score >= 70 ? 'dry' : score >= 40 ? 'moist' : 'wet'
    if (label === 'Temperature') return score >= 60 ? 'high' : score >= 20 ? 'medium' : 'low'
    if (label === 'Humidity') return score >= 45 ? 'low' : score >= 15 ? 'medium' : 'high'
    if (label === 'Cloud Cover') return score >= 25 ? 'clear' : 'cloudy'
    if (label === 'Rain Forecast') return score > 0 ? 'no' : 'yes'
    return 'unknown'
  }

  return (
    <div className="mt-3 border-t border-gray-100 pt-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
      >
        <span>{open ? '▲' : '▼'}</span>
        {open ? 'Hide reasoning' : 'Why?'}
      </button>
      {open && (
        <div className="mt-2 space-y-1">
          {status.evidence_nodes.map((node) => {
            const discrete = getDiscreteValue(node.score, node.label)
            return (
              <FactorBar
                key={node.label}
                label={node.label}
                score={node.score}
                icon={node.icon === 'water_drop' ? '💧' :
                       node.icon === 'thermostat' ? '🌡️' :
                       node.icon === 'air' ? '💨' :
                       node.icon === 'cloud' ? '☁️' : '🌧️'}
                rawLabel={getRawLabel(node.label, discrete)}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

function SoilMoistureBadge({ value }) {
  if (value === null || value === undefined) return null
  const pct = Math.max(0, Math.min(100, Math.round(Number(value))))
  const color = pct <= 30 ? 'text-red-600' : pct <= 60 ? 'text-yellow-600' : 'text-green-600'
  return (
    <span className={`text-xs font-semibold ${color}`}>
      💧 {pct}%
    </span>
  )
}

function ProbabilityBar({ value, threshold }) {
  const pct = Math.round(value * 100)
  const color = pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Probability of needing water</span>
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
          const threshold = status.threshold ?? 0.5
          const needs = prob >= threshold
          return (
            <div key={status.plant_id} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold text-gray-700">{label}</span>
                <div className="flex items-center gap-2">
                  <SoilMoistureBadge value={status.soil_moisture} />
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${needs ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}`}>
                    {needs ? '💧 Needs water' : '✅ OK'}
                  </span>
                </div>
              </div>
              <ProbabilityBar value={prob} threshold={threshold} />
              <WhySection status={status} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
