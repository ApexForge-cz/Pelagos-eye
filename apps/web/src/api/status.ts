export type SourceState = 'LIVE' | 'CACHED' | 'DELAYED' | 'OFFLINE'
export type Availability = 'AVAILABLE' | 'DATA UNAVAILABLE'

export interface QualityIssue {
  code: string
  severity: 'info' | 'warning' | 'error'
  record_count: number
  message: string
}

export interface IngestionRun {
  id: string
  status: 'running' | 'succeeded' | 'partial' | 'failed'
  source_state: SourceState
  cache_age_seconds: number | null
  started_at: string
  finished_at: string | null
  records_received: number
  records_accepted: number
  records_rejected: number
}

export interface SourceVersion {
  data_version: string
  schema_version: string
  source_url: string
  published_at: string | null
  retrieved_at: string
}

export interface SourceStatus {
  slug: string
  display_name: string
  official_url: string
  terms_url: string | null
  attribution_text: string
  license_identifier: string | null
  redistribution_status: 'allowed' | 'restricted' | 'prohibited' | 'unreviewed'
  state: SourceState
  availability: Availability
  has_usable_data: boolean
  latest_run: IngestionRun | null
  latest_usable_run: IngestionRun | null
  latest_version: SourceVersion | null
  quality_issues: QualityIssue[]
}

export interface SourceCatalog {
  generated_at: string
  sources: SourceStatus[]
}

export interface SystemStatus {
  service: 'oceanscope-api'
  version: string
  overall_state: 'READY' | 'DEGRADED'
  checked_at: string
  database: {
    state: 'LIVE' | 'OFFLINE'
    detail: string
  }
}

export interface PlatformStatus {
  system: SystemStatus
  catalog: SourceCatalog
}

export async function loadPlatformStatus(signal?: AbortSignal): Promise<PlatformStatus> {
  const [system, catalog] = await Promise.all([
    requestJson<SystemStatus>('/system/status', signal),
    requestJson<SourceCatalog>('/data/sources', signal),
  ])
  return { system, catalog }
}

async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: 'application/json' },
    signal,
  })
  if (!response.ok) {
    throw new Error(`${path} 返回 HTTP ${response.status}`)
  }
  return (await response.json()) as T
}
