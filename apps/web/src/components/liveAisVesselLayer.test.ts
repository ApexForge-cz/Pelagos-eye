import { describe, expect, it, vi } from 'vitest'
import type { Map as MapLibreMap, MapLayerMouseEvent } from 'maplibre-gl'

import sharedFixture from '../../../../test-fixtures/live-ais/v1-server-events.json'

import type { LiveAisServerEvent } from '../api/liveAis'
import { createInitialLiveAisState, reduceLiveAisEvent } from '../api/liveAisState'
import { mountLiveAisVesselLayer, visibleLiveAisPositions } from './liveAisVesselLayer'

const events = sharedFixture.events as LiveAisServerEvent[]
const state = events.slice(0, 2).reduce(reduceLiveAisEvent, createInitialLiveAisState())
const now = Date.parse('2026-09-20T12:00:10Z')

describe('visibleLiveAisPositions', () => {
  it('uses only a covered, continuous, currently connected TEST DATA snapshot', () => {
    expect(visibleLiveAisPositions(state, now, true)).toHaveLength(1)
    expect(visibleLiveAisPositions(state, now, false)).toEqual([])
    expect(visibleLiveAisPositions({ ...state, requiresSnapshot: true }, now, true)).toEqual([])
    expect(visibleLiveAisPositions({ ...state, status: null }, now, true)).toEqual([])
    expect(
      visibleLiveAisPositions(
        { ...state, status: { ...state.status!, connection_state: 'DISCONNECTED' } },
        now,
        true,
      ),
    ).toEqual([])
    expect(
      visibleLiveAisPositions(
        { ...state, status: { ...state.status!, availability: 'DATA UNAVAILABLE' } },
        now,
        true,
      ),
    ).toEqual([])
    expect(
      visibleLiveAisPositions(
        {
          ...state,
          status: {
            ...state.status!,
            coverage: { ...state.status!.coverage, state: 'NO COVERAGE' },
          },
        },
        now,
        true,
      ),
    ).toEqual([])
  })

  it('expires old observations and rejects coordinates outside effective coverage', () => {
    expect(visibleLiveAisPositions(state, now + 5 * 60_000, true)).toEqual([])
    const position = state.positions['999000001']!
    expect(
      visibleLiveAisPositions(
        { ...state, positions: { [position.mmsi]: { ...position, latitude: 60 } } },
        now,
        true,
      ),
    ).toEqual([])
    expect(
      visibleLiveAisPositions(
        { ...state, positions: { [position.mmsi]: { ...position, observed_at: 'invalid' } } },
        now,
        true,
      ),
    ).toEqual([])
  })

  it('limits selected observations to 5,000 without changing coordinate values', () => {
    const position = state.positions['999000001']!
    const positions = Object.fromEntries(
      Array.from({ length: 5_010 }, (_, index) => {
        const mmsi = String(100_000_000 + index)
        return [mmsi, { ...position, mmsi }]
      }),
    )
    const visible = visibleLiveAisPositions({ ...state, positions }, now, true)
    expect(visible).toHaveLength(5_000)
    expect(visible[0]?.longitude).toBe(-74.01)
    expect(visible[0]?.mmsi).toBe('100000000')
  })

  it('rejects expired CACHED status and clears after a stream gap', () => {
    expect(
      visibleLiveAisPositions(
        { ...state, status: { ...state.status!, source_state: 'CACHED', cache_age_seconds: 301 } },
        now,
        true,
      ),
    ).toEqual([])
    const gap = events[3]!
    expect(visibleLiveAisPositions(reduceLiveAisEvent(state, gap), now, true)).toEqual([])
  })

  it('ages cached status using the clock, not only the last reported cache age', () => {
    const cached = {
      ...state,
      status: {
        ...state.status!,
        source_state: 'CACHED' as const,
        cache_age_seconds: 280,
      },
    }
    expect(visibleLiveAisPositions(cached, now, true)).toHaveLength(1)
    expect(visibleLiveAisPositions(cached, now + 15_000, true)).toEqual([])
  })
})

describe('mountLiveAisVesselLayer', () => {
  it('replaces features, selects the latest TEST DATA position and removes map resources', () => {
    const setData = vi.fn()
    const addSource = vi.fn()
    const addLayer = vi.fn()
    const on = vi.fn()
    const off = vi.fn()
    const removeLayer = vi.fn()
    const removeSource = vi.fn()
    const map = {
      addSource,
      addLayer,
      on,
      off,
      removeLayer,
      removeSource,
      getSource: vi.fn(() => ({ setData })),
      getLayer: vi.fn(() => ({})),
    } as unknown as MapLibreMap
    const selected = vi.fn()
    const layer = mountLiveAisVesselLayer(map, selected)
    const original = state.positions['999000001']!
    const updated = { ...original, longitude: -74.02 }
    layer.update([original])
    layer.update([updated])
    expect(setData).toHaveBeenLastCalledWith({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [-74.02, 40.7] },
          properties: { mmsi: original.mmsi },
        },
      ],
    })
    const click = on.mock.calls[0]?.[2] as (event: MapLayerMouseEvent) => void
    click({ features: [{ properties: { mmsi: original.mmsi } }] } as unknown as MapLayerMouseEvent)
    expect(selected).toHaveBeenCalledWith(updated)
    layer.update([])
    click({ features: [{ properties: { mmsi: original.mmsi } }] } as unknown as MapLayerMouseEvent)
    expect(selected).toHaveBeenCalledTimes(1)
    layer.remove()
    expect(off).toHaveBeenCalledWith('click', 'live-ais-vessel-points', click)
    expect(removeLayer).toHaveBeenCalledOnce()
    expect(removeSource).toHaveBeenCalledOnce()
  })
})
