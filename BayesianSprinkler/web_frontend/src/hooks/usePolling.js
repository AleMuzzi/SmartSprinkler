import { useState, useEffect, useCallback } from 'react'
import { fetchEspStatus, fetchEspHealth, fetchDashboard, fetchBayesianPlantStatus, fetchCistern, refillCistern } from '../services/api.js'
import { resolveHealth } from '../services/health.js'

const INITIAL_HEALTH = {
  espData: null,
  weather: null,
  waterLowAlert: false,
  espHealthy: false,
  serverHealthy: false,
  error: null,
}

export function useEspData() {
  const [health, setHealth] = useState(INITIAL_HEALTH)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const [espHealth, espStatus, dashboard] = await Promise.allSettled([
        fetchEspHealth(),
        fetchEspStatus(),
        fetchDashboard(),
      ])
      setHealth((previous) =>
        resolveHealth(previous, { espHealth, espStatus, dashboard }),
      )
    } catch (e) {
      setHealth((previous) => ({ ...previous, error: e.message }))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
    const interval = setInterval(fetch, 10000)
    return () => clearInterval(interval)
  }, [fetch])

  return {
    espData: health.espData,
    weather: health.weather,
    espHealthy: health.espHealthy,
    serverHealthy: health.serverHealthy,
    waterLowAlert: health.waterLowAlert,
    error: health.error,
    loading,
    refetch: fetch,
  }
}

export function usePlantStatuses() {
  const [plantStatuses, setPlantStatuses] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const res = await fetchBayesianPlantStatus()
      setPlantStatuses(res.plants || [])
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
    const interval = setInterval(fetch, 30000)
    return () => clearInterval(interval)
  }, [fetch])

  return { plantStatuses, error, loading, refetch: fetch }
}

export function useCisternStatus(baseUrl, intervalMs = 30000) {
  const [cistern, setCistern] = useState({
    levelMl: null,
    capacityMl: null,
    levelPct: null,
    waterLowAlert: false,
  })
  const [cisternError, setCisternError] = useState(null)

  const fetch = useCallback(async () => {
    try {
      const data = await fetchCistern(baseUrl)
      setCistern({
        levelMl: data.level_ml,
        capacityMl: data.capacity_ml,
        levelPct: data.level_pct,
        waterLowAlert: data.water_low_alert,
      })
      setCisternError(null)
    } catch (e) {
      setCisternError(e.message)
    }
  }, [baseUrl])

  useEffect(() => {
    fetch()
    const interval = setInterval(fetch, intervalMs)
    return () => clearInterval(interval)
  }, [fetch, intervalMs])

  const refill = useCallback(async () => {
    await refillCistern(baseUrl)
    await fetch()
  }, [baseUrl, fetch])

  return { cistern, refill, refetch: fetch, cisternError }
}
