import { useState } from 'react'

import {
  Badge,
  Empty,
  ErrorNote,
  Loading,
  Panel,
} from '../components/ui'
import { useApi } from '../hooks/useApi'

// Журнал импорта: сводка по загрузке и таблица строк
// (принята / отбракована, причина отбраковки — код ошибки).
export default function ImportLog({ initialImportId }) {
  const { data: batches, loading: batchesLoading, error: batchesError } = useApi('/imports/')
  const { data: sources } = useApi('/sources/')

  const [importId, setImportId] = useState(initialImportId ?? null)
  const selectedId = importId ?? (batches && batches.length ? batches[0].id : null)

  const { data: batch } = useApi(selectedId ? `/imports/${selectedId}` : null)
  const { data: log } = useApi(selectedId ? `/imports/${selectedId}/log` : null)

  if (batchesLoading) return <Loading />
  if (batchesError) return <ErrorNote message={batchesError} />

  const sourceName = (sourceId) => {
    const source = sources?.find((item) => item.id === sourceId)
    return source ? source.name : `источник ${sourceId}`
  }

  return (
    <>
      <Panel
        title="Журнал импорта"
        actions={
          batches && batches.length > 0 ? (
            <select
              value={selectedId ?? ''}
              onChange={(event) => setImportId(Number(event.target.value))}
            >
              {batches.map((item) => (
                <option key={item.id} value={item.id}>
                  №{item.id} — {item.filename} ({sourceName(item.source_id)})
                </option>
              ))}
            </select>
          ) : null
        }
      >
        {!selectedId && <Empty>Загрузок пока нет.</Empty>}

        {batch && (
          <dl className="kv">
            <div className="kv-row">
              <dt>Источник</dt>
              <dd>{sourceName(batch.source_id)}</dd>
            </div>
            <div className="kv-row">
              <dt>Файл</dt>
              <dd>{batch.filename}</dd>
            </div>
            <div className="kv-row">
              <dt>Загружен</dt>
              <dd>{new Date(batch.uploaded_at).toLocaleString('ru-RU')}</dd>
            </div>
            <div className="kv-row">
              <dt>Строк всего</dt>
              <dd>{batch.rows_total}</dd>
            </div>
            <div className="kv-row">
              <dt>Принято</dt>
              <dd>{batch.accepted}</dd>
            </div>
            <div className="kv-row">
              <dt>Отбраковано</dt>
              <dd>{batch.rejected}</dd>
            </div>
          </dl>
        )}
      </Panel>

      {selectedId && (
        <Panel title="Строки файла">
          {!log && <Loading />}
          {log && log.length === 0 && <Empty>Файл пуст.</Empty>}

          {log && log.length > 0 && (
            <table className="data">
              <thead>
                <tr>
                  <th>Строка</th>
                  <th>Статус</th>
                  <th>Причина отбраковки</th>
                </tr>
              </thead>
              <tbody>
                {log.map((row) => (
                  <tr key={row.row_number}>
                    <td>{row.row_number}</td>
                    <td>
                      <Badge tone={row.status === 'accepted' ? 'muted' : 'bad'}>
                        {row.status === 'accepted' ? 'принята' : 'отбракована'}
                      </Badge>
                    </td>
                    <td>
                      {row.reject_reason ? (
                        <code className="mono">{row.reject_reason}</code>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <p className="muted">
            Причины отбраковки: BAD_COLUMN_COUNT — не совпало число колонок,
            NAME_CONFLICT — одинаковые названия с разными инв. номерами,
            INVENTORY_CONFLICT — одинаковые номера с разными названиями,
            DUP_IN_SOURCE — дубль внутри файла, PARENT_REJECTED / NO_PARENT —
            проблемы с «родительским» оборудованием.
          </p>
        </Panel>
      )}
    </>
  )
}
