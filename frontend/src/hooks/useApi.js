import { useEffect, useState } from 'react'
import { api } from '../api'

// Загрузка данных: запрос выполняется при монтировании и при смене path.
// path может быть null — тогда запрос не выполняется (ждём, например, run_id).
export function useApi(path) {
  const [state, setState] = useState({ data: null, loading: Boolean(path), error: null })

  useEffect(() => {
    if (!path) {
      setState({ data: null, loading: false, error: null })
      return
    }

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
