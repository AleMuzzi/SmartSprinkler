import React, { useState, useEffect, useRef } from 'react'
import { getSettings } from '../services/api.js'

export function CameraPanel() {
  const [enabled, setEnabled] = useState(false)
  const [error, setError] = useState(false)
  const imgRef = useRef(null)

  const { espUrl } = getSettings()
  const streamUrl = espUrl.replace(/:\d+$/, '') + ':81/stream'

  useEffect(() => {
    if (!enabled) return
    setError(false)
    if (imgRef.current) {
      imgRef.current.src = streamUrl + `?t=${Date.now()}`
    }
  }, [enabled, streamUrl])

  const handleToggle = () => {
    if (enabled) {
      if (imgRef.current) {
        imgRef.current.src = ''
      }
    }
    setEnabled(e => !e)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-gray-700 flex items-center gap-2">
          <span>📷</span> Camera Feed
        </h3>
        <button
          onClick={handleToggle}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
            enabled
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-blue-500 text-white hover:bg-blue-600'
          }`}
        >
          {enabled ? 'Stop' : 'Start'}
        </button>
      </div>

      {enabled ? (
        <div className="relative rounded-lg overflow-hidden bg-gray-100">
          {error ? (
            <div className="flex items-center justify-center h-48 text-gray-400">
              Camera unreachable — check ESP IP and port 80
            </div>
          ) : (
            <img
              ref={imgRef}
              src={streamUrl + `?t=${Date.now()}`}
              alt="ESP Camera"
              className="w-full h-auto"
              onError={() => setError(true)}
            />
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-32 text-gray-400 text-sm rounded-lg bg-gray-50">
          Press Start to view live MJPEG stream
        </div>
      )}
    </div>
  )
}