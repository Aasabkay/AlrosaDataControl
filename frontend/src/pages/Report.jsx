import { api } from '../api'
import { Loading, ErrorNote, Panel } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { useLatestRun } from '../hooks/useLatestRun'


export default function Report() {
  const { runId } = useLatestRun()
  const { data: report, loading, error } = useApi(
    runId ? `/reconciliations/${runId}` : null
  )

  if (loading) return <Loading />
  if (error) return <ErrorNote message={error} />
  if (!report) return <p className="muted">Свёр ещё не было.</p>

  const summary = report.summary

  return (
    <>
      <Panel
        title="Отчёт о сверке"
        actions={
          <div className="controls">
            <a
              className="button-like"
              href={`${api.baseUrl}/reconciliations/${runId}/report?format=xlsx`}
            >
              Скачать XLSX
            </a>
            <a
              className="button-like secondary"
              href={`${api.baseUrl}/reconciliations/${runId}/report?format=json`}
              target="_blank"
              rel="noreferrer"
            >
              JSON
            </a>
          </div>
        }
      >
        <dl className="kv">
          <div className="kv-row">
            <dt>Организация</dt>
            <dd>{report.meta.organization || '—'}</dd>
          </div>
          <div className="kv-row">
            <dt>Ответственный</dt>
            <dd>{report.meta.responsible || '—'}</dd>
          </div>
          <div className="kv-row">
            <dt>Дата составления</dt>
            <dd>{report.meta.generated_at}</dd>
          </div>
          <div className="kv-row">
            <dt>Период инвентаризации</dt>
            <dd>
              {report.meta.period_start ?? '—'} — {report.meta.period_end ?? '—'}
            </dd>
          </div>
          <div className="kv-row">
            <dt>Комиссия</dt>
            <dd>{report.meta.commission.join(', ') || '—'}</dd>
          </div>
        </dl>

        <h3 className="sub-title">Классификация ошибок</h3>
        <table className="data">
          <thead>
            <tr>
              <th>Показатель</th>
              <th>Значение</th>
            </tr>
          </thead>
          <tbody>
            <tr><td>Всего активов</td><td>{summary.assets_total}</td></tr>
            <tr><td>Активов с замечаниями</td><td>{summary.assets_with_issues}</td></tr>
            <tr><td>Неоднозначное сопоставление</td><td>{summary.ambiguous_assets}</td></tr>
            <tr><td>Всего ошибок</td><td>{summary.issues_total}</td></tr>
            <tr><td>Исключено строк</td><td>{summary.excluded_rows}</td></tr>
            <tr><td>Дубликаты</td><td>{summary.duplicates}</td></tr>
            <tr><td>Пропуски и статусы</td><td>{summary.missing_or_status}</td></tr>
            <tr><td>Расхождения</td><td>{summary.mismatches}</td></tr>
          </tbody>
        </table>

        <h3 className="sub-title">Выводы</h3>
        <ul className="plain-list">
          {report.recommendations.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </Panel>
    </>
  )
}
