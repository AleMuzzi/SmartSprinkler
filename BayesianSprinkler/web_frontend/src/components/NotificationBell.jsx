import React, { useState, useEffect, useRef } from 'react'

export function formatNotificationDate(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('it-IT', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function NotificationBell({ notifications, unreadCount, onOpen, onReadAll }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const handleOutside = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false)
    }
    const handleKey = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handleOutside)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleOutside)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open])

  const badge = unreadCount > 99 ? '99+' : unreadCount

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Notifiche"
        className="relative w-9 h-9 flex items-center justify-center rounded-lg border border-gray-200 hover:bg-gray-100 transition-all"
      >
        <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold leading-none">
            {badge}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 max-h-[70vh] flex flex-col bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <span className="text-sm font-semibold text-gray-700">Notifiche</span>
            {unreadCount > 0 && (
              <span className="text-[11px] font-medium text-blue-600">{unreadCount} nuove</span>
            )}
          </div>

          <div className="overflow-y-auto flex-1 divide-y divide-gray-50">
            {notifications.length === 0 ? (
              <p className="px-4 py-6 text-sm text-gray-400 text-center">Nessuna notifica</p>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => {
                    setOpen(false)
                    onOpen?.(n)
                  }}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-all ${n.unread ? 'bg-blue-50/50' : ''}`}
                >
                  <div className="flex items-start gap-2">
                    {n.unread && <span className="mt-1.5 w-2 h-2 shrink-0 rounded-full bg-blue-500" />}
                    <div className={`min-w-0 ${n.unread ? '' : 'pl-4'}`}>
                      <p className="text-sm font-medium text-gray-800 truncate">{n.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                      <p className="text-[11px] text-gray-400 mt-1">{formatNotificationDate(n.created_at)}</p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>

          {unreadCount > 0 && (
            <button
              type="button"
              onClick={() => onReadAll?.()}
              className="px-4 py-2.5 text-xs font-medium text-gray-600 border-t border-gray-100 hover:bg-gray-50 transition-all"
            >
              Segna tutte come lette
            </button>
          )}
        </div>
      )}
    </div>
  )
}
