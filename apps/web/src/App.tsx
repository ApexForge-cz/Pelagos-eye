import { useCallback, useEffect, useState } from 'react'

import { loadPlatformStatus, type PlatformStatus } from './api/status'
import { SourceCard } from './components/SourceCard'
import { StateBadge } from './components/StateBadge'

type ViewState =
  | { kind: 'loading' }
  | { kind: 'ready'; status: PlatformStatus }
  | { kind: 'error'; message: string }

export function App() {
  const [view, setView] = useState<ViewState>({ kind: 'loading' })
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = useCallback(() => {
    setView({ kind: 'loading' })
    setRefreshKey((value) => value + 1)
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    void loadPlatformStatus(controller.signal)
      .then((status) => setView({ kind: 'ready', status }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setView({
            kind: 'error',
            message: error instanceof Error ? error.message : '状态请求失败',
          })
        }
      })

    return () => controller.abort()
  }, [refreshKey])

  return (
    <main className="status-shell">
      <header className="masthead">
        <div>
          <p className="eyebrow">OceanScope · Phase 2</p>
          <h1>真实数据基础状态</h1>
          <p className="summary">
            此页面只呈现已接入来源的实际可用性、版本、更新时间和质量提示，不生成或补齐任何业务数据。
          </p>
        </div>
        <button className="refresh-button" type="button" onClick={refresh}>
          刷新状态
        </button>
      </header>

      {view.kind === 'loading' && (
        <section className="message-panel" aria-live="polite" aria-busy="true">
          <span className="loading-mark" aria-hidden="true" />
          正在读取数据来源与系统状态…
        </section>
      )}

      {view.kind === 'error' && (
        <section className="message-panel error-panel" role="alert">
          <div>
            <strong>DATA UNAVAILABLE</strong>
            <p>{view.message}</p>
          </div>
          <button type="button" onClick={refresh}>
            重试
          </button>
        </section>
      )}

      {view.kind === 'ready' && <StatusContent status={view.status} />}
    </main>
  )
}

function StatusContent({ status }: { status: PlatformStatus }) {
  const availableCount = status.catalog.sources.filter((source) => source.has_usable_data).length

  return (
    <>
      <section className="system-strip" aria-labelledby="system-heading">
        <div>
          <p className="section-kicker">Platform</p>
          <h2 id="system-heading">系统连接</h2>
        </div>
        <dl className="system-facts">
          <div>
            <dt>API</dt>
            <dd>
              <StateBadge state={status.system.overall_state} />
            </dd>
          </div>
          <div>
            <dt>Database</dt>
            <dd>
              <StateBadge state={status.system.database.state} />
            </dd>
          </div>
          <div>
            <dt>可用来源</dt>
            <dd className="numeric">
              {availableCount} / {status.catalog.sources.length}
            </dd>
          </div>
        </dl>
      </section>

      <section className="catalog" aria-labelledby="catalog-heading">
        <div className="section-heading">
          <div>
            <p className="section-kicker">Provenance</p>
            <h2 id="catalog-heading">数据来源</h2>
          </div>
          <p>目录生成时间：{formatUtc(status.catalog.generated_at)}</p>
        </div>

        {status.catalog.sources.length === 0 ? (
          <div className="message-panel">尚未登记任何数据来源。</div>
        ) : (
          <div className="source-grid">
            {status.catalog.sources.map((source) => (
              <SourceCard key={source.slug} source={source} />
            ))}
          </div>
        )}
      </section>
    </>
  )
}

function formatUtc(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '时间不可用'
  }
  return `${new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'medium',
    timeZone: 'UTC',
  }).format(date)} UTC`
}
