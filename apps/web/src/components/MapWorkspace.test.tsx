import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import sharedFixture from '../../../../test-fixtures/live-ais/v1-server-events.json'
import type { LiveAisServerEvent } from '../api/liveAis'
import { createInitialLiveAisState, reduceLiveAisEvent } from '../api/liveAisState'
import { MapWorkspace } from './MapWorkspace'

const mapMock = vi.hoisted(() => ({
  on: vi.fn(),
  off: vi.fn(),
  jumpTo: vi.fn(),
  getZoom: vi.fn(() => 2),
  addControl: vi.fn(),
  getBounds: vi.fn(() => null),
  remove: vi.fn(),
}))

vi.mock('maplibre-gl', () => ({
  Map: vi.fn(function () {
    return mapMock
  }),
  NavigationControl: vi.fn(),
  FullscreenControl: vi.fn(),
  AttributionControl: vi.fn(),
  Marker: vi.fn(),
  setWorkerUrl: vi.fn(),
}))

vi.mock('./liveAisVesselLayer', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./liveAisVesselLayer')>()),
  mountLiveAisVesselLayer: vi.fn(() => ({ update: vi.fn(), remove: vi.fn() })),
}))

const events = sharedFixture.events as LiveAisServerEvent[]
const state = events.slice(0, 2).reduce(reduceLiveAisEvent, createInitialLiveAisState())
const position = state.positions['999000001']!
const props = {
  ports: [],
  earthquakes: [],
  portsVisible: true,
  earthquakesVisible: true,
  inspectMarine: false,
  onBoundsChange: vi.fn(),
  onSelection: vi.fn(),
  selectedVesselMmsi: position.mmsi,
  liveAis: { state, transportConnected: true },
}

function emit(type: string, event: object = {}) {
  for (const [name, callback] of mapMock.on.mock.calls) {
    if (name === type) (callback as (event: object) => void)(event)
  }
}

function mount() {
  const view = render(<MapWorkspace {...props} />)
  act(() => emit('load'))
  return view
}

describe('selected AIS observation camera', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-20T12:00:10Z'))
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('', { status: 503 }))),
    )
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('locates without animation, follows exact updates, and stops on manual movement', () => {
    const { rerender, unmount } = mount()
    expect(mapMock.jumpTo).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '定位船舶' }))
    expect(mapMock.jumpTo).toHaveBeenLastCalledWith({ center: [-74.01, 40.7], zoom: 7 })
    fireEvent.click(screen.getByRole('button', { name: '跟随船舶' }))
    expect(screen.getByRole('button', { name: '停止跟随' })).toHaveAttribute('aria-pressed', 'true')

    const updated = { ...position, longitude: -73.99, latitude: 40.71 }
    rerender(
      <MapWorkspace
        {...props}
        liveAis={{
          state: { ...state, positions: { [position.mmsi]: updated } },
          transportConnected: true,
        }}
      />,
    )
    expect(mapMock.jumpTo).toHaveBeenLastCalledWith({ center: [-73.99, 40.71], zoom: 7 })
    act(() => emit('movestart'))
    expect(screen.getByRole('button', { name: '停止跟随' })).toBeInTheDocument()
    act(() => emit('movestart', { originalEvent: new MouseEvent('mousedown') }))
    expect(screen.getByRole('button', { name: '跟随船舶' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    const calls = mapMock.jumpTo.mock.calls.length
    rerender(<MapWorkspace {...props} />)
    expect(mapMock.jumpTo).toHaveBeenCalledTimes(calls)
    unmount()
    expect(mapMock.off).toHaveBeenCalledWith('movestart', expect.any(Function))
  })

  it('preserves a closer zoom and stops when the user toggles follow off', () => {
    const { rerender } = mount()
    mapMock.getZoom.mockReturnValueOnce(10)
    fireEvent.click(screen.getByRole('button', { name: '定位船舶' }))
    expect(mapMock.jumpTo).toHaveBeenLastCalledWith({ center: [-74.01, 40.7], zoom: 10 })
    fireEvent.click(screen.getByRole('button', { name: '跟随船舶' }))
    fireEvent.click(screen.getByRole('button', { name: '停止跟随' }))
    const calls = mapMock.jumpTo.mock.calls.length
    rerender(
      <MapWorkspace
        {...props}
        liveAis={{
          state: { ...state, positions: { [position.mmsi]: { ...position, longitude: -73.99 } } },
          transportConnected: true,
        }}
      />,
    )
    expect(mapMock.jumpTo).toHaveBeenCalledTimes(calls)
  })

  it('does not offer camera controls before a valid observation is selected', () => {
    render(<MapWorkspace {...props} selectedVesselMmsi={null} />)
    act(() => emit('load'))
    expect(screen.queryByRole('button', { name: '定位船舶' })).not.toBeInTheDocument()
    expect(mapMock.jumpTo).not.toHaveBeenCalled()
  })

  it.each(['disconnect', 'gap', 'no coverage', 'expired cache', 'outside bounds'] as const)(
    'removes controls on %s and never resumes follow automatically',
    (reason) => {
      const { rerender } = mount()
      fireEvent.click(screen.getByRole('button', { name: '跟随船舶' }))
      const invalid = structuredClone(state)
      if (reason === 'gap') invalid.requiresSnapshot = true
      if (reason === 'no coverage') invalid.status!.coverage.state = 'NO COVERAGE'
      if (reason === 'expired cache') {
        invalid.status!.source_state = 'CACHED'
        invalid.status!.cache_age_seconds = 301
      }
      if (reason === 'outside bounds') invalid.positions[position.mmsi]!.latitude = 60
      const calls = mapMock.jumpTo.mock.calls.length
      rerender(
        <MapWorkspace
          {...props}
          liveAis={{ state: invalid, transportConnected: reason !== 'disconnect' }}
        />,
      )
      expect(screen.queryByRole('button', { name: '定位船舶' })).not.toBeInTheDocument()
      rerender(<MapWorkspace {...props} />)
      expect(screen.getByRole('button', { name: '跟随船舶' })).toHaveAttribute(
        'aria-pressed',
        'false',
      )
      expect(mapMock.jumpTo).toHaveBeenCalledTimes(calls)
    },
  )

  it('expires a silent observation using the existing clock', async () => {
    mount()
    fireEvent.click(screen.getByRole('button', { name: '跟随船舶' }))
    const calls = mapMock.jumpTo.mock.calls.length
    await act(async () => vi.advanceTimersByTimeAsync(5 * 60_000))
    expect(screen.queryByRole('button', { name: '停止跟随' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '定位船舶' })).not.toBeInTheDocument()
    expect(mapMock.jumpTo).toHaveBeenCalledTimes(calls)
  })

  it.each(['selection', 'epoch', 'replacement snapshot'] as const)(
    'requires explicit follow again after changing %s',
    (reason) => {
      const { rerender } = mount()
      fireEvent.click(screen.getByRole('button', { name: '跟随船舶' }))
      const next = structuredClone(state)
      const mmsi = reason === 'selection' ? '999000002' : position.mmsi
      if (reason === 'selection') next.positions = { [mmsi]: { ...position, mmsi } }
      if (reason === 'epoch') next.streamEpoch = 'new-test-epoch'
      if (reason === 'replacement snapshot') next.snapshotSequence = 10
      const calls = mapMock.jumpTo.mock.calls.length
      rerender(
        <MapWorkspace
          {...props}
          selectedVesselMmsi={mmsi}
          liveAis={{ state: next, transportConnected: true }}
        />,
      )
      expect(screen.getByRole('button', { name: '跟随船舶' })).toHaveAttribute(
        'aria-pressed',
        'false',
      )
      expect(mapMock.jumpTo).toHaveBeenCalledTimes(calls)
    },
  )
})
