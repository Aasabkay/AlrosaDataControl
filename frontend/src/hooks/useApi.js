import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'




export function useApi(path) {
  const [state, setState] = useState({ data: null, loading: Boolean(path), error: null })
  const [tick, setTick] = useState(0)

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
  }, [path, tick])

  const reload = useCallback(() => setTick((value) => value + 1), [])

  return { ...state, reload }
}
