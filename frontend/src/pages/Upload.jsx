import { useMemo, useState } from 'react'

import { api } from '../api'
import { Panel, Loading, ErrorNote, Empty, Badge } from '../components/ui'
import { useApi } from '../hooks/useApi'



export default function Upload({ onOpenLog, onOpenDashboard }) {
  const { data: sources, loading, error } = useApi('/sources/')
  const {
    data: batches,
    loading: batchesLoading,
    reload: reloadBatches,
  } = useApi('/imports/')

  const [sourceId, setSourceId] = useState(null)
  const [file, setFile] = useState(null)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState(null)
  const [sendError, setSendError] = useState(null)

  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)
  const [runError, setRunError] = useState(null)

  const selectedSourceId = sourceId ?? (sources && sources.length ? sources[0].id : null)


  const latestBySource = useMemo(() => {
    const map = new Map()
    for (const batch of batches ?? []) {
      if (!map.has(batch.source_id)) map.set(batch.source_id, batch)
    }
    return [...map.values()].sort((a, b) => a.source_id - b.source_id)
  }, [batches])

  if (loading) return <Loading />
  if (error) return <ErrorNote message={error} />

  const sourceName = (id) => {
    const source = sources.find((item) => item.id === id)
    return source ? source.name : `источник ${id}`
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!file || !selectedSourceId) return

    setSending(true)
    setSendError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('source_id', selectedSourceId)
    formData.append('file', file)

    try {
      const data = await api.upload('/imports/', formData)
      setResult(data)
      setFile(null)
      event.target.reset()
      reloadBatches()
    } catch (requestError) {
      setSendError(requestError.message)
    } finally {
      setSending(false)
    }
  }

  async function handleReconcile() {
    setRunning(true)
    setRunError(null)
    setRunResult(null)

    try {
      const data = await api.post('/reconciliations/', {
        batch_ids: latestBySource.map((batch) => batch.id),
      })


      const report = await api.get(`/reconciliations/${data.run_id}`)
      setRunResult({ ...data, issues_total: report.summary.issues_total })
    } catch (requestError) {
      setRunError(requestError.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <Panel title="Загрузка файла источника">
        <form onSubmit={handleSubmit} className="upload-form">
          <label>
            Источник
            <select
              value={selectedSourceId ?? ''}
              onChange={(event) => setSourceId(Number(event.target.value))}
            >
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Файл (CSV или XLSX)
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => setFile(event.target.files[0] ?? null)}
            />
          </label>

          <button className="primary" type="submit" disabled={sending || !file}>
            {sending ? 'Загрузка…' : 'Загрузить'}
          </button>
        </form>

        {sendError && <ErrorNote message={sendError} />}

        {result && (
          <div className="success-note">
            Загрузка принята, номер загрузки (batch_id): <b>{result.batch_id}</b>.{' '}
            <button className="link" type="button" onClick={() => onOpenLog(result.batch_id)}>
              Открыть журнал импорта
            </button>
            <p className="muted">
              Файл разобран: принято строк {result.records_accepted} из {result.rows_total},
              ошибок разбора {result.issues_count}.
            </p>
          </div>
        )}

        <Empty>
          Загрузите по одному файлу от каждого источника, затем запустите сверку.
        </Empty>
      </Panel>

      <Panel title="Запуск сверки">
        {batchesLoading && <Loading />}

        {!batchesLoading && latestBySource.length === 0 && (
          <Empty>Загрузок пока нет — сначала загрузите файлы.</Empty>
        )}

        {!batchesLoading && latestBySource.length > 0 && (
          <>
            <p className="muted">
              Будут сверены последние загрузки по каждому источнику:
            </p>
            <table className="data">
              <thead>
                <tr>
                  <th>Источник</th>
                  <th>Файл</th>
                  <th>Строк</th>
                  <th>Принято</th>
                  <th>Отбраковано</th>
                </tr>
              </thead>
              <tbody>
                {latestBySource.map((batch) => (
                  <tr key={batch.id}>
                    <td>{sourceName(batch.source_id)}</td>
                    <td>{batch.filename}</td>
                    <td>{batch.rows_total}</td>
                    <td>{batch.accepted}</td>
                    <td>{batch.rejected}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="controls">
              <button
                className="primary"
                type="button"
                disabled={running || latestBySource.length < 2}
                onClick={handleReconcile}
              >
                {running ? 'Сверка…' : 'Запустить сверку'}
              </button>
              {latestBySource.length < 2 && (
                <span className="muted">нужно минимум два источника</span>
              )}
            </div>
          </>
        )}

        {runError && <ErrorNote message={runError} />}

        {runResult && (
          <div className="success-note">
            <Badge tone="muted">прогон {runResult.run_id}</Badge>{' '}
            Сверка завершена: активов {runResult.assets_total}, ошибок {runResult.issues_total}.{' '}
            <button className="link" type="button" onClick={onOpenDashboard}>
              Открыть дашборд
            </button>
          </div>
        )}
      </Panel>
    </>
  )
}
