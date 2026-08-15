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

export async function fetchCistern(baseUrl) {
  const url = baseUrl || getSettings().bayesianUrl
  const res = await fetchWithTimeout(`${url}/api/cistern`)
  if (!res.ok) throw new Error(`cistern fetch failed: ${res.status}`)
  return res.json()
}

export async function refillCistern(baseUrl) {
  const url = baseUrl || getSettings().bayesianUrl
  const res = await fetchWithTimeout(`${url}/api/cistern/refill`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`cistern refill failed: ${res.status}`)
  return res.json()
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

export async function fetchFirmwareVersion() {
  const { bayesianUrl } = getSettings()
  const res = await fetchWithTimeout(`${bayesianUrl}/api/esp/version`)
  if (!res.ok) throw new Error(`Firmware version fetch failed: ${res.status}`)
  const data = await res.json()
  return data.version || '-'
}

export function uploadFirmware(file, onProgress) {
  const { bayesianUrl } = getSettings()
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append('file', file)

    xhr.open('POST', `${bayesianUrl}/api/esp/ota`)
    xhr.upload.addEventListener('progress', (evt) => {
      if (evt.lengthComputable && onProgress) {
        onProgress(Math.round((evt.loaded / evt.total) * 100))
      }
    })
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100)
        resolve(JSON.parse(xhr.responseText || '{"status":"ok"}'))
      } else {
        let msg = `Upload failed: ${xhr.status}`
        try {
          const body = JSON.parse(xhr.responseText)
          if (body.detail) msg = body.detail
        } catch (e) { /* keep default */ }
        reject(new Error(msg))
      }
    })
    xhr.addEventListener('error', () => reject(new Error('Network error during upload')))
    xhr.send(form)
  })
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

export async function fetchAuditLog({ filter = '', category = null, limit = 200, startDate = null, endDate = null } = {}) {
  const { bayesianUrl } = getSettings()
  const params = new URLSearchParams()
  if (filter) params.set('filter', filter)
  if (category) params.set('category', category)
  if (limit) params.set('limit', String(limit))
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  const qs = params.toString()
  const url = `${bayesianUrl}/api/audit-log${qs ? '?' + qs : ''}`
  const res = await fetchWithTimeout(url)
  if (!res.ok) throw new Error(`Audit log failed: ${res.status}`)
  return res.json()
}

export async function deleteAuditLog({ startDate = null, endDate = null } = {}) {
  const { bayesianUrl } = getSettings()
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  const qs = params.toString()
  const url = `${bayesianUrl}/api/audit-log${qs ? '?' + qs : ''}`
  const res = await fetchWithTimeout(url, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Audit log delete failed: ${res.status}`)
  return res.json()
}

export async function exportAuditLogCsv({ filter = '', category = null, startDate = null, endDate = null } = {}) {
  const { bayesianUrl } = getSettings()
  const params = new URLSearchParams()
  if (filter) params.set('filter', filter)
  if (category) params.set('category', category)
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  const qs = params.toString()
  const url = `${bayesianUrl}/api/audit-log/export${qs ? '?' + qs : ''}`
  const res = await fetchWithTimeout(url)
  if (!res.ok) throw new Error(`Audit log export failed: ${res.status}`)
  return { blob: await res.blob(), contentDisposition: res.headers.get('content-disposition') || '' }
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