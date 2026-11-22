import { api } from '../api'
import { Loading, ErrorNote, Empty } from '../components/ui'
import { useApi } from '../hooks/useApi'
import { useLatestRun } from '../hooks/useLatestRun'

export default function Dashboard() {
  const { runId, loading: runLoading, error: runError } = useLatestRun()
  const { data: report, loading, error } = useApi(
    runId ? `/reconciliations/${runId}` : null
  )
  const { data: sources } = useApi('/sources')

  if (runLoading || loading) return <Loading />
  if (runError || error) return <ErrorNote message={runError ?? error} />
  if (!report) return <Empty>Свёр ещё не было — загрузите файлы и запустите сверку.</Empty>

  const summary = report.summary
  const maxCount = Math.max(1, ...Object.values(summary.by_code))

  const stats = [
    { label: 'Активов всего', value: summary.assets_total },
    { label: 'Активов с замечаниями', value: summary.assets_with_issues },
    { label: 'Неоднозначное сопоставление', value: summary.ambiguous_assets },
    { label: 'Ошибок всего', value: summary.issues_total },
    { label: 'Исключено строк', value: summary.excluded_rows },
    { label: 'Дубликаты', value: summary.duplicates },
    { label: 'Пропуски и статусы', value: summary.missing_or_status },
    { label: 'Расхождения', value: summary.mismatches },
  ]

  return (
    <>
      <div className="stats">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className={stat.value > 0 ? 'stat' : 'stat clean'}
          >
            <div className="label">{stat.label}</div>
            <div className="value">{stat.value}</div>
          </div>
        ))}
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2 className="panel-title">Ошибки по кодам</h2>
        </div>
        <div className="panel-body">
          {Object.keys(summary.by_code).length === 0 ? (
            <Empty>Ошибок нет.</Empty>
          ) : (
            Object.entries(summary.by_code).map(([code, count]) => (
              <div className="bar-row" key={code}>
                <code className="mono">{code}</code>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${(count / maxCount) * 100}%` }}
                  />
                </div>
                <div className="bar-count">{count}</div>
              </div>
            ))
          )}
        </div>
      </section>

      <div className="two-columns">
        <section className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Выводы</h2>
          </div>
          <div className="panel-body">
            <ul className="plain-list">
              {report.recommendations.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2 className="panel-title">Отчёт составлен</h2>
          </div>
          <div className="panel-body">
            <dl className="kv">
              <dt>Организация</dt>
              <dd>{report.meta.organization || '—'}</dd>
              <dt>Ответственный</dt>
              <dd>{report.meta.responsible || '—'}</dd>
              <dt>Дата</dt>
              <dd>{report.meta.generated_at}</dd>
              <dt>Источники</dt>
              <dd>
                {sources
                  ? sources.map((source) => `${source.id} — ${source.name}`).join('; ')
                  : '—'}
              </dd>
            </dl>
          </div>
        </section>
      </div>

      <p className="footnote">
        Данные: {api.baseUrl} (настоящее API). Прогон сверки: {runId}.
      </p>
    </>
  )
}
