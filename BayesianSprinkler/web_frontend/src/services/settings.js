const DEFAULT_SETTINGS = {
  espUrl: 'http://192.168.1.50',
  bayesianUrl: 'http://localhost:38080',
  pollingInterval: 2000,
  setupCompleted: false,
  useLocation: 'indoor', // 'indoor' | 'outdoor'
  wateringMode: 'automatic', // 'automatic' | 'notification'
  theme: 'system', // 'system' | 'light' | 'dark'
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
    // Merge over the currently stored values so partial saves (e.g. from the
    // Settings panel) never drop unrelated fields such as `setupCompleted`.
    const merged = { ...loadSettings(), ...settings }
    localStorage.setItem('smartsprinkler_settings', JSON.stringify(merged))
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