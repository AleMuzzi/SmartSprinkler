import { test } from 'node:test'
import assert from 'node:assert/strict'

import { resolveHealth } from './health.js'

const fulfilled = (value) => ({ status: 'fulfilled', value })
const rejected = (reason = new Error('network down')) => ({ status: 'rejected', reason })

const previous = () => ({
  espData: { air_temperature: '21.0' },
  weather: { cloud_cover: 'clear' },
  waterLowAlert: false,
  espHealthy: false,
  serverHealthy: false,
  error: null,
})

test('everything green: both badges online, dashboard wins', () => {
  const next = resolveHealth(previous(), {
    espHealth: fulfilled({ status: 'ok' }),
    espStatus: fulfilled({ air_temperature: '9.9', water_low_alert: 'off' }),
    dashboard: fulfilled({
      esp: { air_temperature: '33.0' },
      weather: { cloud_cover: 'cloudy' },
      water_low_alert: 'off',
    }),
  })

  assert.equal(next.espHealthy, true)
  assert.equal(next.serverHealthy, true)
  assert.equal(next.error, null)
  assert.equal(next.espData.air_temperature, '33.0')
  assert.equal(next.weather.cloud_cover, 'cloudy')
  assert.equal(next.waterLowAlert, false)
})

test('server badge follows the dashboard, not the ESP health probe', () => {
  const next = resolveHealth(previous(), {
    espHealth: rejected(),
    espStatus: fulfilled({ air_temperature: '21.0', water_low_alert: 'on' }),
    dashboard: fulfilled({ esp: {}, weather: null, water_low_alert: 'on' }),
  })

  assert.equal(next.espHealthy, false)
  assert.equal(next.serverHealthy, true)
  assert.equal(next.waterLowAlert, true)
})

test('dashboard down while the ESP still answers: server offline, no error', () => {
  const next = resolveHealth(previous(), {
    espHealth: fulfilled({ status: 'ok' }),
    espStatus: fulfilled({ air_temperature: '19.5', water_low_alert: 'off' }),
    dashboard: rejected(),
  })

  assert.equal(next.serverHealthy, false)
  assert.equal(next.espHealthy, true)
  assert.equal(next.error, null)
  // Fallback data comes straight from the ESP snapshot.
  assert.equal(next.espData.air_temperature, '19.5')
  assert.equal(next.weather, null)
})

test('no source at all: error raised and last known values preserved', () => {
  const stale = { ...previous(), waterLowAlert: true }

  const next = resolveHealth(stale, {
    espHealth: rejected(),
    espStatus: rejected(),
    dashboard: rejected(),
  })

  assert.equal(next.serverHealthy, false)
  assert.equal(next.espHealthy, false)
  assert.notEqual(next.error, null)
  assert.equal(next.espData, stale.espData)
  assert.equal(next.weather, stale.weather)
  // A water-low alert must never be cleared by a network failure.
  assert.equal(next.waterLowAlert, true)
})

test('water_low_alert accepts both the string and boolean spellings', () => {
  const base = { ...previous(), waterLowAlert: false }

  assert.equal(
    resolveHealth(base, {
      espHealth: fulfilled({}),
      espStatus: rejected(),
      dashboard: fulfilled({ esp: {}, water_low_alert: true }),
    }).waterLowAlert,
    true,
  )
  assert.equal(
    resolveHealth(base, {
      espHealth: fulfilled({}),
      espStatus: rejected(),
      dashboard: fulfilled({ esp: {}, water_low_alert: 'on' }),
    }).waterLowAlert,
    true,
  )
  assert.equal(
    resolveHealth({ ...previous(), waterLowAlert: true }, {
      espHealth: fulfilled({}),
      espStatus: rejected(),
      dashboard: fulfilled({ esp: {}, water_low_alert: 'off' }),
    }).waterLowAlert,
    false,
  )
})

test('a missing dashboard payload never crashes the reducer', () => {
  const next = resolveHealth(previous(), {
    espHealth: fulfilled({}),
    espStatus: rejected(),
    dashboard: fulfilled(undefined),
  })

  assert.equal(next.serverHealthy, true)
  assert.deepEqual(next.espData, {})
  assert.equal(next.weather, null)
  assert.equal(next.error, null)
})
