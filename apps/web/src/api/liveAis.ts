import type { Availability, SourceState } from './status'

export const LIVE_AIS_PROTOCOL_VERSION = '1.0' as const

export interface LiveAisBounds {
  west: number
  south: number
  east: number
  north: number
}

export interface LiveAisCoverage {
  state: 'COVERED' | 'NO COVERAGE'
  description: string
  bounds: LiveAisBounds | null
  effective_at: string
}

export interface LiveAisProvenance {
  source_slug: string
  source_url: string
  attribution_text: string
  data_version: string
  schema_version: string
  provider_message_type: string
  source_event_id: string | null
  ingested_at: string
  normalized_at: string
  source_state: SourceState
  cache_age_seconds: number | null
}

export interface LiveAisPosition {
  observation_id: string
  mmsi: string
  observed_at: string
  longitude: number
  latitude: number
  speed_over_ground_knots: number | null
  course_over_ground_deg: number | null
  true_heading_deg: number | null
  navigational_status_code: number | null
  quality_flags: string[]
  provenance: LiveAisProvenance
}

interface LiveAisEventBase {
  protocol_version: typeof LIVE_AIS_PROTOCOL_VERSION
  stream_epoch: string
  sequence: number
  emitted_at: string
}

export interface LiveAisSnapshotEvent extends LiveAisEventBase {
  event: 'vessel.snapshot'
  availability: Availability
  source_state: SourceState
  cache_age_seconds: number | null
  coverage: LiveAisCoverage
  positions: LiveAisPosition[]
  truncated: boolean
}

export interface LiveAisPositionEvent extends LiveAisEventBase {
  event: 'vessel.position'
  position: LiveAisPosition
}

export interface LiveAisStatusEvent extends LiveAisEventBase {
  event: 'stream.status'
  connection_state: 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED'
  source_state: SourceState
  cache_age_seconds: number | null
  availability: Availability
  coverage: LiveAisCoverage
  last_observation_at: string | null
  retry_at: string | null
  detail: string
}

export interface LiveAisGapEvent extends LiveAisEventBase {
  event: 'stream.gap'
  gap_started_at: string
  gap_ended_at: string | null
  reason:
    'provider_disconnect' | 'server_backpressure' | 'client_backpressure' | 'subscription_change'
  dropped_updates: number | null
  replay_available: false
  detail: string
}

export type LiveAisServerEvent =
  LiveAisSnapshotEvent | LiveAisPositionEvent | LiveAisStatusEvent | LiveAisGapEvent

const EVENT_NAMES = new Set<LiveAisServerEvent['event']>([
  'vessel.snapshot',
  'vessel.position',
  'stream.status',
  'stream.gap',
])

export function hasSupportedLiveAisEnvelope(value: unknown): boolean {
  if (typeof value !== 'object' || value === null) return false
  const candidate = value as Record<string, unknown>
  return (
    candidate.protocol_version === LIVE_AIS_PROTOCOL_VERSION &&
    typeof candidate.event === 'string' &&
    EVENT_NAMES.has(candidate.event as LiveAisServerEvent['event']) &&
    typeof candidate.stream_epoch === 'string' &&
    Number.isSafeInteger(candidate.sequence) &&
    (candidate.sequence as number) >= 0 &&
    typeof candidate.emitted_at === 'string'
  )
}
