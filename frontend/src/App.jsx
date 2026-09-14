import { useEffect, useState } from 'react'
import './App.css'
import ThemePicker from './ThemePicker.jsx'

async function api(path, method = 'GET', body) {
  const response = await fetch(`/api${path}`, {
    method, credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Randomz-Request': '1' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your username and password requirements.')
  return data
}

export default function App() {
  const [user, setUser] = useState(null)
  const [result, setResult] = useState(null)
  const [page, setPage] = useState('discover')
  const [auth, setAuth] = useState(null)
  const [favorites, setFavorites] = useState([])
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    let active = true
    // One request chain even in development StrictMode; random draws mutate history.
    async function initialize() {
      try {
        const account = await api('/me')
        if (!active) return
        setUser(account)
        const next = await api('/facts/random', 'POST')
        if (active) {
          setResult(next)
          if (next.fact) {
            try { localStorage.setItem('randomz-last-fact', JSON.stringify(next.fact)) } catch { /* Optional offline copy. */ }
          }
        }
      } catch {
        if (active) {
          try {
            const cached = JSON.parse(localStorage.getItem('randomz-last-fact'))
            if (cached) { setResult({ fact: { ...cached, saved: false } }); setOffline(true) }
          } catch { /* Storage may be unavailable. */ }
          setError('Cannot reach DailyRandomz. Check your connection and that the API is running.')
        }
      } finally { if (active) setBusy(false) }
    }
    initialize()
    return () => { active = false }
  }, [])

  async function act(work) {
    setBusy(true)
    setError('')
    try { await work() } catch (e) { setError(e.message === 'Failed to fetch' ? 'Connection lost. Please try again.' : e.message) }
    finally { setBusy(false) }
  }

  async function draw() {
    const next = await api('/facts/random', 'POST')
    setResult(next)
    setOffline(false)
    if (next.fact) {
      try { localStorage.setItem('randomz-last-fact', JSON.stringify(next.fact)) } catch { /* Optional offline copy. */ }
    }
  }

  async function submitAuth(event) {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget))
    await act(async () => {
      const account = await api(`/auth/${auth}`, 'POST', data)
      setUser(account)
      setAuth(null)
      setPage('discover')
      await draw()
    })
  }

  async function navigate(next) {
    await act(async () => {
      if (next === 'favorites') setFavorites(await api('/favorites'))
      setPage(next)
    })
  }

  async function toggleFavorite(fact) {
    if (!user) { setAuth('register'); return }
    await act(async () => {
      await api(`/favorites/${fact.id}`, fact.saved ? 'DELETE' : 'PUT')
      setResult(previous => previous?.fact?.id === fact.id ? { ...previous, fact: { ...previous.fact, saved: !fact.saved } } : previous)
      if (page === 'favorites') setFavorites(await api('/favorites'))
    })
  }

  const fact = result?.fact
  return (
    <div className="app-shell">
      <header>
        <a className="brand" href="/" aria-label="DailyRandomz home"><span className="brand-mark">✳</span> daily<span>randomz</span><span className="brand-dot">.</span></a>
        <nav aria-label="Main navigation">
          <button disabled={busy} className={page === 'discover' ? 'active' : ''} onClick={() => navigate('discover')}>Discover</button>
          {user && <><button disabled={busy} className={page === 'favorites' ? 'active' : ''} onClick={() => navigate('favorites')}>Favorites</button><button disabled={busy} className={page === 'settings' ? 'active' : ''} onClick={() => navigate('settings')}>Settings</button></>}
          {!user && <button className="sign-in" disabled={busy} onClick={() => setAuth('login')}>Sign in <span aria-hidden="true">↗</span></button>}
          <ThemePicker />
        </nav>
      </header>
      <main>
        <div className="eyebrow"><span /> A LITTLE CURIOSITY, EVERY DAY</div>
        <h1>{page === 'favorites' ? <>Worth keeping<span>.</span></> : page === 'settings' ? <>Make it yours<span>.</span></> : <>Find your next<br /><em>“wait, really?”</em></>}</h1>
        <p className="intro">{page === 'favorites' ? 'Your collection of little discoveries.' : page === 'settings' ? `A little more you. Signed in as ${user?.username}.` : 'Big world. Small discoveries. Start with something you didn’t know.'}</p>
        {error && <div className="notice" role="alert">{error} <button disabled={busy} onClick={() => act(async () => { setUser(await api('/me')); await draw() })}>Retry connection</button></div>}
        {auth && <section className="panel auth" aria-labelledby="auth-title">
          <div className="panel-top"><h2 id="auth-title">{auth === 'register' ? 'Keep your discoveries' : 'Welcome back'}</h2><button aria-label="Close sign in" disabled={busy} onClick={() => setAuth(null)}>✕</button></div>
          <p>Save favorites and remember the facts you’ve already seen.</p>
          <form onSubmit={submitAuth}>
            <label>Username<input name="username" required minLength={3} maxLength={32} pattern="[a-zA-Z0-9_]+" autoComplete="username" autoCapitalize="none" spellCheck="false" /></label>
            <small>3–32 letters, numbers, or underscores.</small>
            <label>Password<input name="password" type="password" required minLength={12} maxLength={128} autoComplete={auth === 'register' ? 'new-password' : 'current-password'} /></label>
            <small>12–128 characters. No email or password recovery in this early version.</small>
            <button className="primary" disabled={busy}>{busy ? 'Please wait…' : auth === 'register' ? 'Create account' : 'Sign in'}</button>
          </form>
          <button className="text-button" disabled={busy} onClick={() => setAuth(auth === 'register' ? 'login' : 'register')}>{auth === 'register' ? 'Already have an account? Sign in' : 'New here? Create an account'}</button>
        </section>}
        {page === 'discover' && <>
          <div className="category-tabs"><span className="selected">✦ Facts</span><span>Quotes <small>SOON</small></span><span>Music <small>SOON</small></span><span>Movies <small>SOON</small></span></div>
          <section className="fact-card" aria-live="polite" aria-busy={busy}>
            <div className="card-meta"><span>{offline ? 'OFFLINE · LAST DISCOVERY' : 'YOUR RANDOM DISCOVERY'}</span><span>{fact?.category || 'FACTS'} <span aria-hidden="true">↗</span></span></div>
            <div className="fact-content"><span className="sparkle" aria-hidden="true">✳</span><h2>{fact?.text || (result?.exhausted ? 'You’ve seen every fact in this collection.' : busy ? 'A little discovery is on its way…' : 'Your next discovery is waiting.')}</h2></div>
            <div className="card-bottom"><span>{result?.exhausted ? 'Reset your history in Settings to explore again.' : 'Something new for your corner of the world.'}</span>{fact && <button disabled={busy || offline} onClick={() => toggleFavorite(fact)} aria-label={fact.saved ? 'Remove from favorites' : 'Save to favorites'} aria-pressed={fact.saved}>{fact.saved ? '♥ Saved' : '♡ Save'}</button>}</div>
          </section>
          <div className="draw-row"><button className="primary" disabled={busy || result?.exhausted} onClick={() => act(draw)}><span aria-hidden="true">⤨</span> {busy ? 'Finding a fact…' : 'Surprise me again'} <span aria-hidden="true">→</span></button><span>Follow your curiosity.</span></div>
          {!user && <p className="guest-note">Always free to explore. <button onClick={() => setAuth('register')}>Make it personal</button> to save favorites and skip repeats.</p>}
        </>}
        {page === 'favorites' && <section className="saved-list" aria-label="Saved facts">{favorites.length ? favorites.map(item => <article className="panel" key={item.id}><small>{item.category}</small><h2>{item.text}</h2><button disabled={busy} onClick={() => toggleFavorite({ ...item, saved: true })}>♥ Remove favorite</button></article>) : <div className="panel"><h2>A home for your favorites.</h2><p>Tap Save on a fact you love to keep it here.</p></div>}</section>}
        {page === 'settings' && user && <section className="panel settings"><label className="check"><input type="checkbox" checked={user.avoid_repeats} disabled={busy} onChange={event => act(async () => { setUser(await api('/settings', 'PATCH', { avoid_repeats: event.target.checked })); setResult(previous => previous?.exhausted ? null : previous) })} /> Avoid facts I’ve already seen</label><p>Your history and favorites stay with your account across devices.</p><button disabled={busy} onClick={() => act(async () => { await api('/history', 'DELETE'); await draw(); setPage('discover') })}>Reset viewing history</button><button disabled={busy} onClick={() => act(async () => { await api('/auth/logout', 'POST'); setUser(null); setFavorites([]); setPage('discover'); setResult(null); await draw() })}>Sign out</button></section>}
      </main>
      <footer><span>A daily dose of unexpected.</span><span>FACTS FIRST. MORE RANDOMZ TO COME. <span aria-hidden="true">✳</span></span></footer>
    </div>
  )
}
