import React, { useEffect } from 'react'
import { PLANTS } from '../services/api.js'
import { formatNotificationDate } from './NotificationBell.jsx'

const PLANT_LABELS = Object.fromEntries(PLANTS.map((p) => [p.id, p.label]))

/**
 * Read-only report of a watering proposal: which plants need water and how
 * much each one would receive. Deliberately carries no "water now" action —
 * in notification mode the decision stays with the user, who can act from
 * the control panel.
 */
export function WateringReportModal({ notification, onClose }) {
  useEffect(() => {
    if (!notification) return undefined
    const handleKey = (event) => {
      if (event.key === 'Escape') onClose?.()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [notification, onClose])

  if (!notification) return null

  const doses = Object.entries(notification.doses || {})
  const total = doses.reduce((sum, [, ml]) => sum + Number(ml), 0)

  return (
    <div
      className="fixed inset-0 bg-gray-900 bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-sm max-h-[70vh] overflow-y-auto p-5"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="text-2xl mb-1">💧</div>
            <h2 className="text-base font-bold text-gray-800">{notification.title}</h2>
            <p className="text-xs text-gray-400 mt-0.5">{formatNotificationDate(notification.created_at)}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Chiudi"
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-all"
          >
            ✕
          </button>
        </div>

        <div className="rounded-xl border border-gray-100 divide-y divide-gray-50">
          {doses.map(([plantId, ml]) => (
            <div key={plantId} className="flex items-center justify-between px-3 py-2.5">
              <span className="text-sm text-gray-700">{PLANT_LABELS[plantId] || plantId}</span>
              <span className="text-sm font-semibold text-blue-600">{Math.round(ml)} ml</span>
            </div>
          ))}
          <div className="flex items-center justify-between px-3 py-2.5 bg-gray-50 rounded-b-xl">
            <span className="text-sm font-semibold text-gray-700">Totale</span>
            <span className="text-sm font-bold text-gray-800">{Math.round(total)} ml</span>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-3 leading-snug">
          Nessuna acqua è stata erogata: apri il pannello di controllo per innaffiare quando vuoi.
        </p>

        <button
          type="button"
          onClick={onClose}
          className="w-full mt-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-colors"
        >
          Chiudi
        </button>
      </div>
    </div>
  )
}
