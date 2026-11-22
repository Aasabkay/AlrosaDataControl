// Единая точка обращения к API. Базовый адрес берётся из переменной
// окружения VITE_API_URL, чтобы фронт работал и с моком, и с настоящим API.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, options)

  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      if (body && body.detail) detail = body.detail
    } catch {
      // тело не JSON — оставляем statusText
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
  // Для файлов Content-Type не задаём: браузер сам поставит multipart-границу.
  upload: (path, formData) => request(path, { method: 'POST', body: formData }),
}
