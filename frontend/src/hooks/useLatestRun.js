import { useApi } from './useApi'

// Реальный API хранит историю прогонов: берём самый свежий.
// Пока прогонов нет — runId null, страницы спокойно ждут.
export function useLatestRun() {
  const { data: runs, loading, error } = useApi('/reconciliations/')
  const latest = Array.isArray(runs) && runs.length > 0 ? runs[0] : null

  return {
    runId: latest ? latest.run_id : null,
    loading,
    error,
  }
}
