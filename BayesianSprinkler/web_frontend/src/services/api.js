import { loadSettings } from './settings.js'

const TIMEOUT = 5000

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), TIMEOUT)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    clearTimeout(id)
    return res
  } catch (e) {
    clearTimeout(id)
    throw e
  }
}

export function getSettings() {
  return loadSettings()
}

export async function fetchEspStatus() {
  const { espUrl } = getSettings()
  const res = await fetchWithTimeout(`${espUrl}/status`)
  if (!res.ok) throw new Error(`ESP status failed: ${res.status}`)
  return res.json()
}

export async function fetchEspHealth() {
  const { espUrl } = getSettings()
  const res = await fetchWithTimeout(`${espUrl}/health`)
  if (!res.ok) throw new Error(`ESP health failed: ${res.status}`)
  return res.json()
}

export async function sendEspCommand(action, target, extra = {}) {
  const { espUrl } = getSettings()
  const body = { action, target }
  if (extra.amount !== undefined) body.amount = extra.amount
  if (extra.force) body.force = true
  const res = await fetchWithTimeout(`${espUrl}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`ESP command failed: ${res.status}`)
  return res.json()
}

export async function fetchBayesianHealth() {
  const { bayesianUrl } = getSettings()
  const res = await fetchWithTimeout(`${bayesianUrl}/api/health`)
  if (!res.ok) throw new Error(`Bayesian health failed: ${res.status}`)
  return res.json()
}

export async function fetchBayesianPlantStatus() {
  const { bayesianUrl } = getSettings()
  const res = await fetchWithTimeout(`${bayesianUrl}/api/plants/status`)
  if (!res.ok) throw new Error(`Bayesian plant status failed: ${res.status}`)
  return res.json()
}

export async function fetchBayesianWeatherStatus() {
  const { bayesianUrl } = getSettings()
  const res = await fetchWithTimeout(`${bayesianUrl}/api/weather/status`)
  if (!res.ok) throw new Error(`Bayesian weather status failed: ${res.status}`)
  return res.json()
}

export async function fetchDashboard() {
  const { bayesianUrl } = getSettings()
  const res = await fetchWithTimeout(`${bayesianUrl}/api/dashboard`)
  if (!res.ok) throw new Error(`Dashboard failed: ${res.status}`)
  return res.json()
}

export async function sendBayesianManualWater(plantType) {
  const { bayesianUrl } = getSettings()
  const res = await fetchWithTimeout(`${bayesianUrl}/api/plants/manual-water`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plant_type: plantType }),
  })
  if (!res.ok) throw new Error(`Bayesian manual water failed: ${res.status}`)
  return res.json()
}

export const PLANTS = [
  { id: 'habanero', label: 'Habanero' },
  { id: 'naga_morich', label: 'Naga Morich' },
  { id: 'carolina_reaper', label: 'Carolina Reaper' },
  { id: 'rosmarino', label: 'Rosmarino' },
]