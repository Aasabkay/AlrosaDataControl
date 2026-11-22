import { useState } from 'react'

import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import ImportLog from './pages/ImportLog'
import Issues from './pages/Issues'
import Assets from './pages/Assets'
import Report from './pages/Report'

const TABS = [
  { id: 'dashboard', label: 'Дашборд' },
  { id: 'upload', label: 'Загрузка' },
  { id: 'log', label: 'Журнал импорта' },
  { id: 'issues', label: 'Ошибки' },
  { id: 'assets', label: 'Активы' },
  { id: 'report', label: 'Отчёт' },
]

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [logImportId, setLogImportId] = useState(null)
  const [assetKey, setAssetKey] = useState(null)

  function openLog(importId) {
    setLogImportId(importId)
    setTab('log')
  }

  function openAsset(key) {
    setAssetKey(key)
    setTab('assets')
  }

  return (
    <>
      <header className="app-header">
        <div>
          <h1>Сверка ИТ-активов</h1>
          <span className="subtitle">прототип контроля данных об ИТ-оборудовании</span>
        </div>
        <nav className="tabs">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? 'active' : ''}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'upload' && <Upload onOpenLog={openLog} />}
        {tab === 'log' && <ImportLog key={logImportId} initialImportId={logImportId} />}
        {tab === 'issues' && <Issues onOpenAsset={openAsset} />}
        {tab === 'assets' && <Assets selectedAssetKey={assetKey} />}
        {tab === 'report' && <Report />}
      </main>
    </>
  )
}
