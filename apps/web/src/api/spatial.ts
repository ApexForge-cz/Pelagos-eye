import type { SourceState } from './status'

export interface ViewportBounds {
  west: number
  south: number
  east: number
  north: number
}

export interface RecordProvenance {
  source_slug: string
  source_display_name: string
  source_url: string
  attribution_text: string
  data_version: string
  schema_version: string
  published_at: string | null
  retrieved_at: string
  ingested_at: string
  normalized_at: string
  source_state: SourceState
  cache_age_seconds: number | null
}

export interface PortRecord {
  id: string
  source_record_id: string
  record_type: 'unlocode' | 'wpi'
  name: string
  country_code: string
  un_locode: string | null
  longitude: number | null
  latitude: number | null
  coordinate_accuracy: string | null
  function_code: string | null
  source_status: string | null
  source_updated_value: string | null
  quality_flags: string[]
  provenance: RecordProvenance
}

export interface EarthquakeRecord {
  id: string
  event_id: string
  event_time: string
  provider_updated_at: string
  longitude: number
  latitude: number
  depth_km: number
  magnitude: number | null
  place: string | null
  event_type: string | null
  provider_status: string | null
  tsunami: boolean
  significance: number | null
  detail_url: string | null
  quality_flags: string[]
  provenance: RecordProvenance
}

export interface MarineForecastRecord {
  id: string
  requested_latitude: number
  requested_longitude: number
  grid_latitude: number
  grid_longitude: number
  valid_at: string
  model: string
  wave_height_m: number | null
  wave_direction_deg: number | null
  wave_period_s: number | null
  sea_surface_temperature_c: number | null
  ocean_current_velocity_kmh: number | null
  ocean_current_direction_deg: number | null
  sea_level_height_msl_m: number | null
  units: Record<string, string>
  quality_flags: string[]
  provenance: RecordProvenance
}

export type LayerLoadState<T> =
  | { kind: 'ready'; records: T[]; total: number; truncated: boolean }
  | { kind: 'unavailable'; message: string }

export interface SpatialSnapshot {
  requestedAt: string
  ports: LayerLoadState<PortRecord>
  earthquakes: LayerLoadState<EarthquakeRecord>
}

interface PageResponse<T> {
  total: number
  records: T[]
}

const VIEWPORT_LIMIT = 100

export async function loadSpatialSnapshot(
  bounds: ViewportBounds,
  signal?: AbortSignal,
): Promise<SpatialSnapshot> {
  const now = new Date()
  const start = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  const viewport = new URLSearchParams({
    min_longitude: String(bounds.west),
    min_latitude: String(bounds.south),
    max_longitude: String(bounds.east),
    max_latitude: String(bounds.north),
    limit: String(VIEWPORT_LIMIT),
  })
  const portParams = new URLSearchParams(viewport)
  portParams.set('has_coordinates', 'true')
  const earthquakeParams = new URLSearchParams(viewport)
  earthquakeParams.set('start_at', start.toISOString())
  earthquakeParams.set('end_at', now.toISOString())

  const [ports, earthquakes] = await Promise.all([
    requestLayer<PortRecord>(`/ports?${portParams}`, signal),
    requestLayer<EarthquakeRecord>(`/earthquakes?${earthquakeParams}`, signal),
  ])
  return { requestedAt: now.toISOString(), ports, earthquakes }
}

export async function loadMarineForecast(
  latitude: number,
  longitude: number,
  signal?: AbortSignal,
): Promise<LayerLoadState<MarineForecastRecord>> {
  const now = new Date()
  const end = new Date(now.getTime() + 24 * 60 * 60 * 1000)
  const params = new URLSearchParams({
    latitude: latitude.toFixed(6),
    longitude: longitude.toFixed(6),
    start_at: now.toISOString(),
    end_at: end.toISOString(),
    limit: '24',
  })
  return requestLayer<MarineForecastRecord>(`/ocean/forecast?${params}`, signal)
}

async function requestLayer<T>(path: string, signal?: AbortSignal): Promise<LayerLoadState<T>> {
  try {
    const response = await fetch(path, { headers: { Accept: 'application/json' }, signal })
    if (!response.ok) {
      return { kind: 'unavailable', message: `${path.split('?')[0]} 返回 HTTP ${response.status}` }
    }
    const page = (await response.json()) as PageResponse<T>
    return {
      kind: 'ready',
      records: page.records,
      total: page.total,
      truncated: page.total > page.records.length,
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    return {
      kind: 'unavailable',
      message: error instanceof Error ? error.message : '空间数据请求失败',
    }
  }
}
