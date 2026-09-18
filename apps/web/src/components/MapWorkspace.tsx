import { useEffect, useRef, useState, type RefObject } from 'react'
import {
  AttributionControl,
  FullscreenControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  type MapMouseEvent,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

import type { EarthquakeRecord, PortRecord, ViewportBounds } from '../api/spatial'

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
  const [coordinates, setCoordinates] = useState('0.0000°, 0.0000°')
  const [basemapUnavailable, setBasemapUnavailable] = useState(false)

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

  return (
    <div className={`map-stage ${inspectMarine ? 'is-inspecting' : ''}`}>
      <div className="map-grid" aria-hidden="true" />
      <div ref={containerRef} className="map-canvas" aria-label="OceanScope 交互式海事地图" />
      {basemapUnavailable && <div className="map-basemap-state">BASEMAP OFFLINE · WGS 84</div>}
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
    map.addLayer({
      id: 'osm',
      type: 'raster',
      source: 'osm',
      paint: { 'raster-opacity': 0.62, 'raster-saturation': -0.7, 'raster-contrast': 0.2 },
    })
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
