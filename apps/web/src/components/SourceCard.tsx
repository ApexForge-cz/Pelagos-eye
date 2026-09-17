import type { SourceStatus } from '../api/status'
import { StateBadge } from './StateBadge'

export function SourceCard({ source }: { source: SourceStatus }) {
  const run = source.latest_usable_run ?? source.latest_run

  return (
    <article className="source-card" aria-labelledby={`source-${source.slug}`}>
      <div className="source-card-header">
        <div>
          <p className="source-slug">{source.slug}</p>
          <h3 id={`source-${source.slug}`}>{source.display_name}</h3>
        </div>
        <StateBadge state={source.state} />
      </div>

      <p className={`availability ${source.has_usable_data ? '' : 'unavailable'}`}>
        {source.availability}
      </p>

      <dl className="source-facts">
        <Fact label="数据版本" value={source.latest_version?.data_version ?? '未产生版本'} />
        <Fact label="获取时间" value={formatUtc(source.latest_version?.retrieved_at)} />
        <Fact label="可用批次完成" value={formatUtc(run?.finished_at)} />
        <Fact label="最新运行状态" value={source.latest_run?.status ?? '无运行记录'} />
        <Fact
          label="可用批次：接受 / 拒绝"
          value={run ? `${run.records_accepted} / ${run.records_rejected}` : '无运行记录'}
        />
        <Fact
          label={source.state === 'CACHED' ? '当前缓存年龄' : '数据年龄'}
          value={formatDuration(
            source.state === 'CACHED' ? source.cache_age_seconds : source.freshness.age_seconds,
          )}
        />
        <Fact label="再分发" value={source.redistribution_status} />
      </dl>

      {source.quality_issues.length > 0 && (
        <div className="quality-block">
          <h4>质量提示</h4>
          <ul>
            {source.quality_issues.map((issue) => (
              <li key={issue.code}>
                <span>{issue.code}</span>
                <strong>{issue.record_count}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="attribution">{source.attribution_text}</p>
      <div className="source-links">
        <a href={source.official_url} target="_blank" rel="noreferrer">
          官方来源
        </a>
        {source.latest_version && (
          <a href={source.latest_version.source_url} target="_blank" rel="noreferrer">
            版本来源
          </a>
        )}
        {source.terms_url && (
          <a href={source.terms_url} target="_blank" rel="noreferrer">
            使用条款
          </a>
        )}
      </div>
    </article>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function formatUtc(value: string | null | undefined) {
  if (!value) {
    return 'DATA UNAVAILABLE'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'DATA UNAVAILABLE'
  }
  return `${new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(date)} UTC`
}

function formatDuration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined) {
    return '年龄未知'
  }
  if (seconds < 60) {
    return `${seconds} 秒`
  }
  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)} 分钟`
  }
  return `${Math.floor(seconds / 3600)} 小时 ${Math.floor((seconds % 3600) / 60)} 分钟`
}
