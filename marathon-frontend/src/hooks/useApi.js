import { useCallback, useState } from 'react'

/**
 * Generic data-fetching hook.
 * Returns { data, loading, error, execute }
 * execute(apiFn, ...args) calls apiFn(...args) and manages state.
 */
export function useApi() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const execute = useCallback(async (apiFn, ...args) => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiFn(...args)
      setData(result)
      return result
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'An unexpected error occurred'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, execute, setData }
}
