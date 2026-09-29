import type { GeoJSONSource, Map as MapLibreMap, MapLayerMouseEvent } from 'maplibre-gl'

import type { LiveAisPosition } from '../api/liveAis'
import type { LiveAisClientState } from '../api/liveAisState'

const SOURCE_ID = 'live-ais-vessels'
const LAYER_ID = 'live-ais-vessel-points'
export const LIVE_AIS_MAP_LIMIT = 5_000
const MAX_AGE_MS = 5 * 60 * 1_000

export function visibleLiveAisPositions(
  state: LiveAisClientState,
  now: number,
  transportConnected: boolean,
): LiveAisPosition[] {
  const status = state.status
  const statusAgeSeconds = status ? (now - Date.parse(status.emitted_at)) / 1_000 : NaN
  if (
    !transportConnected ||
    state.requiresSnapshot ||
    !status ||
    status.connection_state !== 'CONNECTED' ||
    status.availability !== 'AVAILABLE' ||
    status.coverage.state !== 'COVERED' ||
    (status.source_state !== 'LIVE' && status.source_state !== 'CACHED') ||
    (status.source_state === 'CACHED' &&
      (status.cache_age_seconds === null ||
        !Number.isFinite(statusAgeSeconds) ||
        statusAgeSeconds < -30 ||
        status.cache_age_seconds + Math.max(0, statusAgeSeconds) > 300))
  )
    return []

  const bounds = status.coverage.bounds
  if (!bounds) return []

  return Object.values(state.positions)
    .filter((position) => {
      const age = now - Date.parse(position.observed_at)
      return (
        Number.isFinite(age) &&
        age >= -30_000 &&
        age <= MAX_AGE_MS &&
        Number.isFinite(position.longitude) &&
        Number.isFinite(position.latitude) &&
        position.longitude >= bounds.west &&
        position.longitude <= bounds.east &&
        position.latitude >= bounds.south &&
        position.latitude <= bounds.north &&
        (position.provenance.source_state === 'LIVE' ||
          position.provenance.source_state === 'CACHED')
      )
    })
    .sort((a, b) => a.mmsi.localeCompare(b.mmsi))
    .slice(0, LIVE_AIS_MAP_LIMIT)
}

export function mountLiveAisVesselLayer(
  map: MapLibreMap,
  onSelect: (position: LiveAisPosition) => void,
) {
  const byMmsi = new Map<string, LiveAisPosition>()
  map.addSource(SOURCE_ID, { type: 'geojson', data: emptyCollection() })
  map.addLayer({
    id: LAYER_ID,
    type: 'circle',
    source: SOURCE_ID,
    paint: {
      'circle-radius': 5,
      'circle-color': '#e8bb69',
      'circle-stroke-color': '#15232a',
      'circle-stroke-width': 1.5,
    },
  })

  const select = (event: MapLayerMouseEvent) => {
    const mmsi: unknown = event.features?.[0]?.properties?.mmsi
    if (typeof mmsi !== 'string') return
    const position = byMmsi.get(mmsi)
    if (position) onSelect(position)
  }
  map.on('click', LAYER_ID, select)

  return {
    update(positions: LiveAisPosition[]) {
      byMmsi.clear()
      for (const position of positions.slice(0, LIVE_AIS_MAP_LIMIT))
        byMmsi.set(position.mmsi, position)
      const source: GeoJSONSource | undefined = map.getSource(SOURCE_ID)
      void source?.setData({
        type: 'FeatureCollection',
        features: [...byMmsi.values()].map((position) => ({
          type: 'Feature' as const,
          geometry: {
            type: 'Point' as const,
            coordinates: [position.longitude, position.latitude],
          },
          properties: { mmsi: position.mmsi },
        })),
      })
    },
    remove() {
      map.off('click', LAYER_ID, select)
      byMmsi.clear()
      if (map.getLayer(LAYER_ID)) map.removeLayer(LAYER_ID)
      if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID)
    },
  }
}

function emptyCollection() {
  return { type: 'FeatureCollection' as const, features: [] }
}
