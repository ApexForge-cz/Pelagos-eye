const foundationItems = [
  'React + TypeScript development shell',
  'FastAPI liveness and readiness endpoints',
  'Typed configuration and structured logs',
  'Automated formatting, linting, tests, and builds',
]

export function App() {
  return (
    <main className="foundation-shell">
      <section className="foundation-card" aria-labelledby="page-title">
        <p className="eyebrow">OceanScope · Phase 1</p>
        <h1 id="page-title">工程基础已启动</h1>
        <p className="summary">
          当前只验证工程结构与开发链路。地图、船舶、港口、海洋环境和风险数据仍为后续阶段计划，
          本页面不会展示模拟业务数据。
        </p>

        <div className="status" role="status">
          <span className="status-dot" aria-hidden="true" />
          Engineering foundation
        </div>

        <ul>
          {foundationItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>

        <p className="notice">No production maritime data is connected in Phase 1.</p>
      </section>
    </main>
  )
}
