import React, { useEffect, useState } from 'react'
import { fetchAuditLog, exportAuditLogCsv } from '../services/api.js'

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
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)
  const [count, setCount] = useState(0)
  const [expandedDetails, setExpandedDetails] = useState({})

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

  const downloadCsv = async () => {
    setExporting(true)
    setError(null)
    try {
      const { blob, contentDisposition } = await exportAuditLogCsv({
        filter,
        category: category || null,
      })
      // Try to honour server-suggested filename, fallback to timestamp.
      let filename = `audit_log_${Date.now()}.csv`
      const m = contentDisposition.match(/filename="?([^";]+)"?/)
      if (m) filename = m[1]
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.message)
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [filter, category])

  const errorCount = entries.filter((e) => e.category === 'error').length
  const recentErrors = entries.filter((e) => e.category === 'error').slice(0, 5)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-gray-700 flex items-center gap-2">
          <span>📋</span> Audit Log
          <span className="text-xs text-gray-400 font-normal">({count} entries)</span>
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={downloadCsv}
            disabled={exporting}
            className="text-xs px-3 py-1 rounded bg-blue-500 text-white hover:bg-blue-600 disabled:bg-gray-300"
          >
            {exporting ? '...' : '⬇ Download CSV'}
          </button>
          <button
            onClick={load}
            disabled={loading}
            className="text-xs px-3 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-700"
          >
            {loading ? '...' : 'Refresh'}
          </button>
        </div>
      </div>

      {errorCount > 0 && (
        <div className="mb-3 rounded-xl border border-red-200 bg-red-50 p-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-red-600 font-semibold text-sm">⚠️ {errorCount} error{errorCount === 1 ? '' : 's'} in this view</span>
            <button
              onClick={() => setCategory('error')}
              className="text-xs px-2 py-0.5 rounded bg-red-500 text-white hover:bg-red-600"
            >
              View errors
            </button>
          </div>
          {category !== 'error' && recentErrors.slice(0, 2).map((e) => (
            <div key={e.id} className="text-xs text-red-700 font-mono break-all">
              • {e.message}
            </div>
          ))}
        </div>
      )}

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
          <option value="ota">ota</option>
        </select>
      </div>

      {error && (
        <div className="text-red-600 text-sm mb-3">⚠️ {error}</div>
      )}

      <div className="overflow-y-auto max-h-[480px] divide-y divide-gray-100">
        {entries.length === 0 && !loading && (
          <div className="text-gray-400 text-sm text-center py-8">No log entries</div>
        )}
        {entries.map((entry) => {
          const expanded = expandedDetails[entry.id]
          const details = entry.details || ''
          const long = details.length > 120
          return (
            <div key={entry.id} className={`py-2 hover:bg-gray-50 px-2 -mx-2 rounded ${entry.category === 'error' ? 'bg-red-50/50' : ''}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${CATEGORY_COLORS[entry.category] || 'bg-gray-100 text-gray-700'}`}>
                  {entry.category}
                </span>
                <span className="text-xs text-gray-400">{formatTimestamp(entry.timestamp)}</span>
              </div>
              <div className="text-sm text-gray-700">{entry.message}</div>
              {details && (
                <div className="text-xs text-gray-500 mt-0.5 font-mono break-all">
                  {long && !expanded ? `${details.slice(0, 120)}… ` : details}
                  {long && (
                    <button
                      onClick={() => setExpandedDetails((d) => ({ ...d, [entry.id]: !expanded }))}
                      className="text-xs text-blue-500 hover:underline ml-1"
                    >
                      {expanded ? '▲ collapse' : '▼ expand'}
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}