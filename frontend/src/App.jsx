import { useEffect, useState } from 'react'

import { api, getToken } from './api'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import ImportLog from './pages/ImportLog'
import Issues from './pages/Issues'
import Assets from './pages/Assets'
import Report from './pages/Report'
import Auth from './pages/Auth'

const TABS = [
  { id: 'dashboard', label: 'Дашборд' },
  { id: 'upload', label: 'Загрузка' },
  { id: 'log', label: 'Журнал импорта' },
  { id: 'issues', label: 'Ошибки' },
  { id: 'assets', label: 'Активы' },
  { id: 'report', label: 'Отчёт' },
]

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getToken()))
  const [tab, setTab] = useState('dashboard')
  const [logImportId, setLogImportId] = useState(null)
  const [assetKey, setAssetKey] = useState(null)

  useEffect(() => {
    const logout = () => setAuthenticated(false)
    window.addEventListener('auth:unauthorized', logout)
    return () => window.removeEventListener('auth:unauthorized', logout)
  }, [])

  function openLog(importId) {
    setLogImportId(importId)
    setTab('log')
  }

  function openAsset(key) {
    setAssetKey(key)
    setTab('assets')
  }

  if (!authenticated) {
    return <Auth onAuthenticated={() => setAuthenticated(true)} />
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
        <button
          className="link logout"
          type="button"
          onClick={() => {
            api.logout()
            setAuthenticated(false)
          }}
        >
          Выйти
        </button>
      </header>

      <main>
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'upload' && (
          <Upload onOpenLog={openLog} onOpenDashboard={() => setTab('dashboard')} />
        )}
        {tab === 'log' && <ImportLog key={logImportId} initialImportId={logImportId} />}
        {tab === 'issues' && <Issues onOpenAsset={openAsset} />}
        {tab === 'assets' && <Assets selectedAssetKey={assetKey} />}
        {tab === 'report' && <Report />}
      </main>
    </>
  )
}
