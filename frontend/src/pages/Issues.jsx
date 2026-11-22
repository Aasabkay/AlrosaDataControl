import { useState } from 'react'

import {
  Badge,
  Empty,
  ErrorNote,
  Loading,
  Panel,
  Values,
  categoryLabel,
  formatRefs,
  severityLabel,
  severityTone,
} from '../components/ui'
import { useApi } from '../hooks/useApi'

const CATEGORY_OPTIONS = [
  { value: '', label: 'все категории' },
  { value: 'excluded', label: 'исключённые строки' },
  { value: 'duplicate', label: 'дубликаты' },
  { value: 'missing', label: 'пропуски и статусы' },
  { value: 'mismatch', label: 'расхождения' },
]

const SEVERITY_OPTIONS = [
  { value: '', label: 'любая критичность' },
  { value: 'high', label: 'высокая' },
  { value: 'medium', label: 'средняя' },
  { value: 'low', label: 'низкая' },
]

export default function Issues({ onOpenAsset }) {
  const [category, setCategory] = useState('')
  const [severity, setSeverity] = useState('')
  const [code, setCode] = useState('')

  const params = new URLSearchParams()
  if (category) params.set('category', category)
  if (severity) params.set('severity', severity)
  if (code) params.set('code', code)
  const query = params.toString()

  const { data: issues, loading, error } = useApi(
    `/reconciliations/1/issues${query ? `?${query}` : ''}`
  )

  return (
    <Panel
      title={issues ? `Ошибки (${issues.length})` : 'Ошибки'}
      actions={
        <div className="controls">
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
            {SEVERITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="код, например FIELD_MISMATCH"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </div>
      }
    >
      {loading && <Loading />}
      {error && <ErrorNote message={error} />}

      {issues && issues.length === 0 && <Empty>Под фильтры ничего не попало.</Empty>}

      {issues && issues.length > 0 && (
        <table className="data">
          <thead>
            <tr>
              <th>Критичность</th>
              <th>Код</th>
              <th>Категория</th>
              <th>Поле</th>
              <th>Сообщение</th>
              <th>Значения по источникам</th>
              <th>Строки</th>
              <th>Актив</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, index) => (
              <tr key={index}>
                <td>
                  <Badge tone={severityTone(issue.severity)}>
                    {severityLabel(issue.severity)}
                  </Badge>
                </td>
                <td>
                  <code className="mono">{issue.code}</code>
                </td>
                <td>{categoryLabel(issue.category)}</td>
                <td>{issue.field ?? '—'}</td>
                <td>
                  {issue.message}
                  {issue.suggestion && (
                    <div className="muted">
                      Возможно, имелось в виду: {issue.suggestion}
                    </div>
                  )}
                </td>
                <td>
                  <Values values={issue.values} />
                </td>
                <td>{formatRefs(issue.refs)}</td>
                <td>
                  {issue.asset_key ? (
                    <button
                      className="link"
                      type="button"
                      onClick={() => onOpenAsset(issue.asset_key)}
                    >
                      {issue.asset_key}
                    </button>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  )
}
