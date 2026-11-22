import { useState } from 'react'

import {
  Badge,
  Empty,
  ErrorNote,
  Loading,
  Panel,
  categoryLabel,
  formatRefs,
  severityLabel,
  severityTone,
} from '../components/ui'
import { useApi } from '../hooks/useApi'

// Журнал импорта: что приняли, что отбраковали и почему.
export default function ImportLog({ initialImportId }) {
  const { data: sources, loading: sourcesLoading, error: sourcesError } = useApi('/sources')

  const [importId, setImportId] = useState(initialImportId ?? 1)
  const path = `/imports/${importId}/log`
  const { data: log, loading, error } = useApi(path)

  if (sourcesLoading) return <Loading />
  if (sourcesError) return <ErrorNote message={sourcesError} />

  return (
    <Panel
      title="Журнал импорта"
      actions={
        <select
          value={importId}
          onChange={(event) => setImportId(Number(event.target.value))}
        >
          {sources.map((source) => (
            <option key={source.id} value={source.id}>
              {source.id} — {source.name}
            </option>
          ))}
        </select>
      }
    >
      {loading && <Loading />}
      {error && <ErrorNote message={error} />}

      {log && log.issues.length === 0 && (
        <Empty>Все строки источника приняты без замечаний.</Empty>
      )}

      {log && log.issues.length > 0 && (
        <table className="data">
          <thead>
            <tr>
              <th>Категория</th>
              <th>Код</th>
              <th>Критичность</th>
              <th>Сообщение</th>
              <th>Строки</th>
            </tr>
          </thead>
          <tbody>
            {log.issues.map((issue, index) => (
              <tr key={index}>
                <td>{categoryLabel(issue.category)}</td>
                <td>
                  <code className="mono">{issue.code}</code>
                </td>
                <td>
                  <Badge tone={severityTone(issue.severity)}>
                    {severityLabel(issue.severity)}
                  </Badge>
                </td>
                <td>{issue.message}</td>
                <td>{formatRefs(issue.refs)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  )
}
