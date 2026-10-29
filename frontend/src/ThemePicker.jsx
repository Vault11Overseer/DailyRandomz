// THEME PICKER
import { useEffect, useState } from 'react'

export default function ThemePicker() {
  const [preference, setPreference] = useState(() => document.documentElement.dataset.themePreference || 'system')

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    function apply() {
      const theme = preference === 'system' ? (media.matches ? 'dark' : 'light') : preference
      document.documentElement.dataset.theme = theme
      document.documentElement.dataset.themePreference = preference
      document.documentElement.style.colorScheme = theme
      document.querySelector('meta[name="theme-color"]').content = theme === 'dark' ? '#080808' : '#ffffff'
    }
    apply()
    media.addEventListener('change', apply)
    return () => media.removeEventListener('change', apply)
  }, [preference])

  useEffect(() => {
    function sync(event) {
      if (event.key === 'randomz-theme' || event.key === null) {
        setPreference(['light', 'dark'].includes(event.newValue) ? event.newValue : 'system')
      }
    }
    window.addEventListener('storage', sync)
    return () => window.removeEventListener('storage', sync)
  }, [])

  function choose(event) {
    const next = event.target.value
    setPreference(next)
    try { localStorage.setItem('randomz-theme', next) } catch { /* Theme still works when storage is blocked. */ }
  }

  return (
    <label className="theme-picker">
      <span>Theme</span>
      <select value={preference} onChange={choose}>
        <option value="system">System</option>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </label>
  )
}
