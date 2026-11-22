import { useEffect, useState } from 'react'
import { api } from '../api'

// Загрузка данных: запрос выполняется при монтировании и при смене path.
// Возвращает { data, loading, error } — одинаковый контракт для всех страниц.
export function useApi(path) {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  useEffect(() => {
    let alive = true
    setState({ data: null, loading: true, error: null })

    api
      .get(path)
      .then((data) => {
        if (alive) setState({ data, loading: false, error: null })
      })
      .catch((error) => {
        if (alive) setState({ data: null, loading: false, error: error.message })
      })

    return () => {
      alive = false
    }
  }, [path])

  return state
}
