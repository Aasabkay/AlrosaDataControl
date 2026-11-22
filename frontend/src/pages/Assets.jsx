import { useEffect, useState } from 'react'

import {
  Badge,
  Empty,
  ErrorNote,
  Loading,
  Panel,
  Values,
  categoryLabel,
  severityLabel,
  severityTone,
} from '../components/ui'
import { useApi } from '../hooks/useApi'
import { useLatestRun } from '../hooks/useLatestRun'

const FIELDS = [
  ['name', 'Наименование'],
  ['asset_type', 'Тип'],
  ['manufacturer', 'Производитель'],
  ['model', 'Модель'],
  ['inventory_number', 'Инв. номер'],
  ['serial_number', 'Серийный номер'],
  ['location', 'Местоположение'],
  ['status', 'Состояние'],
  ['responsible_person', 'Ответственный'],
]

export default function Assets({ selectedAssetKey }) {
  const { runId } = useLatestRun()
  const { data: assets, loading, error } = useApi(
    runId ? `/reconciliations/${runId}/assets` : null
  )
  const [selectedKey, setSelectedKey] = useState(null)

  // Выбор из другой вкладки (например, по клику на актив в списке ошибок).
  useEffect(() => {
    if (selectedAssetKey) setSelectedKey(selectedAssetKey)
  }, [selectedAssetKey])

  const detailPath =
    runId && selectedKey
      ? `/reconciliations/${runId}/assets/${encodeURIComponent(selectedKey)}`
      : null
  const { data: detail, loading: detailLoading, error: detailError } = useApi(detailPath)

  return (
    <>
      <Panel title="Активы">
        {loading && <Loading />}
        {error && <ErrorNote message={error} />}

        {assets && (
          <table className="data">
            <thead>
              <tr>
                <th>Наименование</th>
                <th>Тип</th>
                <th>Инв. номер</th>
                <th>Серийный номер</th>
                <th>Модель</th>
                <th>Источники</th>
                <th>Примечания</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => (
                <tr
                  key={asset.asset_key}
                  className={asset.asset_key === selectedKey ? 'selected' : 'clickable'}
                  onClick={() => setSelectedKey(asset.asset_key)}
                >
                  <td>{asset.name ?? '—'}</td>
                  <td>{asset.asset_type ?? '—'}</td>
                  <td>{asset.inventory_number ?? '—'}</td>
                  <td>{asset.serial_number ?? '—'}</td>
                  <td>{asset.model ?? '—'}</td>
                  <td>{asset.sources.join(', ')}</td>
                  <td>{asset.notes.join('; ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      {selectedKey && (
        <Panel title={`Актив: ${selectedKey}`}>
          {detailLoading && <Loading />}
          {detailError && <ErrorNote message={detailError} />}

          {detail && (
            <>
              <dl className="kv">
                {FIELDS.map(([field, label]) => (
                  <div key={field} className="kv-row">
                    <dt>{label}</dt>
                    <dd>{detail.asset[field] ?? '—'}</dd>
                  </div>
                ))}
                <div className="kv-row">
                  <dt>Источники</dt>
                  <dd>{detail.asset.sources.join(', ')}</dd>
                </div>
                <div className="kv-row">
                  <dt>Примечания</dt>
                  <dd>{detail.asset.notes.join('; ') || '—'}</dd>
                </div>
              </dl>

              <h3 className="sub-title">Замечания по активу</h3>
              {detail.issues.length === 0 ? (
                <Empty>Замечаний нет: источники согласованы.</Empty>
              ) : (
                <table className="data">
                  <thead>
                    <tr>
                      <th>Код</th>
                      <th>Поле</th>
                      <th>Сообщение</th>
                      <th>Значения по источникам</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.issues.map((issue, index) => (
                      <tr key={index}>
                        <td>
                          <code className="mono">{issue.code}</code>{' '}
                          <Badge tone={severityTone(issue.severity)}>
                            {severityLabel(issue.severity)}
                          </Badge>
                        </td>
                        <td>{issue.field ?? '—'}</td>
                        <td>
                          {categoryLabel(issue.category)}: {issue.message}
                        </td>
                        <td>
                          <Values values={issue.values} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          )}
        </Panel>
      )}
    </>
  )
}
