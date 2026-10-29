// Header health indicators, derived from the three requests `useEspData`
// fires on every poll. Pure and React-free on purpose: `node --test` covers
// it directly, so the badges can never silently go stale again.
//
// Each argument is a `Promise.allSettled` result: `{status: 'fulfilled',
// value}` or `{status: 'rejected'}`. `allSettled` never rejects, which is
// exactly why the old code (a `catch` around it) reported the server as
// online forever.

/**
 * @param {{espData: object|null, weather: object|null, waterLowAlert: boolean,
 *          espHealthy: boolean, serverHealthy: boolean, error: string|null}} previous
 * @param {{espHealth: object, espStatus: object, dashboard: object}} results
 */
export function resolveHealth(previous, { espHealth, espStatus, dashboard }) {
  const next = {
    // Unknown values keep their last known state: a transient failure must
    // not clear the water-low alert or blank the telemetry.
    espData: previous.espData,
    weather: previous.weather,
    waterLowAlert: previous.waterLowAlert,
    espHealthy: espHealth.status === 'fulfilled',
    // The dashboard comes from the Bayesian/SmartSprinkler server, so its
    // outcome is the only honest signal for this badge.
    serverHealthy: dashboard.status === 'fulfilled',
    error: null,
  }

  if (dashboard.status === 'fulfilled') {
    // Preferred source: server-resolved dashboard, which merges the web
    // forecast when the DHT reports -1.
    const payload = dashboard.value || {}
    next.espData = payload.esp || {}
    next.weather = payload.weather || null
    next.waterLowAlert =
      payload.water_low_alert === 'on' || payload.water_low_alert === true
  } else if (espStatus.status === 'fulfilled') {
    // Fallback: raw ESP snapshot when the server is unreachable.
    const payload = espStatus.value || {}
    next.espData = payload
    next.weather = null
    next.waterLowAlert = payload.water_low_alert === 'on'
  } else {
    // No source produced data: everything the panel would render is unknown.
    next.error = 'No data source reachable'
  }

  return next
}
