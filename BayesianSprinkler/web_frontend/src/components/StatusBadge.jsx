import React from 'react'

function StatusBadge({ status, label }) {
  const isOnline = status === 'online'
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${isOnline ? 'bg-green-500 pulse-green' : 'bg-red-500'}`} />
      <span className="text-sm text-gray-600">{label}: {isOnline ? 'Online' : 'Offline'}</span>
    </div>
  )
}

export function HealthBar({ espOnline, bayesianOnline }) {
  return (
    <div className="flex gap-4 flex-wrap">
      <StatusBadge status={espOnline ? 'online' : 'offline'} label="ESP32" />
      <StatusBadge status={bayesianOnline ? 'online' : 'offline'} label="Bayesian" />
    </div>
  )
}