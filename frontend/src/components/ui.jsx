



const CATEGORY_LABELS = {
  excluded: 'исключённые строки',
  duplicate: 'дубликаты',
  missing: 'пропуски и статусы',
  mismatch: 'расхождения',
}

const SEVERITY_LABELS = {
  high: 'высокая',
  medium: 'средняя',
  low: 'низкая',
}

export function categoryLabel(value) {
  return CATEGORY_LABELS[value] ?? value
}

export function severityLabel(value) {
  return SEVERITY_LABELS[value] ?? value
}

export function severityTone(value) {
  if (value === 'high') return 'bad'
  if (value === 'medium') return 'warn'
  return 'muted'
}

export function formatRefs(refs) {
  return refs
    .map((ref) => `источник ${ref.source_id}, строка ${ref.row_number}`)
    .join('; ')
}

export function Panel({ title, children, actions = null }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title">{title}</h2>
        {actions}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  )
}

export function Stat({ label, value, attention = false }) {
  return (
    <div className={attention ? 'stat attention' : 'stat'}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  )
}

export function Badge({ tone = 'muted', children }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function Loading() {
  return <p className="muted">Загрузка…</p>
}

export function ErrorNote({ message }) {
  return <div className="error-note">{message}</div>
}

export function Empty({ children }) {
  return <p className="muted">{children}</p>
}


export function Values({ values }) {
  if (!values || values.length === 0) return <span className="muted">—</span>
  return (
    <ul className="diff-list">
      {values.map((item, index) => (
        <li key={index}>
          источник {item.ref.source_id}, строка {item.ref.row_number}:{' '}
          <b>{item.value ?? 'пусто'}</b>
        </li>
      ))}
    </ul>
  )
}
