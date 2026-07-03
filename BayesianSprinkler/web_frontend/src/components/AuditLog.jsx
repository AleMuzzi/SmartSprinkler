import React, { useEffect, useState } from 'react'
import { fetchAuditLog } from '../services/api.js'

const CATEGORY_COLORS = {
  inference: 'bg-blue-100 text-blue-700',
  command: 'bg-green-100 text-green-700',
  alert: 'bg-red-100 text-red-700',
  error: 'bg-red-200 text-red-900',
  config: 'bg-purple-100 text-purple-700',
}

function formatTimestamp(ts) {
  try {
    const d = new Date(ts)
    return d.toLocaleString()
  } catch {
    return ts
  }
}

export function AuditLog({ initialFilter = '' }) {
  const [entries, setEntries] = useState([])
  const [filter, setFilter] = useState(initialFilter)
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [count, setCount] = useState(0)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchAuditLog({ filter, category: category || null, limit: 200 })
      setEntries(res.entries || [])
      setCount(res.count || 0)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [filter, category])

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-gray-700 flex items-center gap-2">
          <span>📋</span> Audit Log
          <span className="text-xs text-gray-400 font-normal">({count} entries)</span>
        </h3>
        <button
          onClick={load}
          disabled={loading}
          className="text-xs px-3 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-700"
        >
          {loading ? '...' : 'Refresh'}
        </button>
      </div>

      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by text…"
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white"
        >
          <option value="">All categories</option>
          <option value="inference">inference</option>
          <option value="command">command</option>
          <option value="alert">alert</option>
          <option value="error">error</option>
          <option value="config">config</option>
        </select>
      </div>

      {error && (
        <div className="text-red-600 text-sm mb-3">⚠️ {error}</div>
      )}

      <div className="overflow-y-auto max-h-[480px] divide-y divide-gray-100">
        {entries.length === 0 && !loading && (
          <div className="text-gray-400 text-sm text-center py-8">No log entries</div>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className="py-2 hover:bg-gray-50 px-2 -mx-2 rounded">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${CATEGORY_COLORS[entry.category] || 'bg-gray-100 text-gray-700'}`}>
                {entry.category}
              </span>
              <span className="text-xs text-gray-400">{formatTimestamp(entry.timestamp)}</span>
            </div>
            <div className="text-sm text-gray-700">{entry.message}</div>
            {entry.details && (
              <div className="text-xs text-gray-500 mt-0.5 font-mono break-all">{entry.details}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}