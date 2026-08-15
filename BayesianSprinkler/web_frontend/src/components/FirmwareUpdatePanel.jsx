import React, { useState, useEffect, useRef } from 'react'
import { fetchFirmwareVersion, uploadFirmware } from '../services/api.js'

export function FirmwareUpdatePanel({ onMessage }) {
  const [version, setVersion] = useState('-')
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(null)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')
  const fileInputRef = useRef(null)

  useEffect(() => {
    refreshVersion()
  }, [])

  const refreshVersion = async () => {
    try {
      const v = await fetchFirmwareVersion()
      setVersion(v)
      setStatus('')
    } catch (e) {
      setVersion('-')
    }
  }

  const handleFile = (e) => {
    const selected = e.target.files?.[0] || null
    if (selected && !selected.name.toLowerCase().endsWith('.bin')) {
      onMessage?.('Seleziona un file .bin', 'error')
      setFile(null)
      e.target.value = ''
      return
    }
    setFile(selected)
    setProgress(null)
    setStatus('')
  }

  const handleUpload = async () => {
    if (!file) {
      onMessage?.('Seleziona prima un file firmware', 'error')
      return
    }
    setBusy(true)
    setProgress(0)
    setStatus('Upload in corso...')
    try {
      await uploadFirmware(file, (p) => setProgress(p))
      setStatus('Firmware inviato. La ESP si riavvierà a breve...')
      onMessage?.('Firmware aggiornato con successo', 'success')
      setTimeout(() => {
        setBusy(false)
        setFile(null)
        setProgress(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
        refreshVersion()
      }, 3000)
    } catch (e) {
      setStatus(`Errore: ${e.message}`)
      setBusy(false)
      onMessage?.(e.message, 'error')
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <span>🔧</span> Firmware Update
      </h4>

      <div className="flex items-center gap-3 mb-4">
        <span className="text-xs text-gray-500 uppercase tracking-wide">Versione corrente</span>
        <span className="px-3 py-1 bg-gray-100 rounded-lg font-mono text-sm text-gray-800">
          {version}
        </span>
        <button
          onClick={refreshVersion}
          className="text-xs text-blue-500 hover:text-blue-700"
        >
          ↻ Refresh
        </button>
      </div>

      <div className="space-y-3">
        <input
          ref={fileInputRef}
          type="file"
          accept=".bin"
          onChange={handleFile}
          disabled={busy}
          className="text-sm text-gray-600 file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-600 file:text-sm file:font-semibold hover:file:bg-blue-100"
        />

        {file && (
          <p className="text-xs text-gray-500">Selezionato: {file.name} ({Math.round(file.size / 1024)} KB)</p>
        )}

        {progress !== null && (
          <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        {progress !== null && status && (
          <p className="text-xs text-gray-600">{status} {progress !== null ? `${progress}%` : ''}</p>
        )}

        <button
          onClick={handleUpload}
          disabled={busy || !file}
          className={`w-full py-2.5 rounded-lg font-semibold transition-all ${
            busy || !file
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          {busy ? 'Upload in corso...' : 'Aggiorna Firmware'}
        </button>
      </div>
    </div>
  )
}