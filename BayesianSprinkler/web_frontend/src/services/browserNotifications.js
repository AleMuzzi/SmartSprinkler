// Thin wrapper around the browser Notification API so unsupported or
// permission-denied browsers degrade to the in-app toast alone.

export function hasNotificationApi() {
  return typeof window !== 'undefined' && 'Notification' in window
}

export async function requestNotificationPermission() {
  if (!hasNotificationApi()) return 'denied'
  if (Notification.permission !== 'default') return Notification.permission
  try {
    return await Notification.requestPermission()
  } catch (e) {
    return Notification.permission
  }
}

export function raiseBrowserNotification({ title, body, tag, onClick }) {
  if (!hasNotificationApi() || Notification.permission !== 'granted') return null
  try {
    const notification = new Notification(title, { body, icon: '/favicon.png', tag })
    if (onClick) {
      notification.onclick = () => {
        window.focus()
        notification.close()
        onClick()
      }
    }
    return notification
  } catch (e) {
    return null
  }
}
