



const BASE_URL =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, options)

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
}
