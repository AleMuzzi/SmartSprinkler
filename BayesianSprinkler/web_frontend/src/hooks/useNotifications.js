import { useState, useEffect, useCallback, useRef } from 'react'
import {
  fetchNotifications,
  openNotification,
  readNotification,
  readAllNotifications,
} from '../services/api.js'

/**
 * Poll the server-side notification centre.
 *
 * ``onNew`` is invoked only for entries created after the first successful
 * load (history is never replayed) and only while they are still unread, so
 * opening the portal doesn't re-fire notifications the mobile app already
 * acknowledged.
 */
export function useNotifications({ intervalMs = 15000, onNew } = {}) {
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const onNewRef = useRef(onNew)
  onNewRef.current = onNew
  const lastSeenRef = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const data = await fetchNotifications()
      const list = data.notifications || []
      setNotifications(list)
      setUnreadCount(data.unread_count || 0)
      setError(null)

      const highest = list.reduce((max, n) => Math.max(max, n.id), 0)
      if (lastSeenRef.current === null) {
        lastSeenRef.current = highest
        return
      }
      const fresh = list.filter((n) => n.id > lastSeenRef.current && n.unread)
      lastSeenRef.current = Math.max(lastSeenRef.current, highest)
      if (fresh.length) onNewRef.current?.(fresh)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, intervalMs)
    return () => clearInterval(interval)
  }, [refresh, intervalMs])

  const open = useCallback(async (notification) => {
    await openNotification(notification.id)
    await refresh()
  }, [refresh])

  const read = useCallback(async (notification) => {
    await readNotification(notification.id)
    await refresh()
  }, [refresh])

  const readAll = useCallback(async () => {
    await readAllNotifications()
    await refresh()
  }, [refresh])

  return { notifications, unreadCount, loading, error, refresh, open, read, readAll }
}
