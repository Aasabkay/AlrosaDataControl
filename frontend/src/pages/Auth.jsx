import { useState } from 'react'

import { api } from '../api'
import { ErrorNote } from '../components/ui'

export default function Auth({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)

    try {
      if (mode === 'register') await api.register(login, password)
      await api.login(login, password)
      onAuthenticated()
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <h1>Сверка ИТ-активов</h1>
        <p className="muted">прототип контроля данных об ИТ-оборудовании</p>

        <div className="auth-tabs">
          <button
            type="button"
            className={mode === 'login' ? 'active' : ''}
            onClick={() => { setMode('login'); setError(null) }}
          >
            Вход
          </button>
          <button
            type="button"
            className={mode === 'register' ? 'active' : ''}
            onClick={() => { setMode('register'); setError(null) }}
          >
            Регистрация
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            Логин
            <input
              value={login}
              onChange={(event) => setLogin(event.target.value)}
              autoComplete="username"
            />
          </label>
          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            />
          </label>

          {error && <ErrorNote message={error} />}

          <button className="primary" type="submit" disabled={busy || !login || !password}>
            {busy
              ? 'Подождите…'
              : mode === 'register'
                ? 'Зарегистрироваться и войти'
                : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}
