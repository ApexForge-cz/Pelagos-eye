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

export function isSupportedLiveAisEvent(value: unknown): value is LiveAisServerEvent {
  if (!hasSupportedLiveAisEnvelope(value) || !isRecord(value)) return false
  if (!isUuid(value.stream_epoch) || !isDate(value.emitted_at)) return false
  switch (value.event) {
    case 'vessel.snapshot':
      return isSnapshotEvent(value)
    case 'vessel.position':
      return isPosition(value.position)
    case 'stream.status':
      return isStatusEvent(value)
    case 'stream.gap':
      return isGapEvent(value)
    default:
      return false
  }
}

function isSnapshotEvent(value: Record<string, unknown>) {
  if (
    !isAvailability(value.availability) ||
    !isSourceState(value.source_state) ||
    !isCacheAgeForState(value.source_state, value.cache_age_seconds) ||
    !isCoverage(value.coverage) ||
    !Array.isArray(value.positions) ||
    !value.positions.every(isPosition) ||
    typeof value.truncated !== 'boolean'
  )
    return false
  return !(
    (value.availability === 'DATA UNAVAILABLE' || value.coverage.state === 'NO COVERAGE') &&
    value.positions.length > 0
  )
}

function isStatusEvent(value: Record<string, unknown>) {
  return (
    isOneOf(value.connection_state, ['CONNECTING', 'CONNECTED', 'RECONNECTING', 'DISCONNECTED']) &&
    isSourceState(value.source_state) &&
    isCacheAgeForState(value.source_state, value.cache_age_seconds) &&
    isAvailability(value.availability) &&
    isCoverage(value.coverage) &&
    isNullableDate(value.last_observation_at) &&
    isNullableDate(value.retry_at) &&
    isNonEmptyString(value.detail)
  )
}

function isGapEvent(value: Record<string, unknown>) {
  if (
    !isDate(value.gap_started_at) ||
    !isNullableDate(value.gap_ended_at) ||
    !isOneOf(value.reason, [
      'provider_disconnect',
      'server_backpressure',
      'client_backpressure',
      'subscription_change',
    ]) ||
    !(value.dropped_updates === null || isNonNegativeInteger(value.dropped_updates)) ||
    value.replay_available !== false ||
    !isNonEmptyString(value.detail)
  )
    return false
  return (
    value.gap_ended_at === null ||
    Date.parse(value.gap_ended_at) >= Date.parse(value.gap_started_at)
  )
}

function isCoverage(value: unknown): value is LiveAisCoverage {
  if (!isRecord(value) || !isOneOf(value.state, ['COVERED', 'NO COVERAGE'])) return false
  if (!isNonEmptyString(value.description) || !isDate(value.effective_at)) return false
  if (value.bounds !== null && !isBounds(value.bounds)) return false
  return value.state !== 'COVERED' || value.bounds !== null
}

function isBounds(value: unknown): value is LiveAisBounds {
  if (!isRecord(value)) return false
  const { west, south, east, north } = value
  return (
    isFiniteRange(west, -180, 180) &&
    isFiniteRange(east, -180, 180) &&
    isFiniteRange(south, -90, 90) &&
    isFiniteRange(north, -90, 90) &&
    west < east &&
    south < north
  )
}

function isPosition(value: unknown): value is LiveAisPosition {
  if (!isRecord(value)) return false
  return (
    isNonEmptyString(value.observation_id) &&
    typeof value.mmsi === 'string' &&
    /^\d{9}$/.test(value.mmsi) &&
    isDate(value.observed_at) &&
    isFiniteRange(value.longitude, -180, 180) &&
    isFiniteRange(value.latitude, -90, 90) &&
    isNullableFiniteRange(value.speed_over_ground_knots, 0, 102.3, false) &&
    isNullableFiniteRange(value.course_over_ground_deg, 0, 360, false) &&
    isNullableIntegerRange(value.true_heading_deg, 0, 359) &&
    isNullableIntegerRange(value.navigational_status_code, 0, 15) &&
    Array.isArray(value.quality_flags) &&
    value.quality_flags.every((flag) => typeof flag === 'string') &&
    isProvenance(value.provenance)
  )
}

function isProvenance(value: unknown): value is LiveAisProvenance {
  if (!isRecord(value) || !isSourceState(value.source_state)) return false
  if (!isDate(value.ingested_at) || !isDate(value.normalized_at)) return false
  return (
    isNonEmptyString(value.source_slug) &&
    isNonEmptyString(value.source_url) &&
    isNonEmptyString(value.attribution_text) &&
    isNonEmptyString(value.data_version) &&
    isNonEmptyString(value.schema_version) &&
    isNonEmptyString(value.provider_message_type) &&
    (value.source_event_id === null || typeof value.source_event_id === 'string') &&
    Date.parse(value.normalized_at) >= Date.parse(value.ingested_at) &&
    isCacheAgeForState(value.source_state, value.cache_age_seconds)
  )
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}

function isUuid(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)
  )
}

function isDate(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    /(Z|[+-]\d{2}:\d{2})$/.test(value) &&
    Number.isFinite(Date.parse(value))
  )
}

function isNullableDate(value: unknown): value is string | null {
  return value === null || isDate(value)
}

function isFiniteRange(value: unknown, minimum: number, maximum: number): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= minimum && value <= maximum
}

function isNullableFiniteRange(
  value: unknown,
  minimum: number,
  maximum: number,
  inclusiveMaximum = true,
) {
  return (
    value === null ||
    (typeof value === 'number' &&
      Number.isFinite(value) &&
      value >= minimum &&
      (inclusiveMaximum ? value <= maximum : value < maximum))
  )
}

function isNullableIntegerRange(value: unknown, minimum: number, maximum: number) {
  return (
    value === null ||
    (Number.isInteger(value) && Number(value) >= minimum && Number(value) <= maximum)
  )
}

function isNonNegativeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) >= 0
}

function isSourceState(value: unknown): value is SourceState {
  return isOneOf(value, ['LIVE', 'CACHED', 'DELAYED', 'OFFLINE'])
}

function isAvailability(value: unknown): value is Availability {
  return isOneOf(value, ['AVAILABLE', 'DATA UNAVAILABLE'])
}

function isCacheAgeForState(state: SourceState, value: unknown) {
  return state === 'CACHED' ? isNonNegativeInteger(value) : value === null
}

function isOneOf<const Values extends readonly string[]>(
  value: unknown,
  values: Values,
): value is Values[number] {
  return typeof value === 'string' && (values as readonly string[]).includes(value)
}
