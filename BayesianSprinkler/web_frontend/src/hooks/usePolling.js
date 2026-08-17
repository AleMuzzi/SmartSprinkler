import { useState, useEffect, useCallback } from 'react'
import { fetchEspStatus, fetchEspHealth, fetchDashboard, fetchBayesianPlantStatus, fetchCistern, refillCistern } from '../services/api.js'

export function useEspData() {
  const [espData, setEspData] = useState(null)
  const [weather, setWeather] = useState(null)
  const [espHealthy, setEspHealthy] = useState(false)
  const [waterLowAlert, setWaterLowAlert] = useState(false)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const [healthRes, statusRes, dashRes] = await Promise.allSettled([
        fetchEspHealth(),
        fetchEspStatus(),
        fetchDashboard(),
      ])

      setEspHealthy(healthRes.status === 'fulfilled')

      // Preferred source: the server-resolved dashboard, which already
      // merges the web forecast (with source flags) when the DHT reports -1.
      if (dashRes.status === 'fulfilled') {
        setEspData(dashRes.value.esp || {})
        setWeather(dashRes.value.weather || null)
        setWaterLowAlert(
          dashRes.value.water_low_alert === 'on' ||
          dashRes.value.water_low_alert === true,
        )
        setError(null)
      } else if (statusRes.status === 'fulfilled') {
        // Fallback: raw ESP snapshot when the Bayesian server is unreachable.
        setEspData(statusRes.value)
        setWeather(null)
        setWaterLowAlert(statusRes.value.water_low_alert === 'on')
        setError(null)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
    const interval = setInterval(fetch, 10000)
    return () => clearInterval(interval)
  }, [fetch])

  return { espData, weather, espHealthy, waterLowAlert, error, loading, refetch: fetch }
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
