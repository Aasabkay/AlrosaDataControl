const BASE_URL =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')

const TOKEN_KEY = 'alrosa_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers)
  const token = getToken()

  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (response.status === 401 && token && path !== '/auth/login') {
    clearToken()
    window.dispatchEvent(new Event('auth:unauthorized'))
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (body && body.detail) detail = body.detail
    } catch {

    }
    throw new Error(`Ошибка API (${response.status}): ${detail}`)
  }

  const contentType = response.headers.get('content-type') ?? ''
  return contentType.includes('application/json') ? response.json() : response
}

export const api = {
  baseUrl: BASE_URL,
  get: (path) => request(path),
  post: (path, body) =>
    request(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  upload: (path, formData) => request(path, { method: 'POST', body: formData }),

  register: (login, password) =>
    request('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, password }),
    }),

  login: async (login, password) => {
    const form = new URLSearchParams()
    form.append('username', login)
    form.append('password', password)

    const data = await request('/auth/login', { method: 'POST', body: form })
    setToken(data.access_token)
    return data
  },

  logout: clearToken,
}
