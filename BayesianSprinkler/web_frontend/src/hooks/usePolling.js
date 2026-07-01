import { useState, useEffect, useCallback } from 'react'
import { fetchEspHealth, fetchDashboard } from '../services/api.js'
import { loadPollingInterval } from '../services/settings.js'

export function useDashboard() {
  const [espData, setEspData] = useState(null)
  const [espHealthy, setEspHealthy] = useState(false)
  const [plantStatuses, setPlantStatuses] = useState([])
  const [weather, setWeather] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const [espRes, dashboardRes] = await Promise.allSettled([
        fetchEspHealth(),
        fetchDashboard(),
      ])

      setEspHealthy(espRes.status === 'fulfilled')

      if (dashboardRes.status === 'fulfilled') {
        setEspData(dashboardRes.value.esp)
        setPlantStatuses(dashboardRes.value.plants || [])
        setWeather(dashboardRes.value.weather)
        setError(null)
      } else {
        setError(dashboardRes.reason?.message || 'Dashboard unavailable')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
    const interval = setInterval(fetch, loadPollingInterval())
    return () => clearInterval(interval)
  }, [fetch])

  return { espData, espHealthy, plantStatuses, weather, error, loading, refetch: fetch }
}
