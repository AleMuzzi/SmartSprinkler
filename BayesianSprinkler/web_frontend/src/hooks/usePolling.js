import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchEspStatus, fetchBayesianPlantStatus, fetchBayesianWeatherStatus, fetchEspHealth, fetchBayesianHealth } from '../services/api.js'
import { loadPollingInterval } from '../services/settings.js'

export function useEspStatus() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const result = await fetchEspStatus()
      setData(result)
      setError(null)
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

  return { data, error, loading, refetch: fetch }
}

export function useBayesianStatus() {
  const [plantStatuses, setPlantStatuses] = useState([])
  const [weather, setWeather] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    try {
      const [plantsRes, weatherRes] = await Promise.all([
        fetchBayesianPlantStatus(),
        fetchBayesianWeatherStatus().catch(() => null),
      ])
      setPlantStatuses(plantsRes.plants || [])
      setWeather(weatherRes)
      setError(null)
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

  return { plantStatuses, weather, error, loading, refetch: fetch }
}

export function useHealthChecks() {
  const [espHealthy, setEspHealthy] = useState(false)
  const [bayesianHealthy, setBayesianHealthy] = useState(false)
  const [loading, setLoading] = useState(true)

  const check = useCallback(async () => {
    setLoading(true)
    const [esp, bayesian] = await Promise.allSettled([
      fetchEspHealth().then(() => true),
      fetchBayesianHealth().then(() => true),
    ])
    setEspHealthy(esp.status === 'fulfilled')
    setBayesianHealthy(bayesian.status === 'fulfilled')
    setLoading(false)
  }, [])

  useEffect(() => {
    check()
    const interval = setInterval(check, loadPollingInterval())
    return () => clearInterval(interval)
  }, [check])

  return { espHealthy, bayesianHealthy, loading, refetch: check }
}