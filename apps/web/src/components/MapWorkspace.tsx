import { useEffect, useMemo, useRef, useState, type RefObject } from 'react'
import {
  AttributionControl,
  FullscreenControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  type MapMouseEvent,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

import type { LiveAisPosition } from '../api/liveAis'
import type { LiveAisClientState } from '../api/liveAisState'
import type { EarthquakeRecord, PortRecord, ViewportBounds } from '../api/spatial'
import {
  LIVE_AIS_MAP_LIMIT,
  mountLiveAisVesselLayer,
  visibleLiveAisPositions,
} from './liveAisVesselLayer'

export type MapSelection =
  | { kind: 'port'; record: PortRecord }
  | { kind: 'earthquake'; record: EarthquakeRecord }
  | { kind: 'coordinate'; longitude: number; latitude: number }

interface MapWorkspaceProps {
  ports: PortRecord[]
  earthquakes: EarthquakeRecord[]
  portsVisible: boolean
  earthquakesVisible: boolean
  inspectMarine: boolean
  onBoundsChange: (bounds: ViewportBounds) => void
  onSelection: (selection: MapSelection) => void
  liveAis?: { state: LiveAisClientState; transportConnected: boolean }
  onVesselSelection?: (position: LiveAisPosition) => void
}

interface MapCallbacks {
  onBoundsChange: (bounds: ViewportBounds) => void
  onSelection: (selection: MapSelection) => void
}

export function MapWorkspace({
  ports,
  earthquakes,
  portsVisible,
  earthquakesVisible,
  inspectMarine,
  onBoundsChange,
  onSelection,
  liveAis,
  onVesselSelection,
}: MapWorkspaceProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const markersRef = useRef<{ ports: Marker[]; earthquakes: Marker[] }>({
    ports: [],
    earthquakes: [],
  })
  const callbacksRef = useRef({ onBoundsChange, onSelection })
  const recordsRef = useRef({ ports, earthquakes, inspectMarine })
  const visibilityRef = useRef({ portsVisible, earthquakesVisible })
  const liveAisLayerRef = useRef<ReturnType<typeof mountLiveAisVesselLayer> | null>(null)
  const liveAisRef = useRef({ liveAis, onVesselSelection })
  const [now, setNow] = useState(() => Date.now())
  const [coordinates, setCoordinates] = useState('0.0000°, 0.0000°')
  const [basemapUnavailable, setBasemapUnavailable] = useState(false)
  const hasLiveAis = Boolean(liveAis)
  const visibleVessels = useMemo(
    () => (liveAis ? visibleLiveAisPositions(liveAis.state, now, liveAis.transportConnected) : []),
    [liveAis, now],
  )

  useEffect(() => {
    callbacksRef.current = { onBoundsChange, onSelection }
  }, [onBoundsChange, onSelection])

  useEffect(() => {
    recordsRef.current = { ports, earthquakes, inspectMarine }
  }, [ports, earthquakes, inspectMarine])

  useEffect(() => {
    visibilityRef.current = { portsVisible, earthquakesVisible }
  }, [portsVisible, earthquakesVisible])

  useEffect(() => {
    liveAisRef.current = { liveAis, onVesselSelection }
  }, [liveAis, onVesselSelection])

  useEffect(() => {
    if (!hasLiveAis) return
    const timer = window.setInterval(() => setNow(Date.now()), 15_000)
    return () => window.clearInterval(timer)
  }, [hasLiveAis])

  useEffect(() => {
    if (!containerRef.current) return

    const map = new MapLibreMap({
      container: containerRef.current,
      center: [112, 24],
      zoom: 2.35,
      minZoom: 1.25,
      maxZoom: 12,
      attributionControl: false,
      style: {
        version: 8,
        sources: {},
        layers: [
          {
            id: 'background',
            type: 'background',
            paint: { 'background-color': 'rgba(6, 16, 24, 0.42)' },
          },
        ],
      },
    })
    mapRef.current = map
    map.addControl(new NavigationControl({ visualizePitch: true }), 'top-right')
    map.addControl(new FullscreenControl(), 'top-right')
    map.addControl(new AttributionControl({ compact: true }), 'bottom-right')

    const emitBounds = () => {
      const bounds = map.getBounds()
      if (!bounds) return
      const west = Math.max(-180, bounds.getWest())
      const east = Math.min(180, bounds.getEast())
      const south = Math.max(-90, bounds.getSouth())
      const north = Math.min(90, bounds.getNorth())
      if (west < east && south < north) {
        callbacksRef.current.onBoundsChange({ west, south, east, north })
      }
    }

    const basemapController = new AbortController()
    const activeMarkers = markersRef.current
    map.on('load', () => {
      liveAisLayerRef.current = mountLiveAisVesselLayer(map, (position) => {
        liveAisRef.current.onVesselSelection?.(position)
      })
      liveAisLayerRef.current.update(
        liveAisRef.current.liveAis
          ? visibleLiveAisPositions(
              liveAisRef.current.liveAis.state,
              Date.now(),
              liveAisRef.current.liveAis.transportConnected,
            )
          : [],
      )
      activeMarkers.ports = createPortMarkers(
        map,
        recordsRef.current.ports,
        visibilityRef.current.portsVisible,
        callbacksRef,
      )
      activeMarkers.earthquakes = createEarthquakeMarkers(
        map,
        recordsRef.current.earthquakes,
        visibilityRef.current.earthquakesVisible,
        callbacksRef,
      )
      emitBounds()
      void attachOpenStreetMap(map, basemapController.signal).then((unavailable) => {
        if (!basemapController.signal.aborted) setBasemapUnavailable(unavailable)
      })
    })

    map.on('moveend', emitBounds)
    map.on('mousemove', (event: MapMouseEvent) => {
      setCoordinates(`${event.lngLat.lng.toFixed(4)}°, ${event.lngLat.lat.toFixed(4)}°`)
    })
    map.on('click', (event: MapMouseEvent) => {
      if (!recordsRef.current.inspectMarine) return
      callbacksRef.current.onSelection({
        kind: 'coordinate',
        longitude: event.lngLat.lng,
        latitude: event.lngLat.lat,
      })
    })

    return () => {
      basemapController.abort()
      clearMarkers(activeMarkers.ports)
      clearMarkers(activeMarkers.earthquakes)
      liveAisLayerRef.current?.remove()
      liveAisLayerRef.current = null
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    clearMarkers(markersRef.current.ports)
    markersRef.current.ports = createPortMarkers(map, ports, portsVisible, callbacksRef)
  }, [ports, portsVisible])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    clearMarkers(markersRef.current.earthquakes)
    markersRef.current.earthquakes = createEarthquakeMarkers(
      map,
      earthquakes,
      earthquakesVisible,
      callbacksRef,
    )
  }, [earthquakes, earthquakesVisible])

  useEffect(() => {
    liveAisLayerRef.current?.update(visibleVessels)
  }, [visibleVessels])
  const aisUsable =
    liveAis?.transportConnected &&
    !liveAis.state.requiresSnapshot &&
    liveAis.state.status?.connection_state === 'CONNECTED' &&
    liveAis.state.status.availability === 'AVAILABLE' &&
    liveAis.state.status.coverage.state === 'COVERED'
  const attributions = new Map(
    visibleVessels.map((position) => [
      `${position.provenance.source_slug}:${position.provenance.attribution_text}`,
      { url: position.provenance.source_url, label: position.provenance.attribution_text },
    ]),
  )
  const observationTimes = visibleVessels
    .map((position) => Date.parse(position.observed_at))
    .sort((a, b) => a - b)
  const aisStatus = liveAis?.state.status
  const statusAge = aisStatus ? (now - Date.parse(aisStatus.emitted_at)) / 1_000 : NaN
  const cacheAge =
    aisStatus?.source_state === 'CACHED' &&
    aisStatus.cache_age_seconds !== null &&
    Number.isFinite(statusAge)
      ? Math.max(0, Math.floor(aisStatus.cache_age_seconds + Math.max(0, statusAge)))
      : null

  return (
    <div className={`map-stage ${inspectMarine ? 'is-inspecting' : ''}`}>
      <div className="map-grid" aria-hidden="true" />
      <div ref={containerRef} className="map-canvas" aria-label="OceanScope 交互式海事地图" />
      {basemapUnavailable && <div className="map-basemap-state">BASEMAP OFFLINE · WGS 84</div>}
      {liveAis && (
        <div className="map-ais-state" aria-label="AIS map layer status">
          <span>
            AIS{' '}
            {liveAis.transportConnected
              ? (liveAis.state.status?.source_state ?? 'OFFLINE')
              : 'OFFLINE'}
            {' · '}
            {liveAis.state.status?.coverage.state ?? 'DATA UNAVAILABLE'}
            {' · '}
            {aisUsable ? `${visibleVessels.length} observations` : 'positions not displayed'}
            {(liveAis.state.truncated ||
              Object.keys(liveAis.state.positions).length > LIVE_AIS_MAP_LIMIT) &&
              ' · TRUNCATED'}
          </span>
          {liveAis.state.status?.coverage.effective_at && (
            <span>Coverage effective {liveAis.state.status.coverage.effective_at}</span>
          )}
          {cacheAge !== null && <span>Cache age {cacheAge} s</span>}
          {observationTimes[0] !== undefined && (
            <span>
              Observed {new Date(observationTimes[0]).toISOString()} to{' '}
              {new Date(observationTimes.at(-1)!).toISOString()}
            </span>
          )}
          {attributions.size > 0 && (
            <span>
              Source{' '}
              {[...attributions].map(([key, attribution]) =>
                attribution.url.startsWith('https://') ? (
                  <a key={key} href={attribution.url} target="_blank" rel="noreferrer">
                    {attribution.label}
                  </a>
                ) : (
                  <span key={key}>{attribution.label} </span>
                ),
              )}
            </span>
          )}
        </div>
      )}
      <div className="coordinate-readout" aria-live="off">
        WGS 84&nbsp; {coordinates}
      </div>
    </div>
  )
}

async function attachOpenStreetMap(map: MapLibreMap, signal: AbortSignal): Promise<boolean> {
  try {
    const response = await fetch('https://tile.openstreetmap.org/0/0/0.png', {
      cache: 'force-cache',
      signal: AbortSignal.any([signal, AbortSignal.timeout(2000)]),
    })
    if (!response.ok || signal.aborted) return true
    map.addSource('osm', {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap contributors',
    })
    map.addLayer(
      {
        id: 'osm',
        type: 'raster',
        source: 'osm',
        paint: { 'raster-opacity': 0.62, 'raster-saturation': -0.7, 'raster-contrast': 0.2 },
      },
      'live-ais-vessel-points',
    )
    return false
  } catch {
    if (signal.aborted) return true
    return true
  }
}

function createPortMarkers(
  map: MapLibreMap,
  records: PortRecord[],
  visible: boolean,
  callbacks: RefObject<MapCallbacks>,
) {
  if (!visible) return []
  return records.flatMap((record) => {
    if (record.longitude === null || record.latitude === null) return []
    const element = markerElement('port', record.name)
    element.addEventListener('click', (event) => {
      event.stopPropagation()
      callbacks.current.onSelection({ kind: 'port', record })
    })
    return [new Marker({ element }).setLngLat([record.longitude, record.latitude]).addTo(map)]
  })
}

function createEarthquakeMarkers(
  map: MapLibreMap,
  records: EarthquakeRecord[],
  visible: boolean,
  callbacks: RefObject<MapCallbacks>,
) {
  if (!visible) return []
  return records.map((record) => {
    const size = Math.max(8, Math.min(22, 8 + (record.magnitude ?? 0) * 2))
    const element = markerElement('earthquake', record.place ?? record.event_id)
    element.style.width = `${size}px`
    element.style.height = `${size}px`
    element.addEventListener('click', (event) => {
      event.stopPropagation()
      callbacks.current.onSelection({ kind: 'earthquake', record })
    })
    return new Marker({ element }).setLngLat([record.longitude, record.latitude]).addTo(map)
  })
}

function markerElement(kind: 'port' | 'earthquake', label: string) {
  const element = document.createElement('button')
  element.type = 'button'
  element.className = `spatial-marker ${kind}`
  element.setAttribute('aria-label', label)
  return element
}

function clearMarkers(markers: Marker[]) {
  for (const marker of markers) marker.remove()
}
