const DEFAULT_SETTINGS = {
  espUrl: 'http://192.168.1.50:80',
  bayesianUrl: 'http://localhost:38080',
  pollingInterval: 2000,
}

export function loadSettings() {
  try {
    const stored = localStorage.getItem('smartsprinkler_settings')
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
    }
  } catch (e) {
    console.warn('Failed to load settings:', e)
  }
  return DEFAULT_SETTINGS
}

export function saveSettings(settings) {
  try {
    localStorage.setItem('smartsprinkler_settings', JSON.stringify(settings))
  } catch (e) {
    console.warn('Failed to save settings:', e)
  }
}

export function loadPollingInterval() {
  const settings = loadSettings()
  return settings.pollingInterval
}

export function savePollingInterval(interval) {
  const settings = loadSettings()
  settings.pollingInterval = interval
  saveSettings(settings)
}