import { useState } from 'react'

import { api } from '../api'
import { Panel, Loading, ErrorNote, Empty } from '../components/ui'
import { useApi } from '../hooks/useApi'

// Экран загрузки. Пока работает мок: файл уходит на POST /imports,
// сервер отвечает номером загрузки, но разбор пока делает настоящий API.
export default function Upload({ onOpenLog }) {
  const { data: sources, loading, error } = useApi('/sources')

  const [sourceId, setSourceId] = useState('1')
  const [file, setFile] = useState(null)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState(null)
  const [sendError, setSendError] = useState(null)

  if (loading) return <Loading />
  if (error) return <ErrorNote message={error} />

  async function handleSubmit(event) {
    event.preventDefault()
    setSending(true)
    setSendError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('source_id', sourceId)
    formData.append('batch_id', '1')
    if (file) formData.append('file', file)

    try {
      const data = await api.upload('/imports', formData)
      setResult(data)
    } catch (requestError) {
      setSendError(requestError.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <Panel title="Загрузка файла источника">
      <form onSubmit={handleSubmit} className="upload-form">
        <label>
          Источник
          <select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.id} — {source.name}
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

        <button className="primary" type="submit" disabled={sending}>
          {sending ? 'Загрузка…' : 'Загрузить'}
        </button>
      </form>

      {sendError && <ErrorNote message={sendError} />}

      {result && (
        <div className="success-note">
          Загрузка принята, номер загрузки (batch_id): <b>{result.batch_id ?? result.import_id}</b>.{' '}
          <button
            className="link"
            type="button"
            onClick={() => onOpenLog(result.batch_id ?? result.import_id)}
          >
            Открыть журнал импорта
          </button>
          <p className="muted">
            Файл разобран: принято строк {result.records_accepted} из {result.rows_total},
            ошибок разбора {result.issues_count}.
          </p>
        </div>
      )}

      <Empty>
        После загрузки откройте «Журнал импорта», чтобы увидеть принятые и
        отбракованные строки.
      </Empty>
    </Panel>
  )
}
