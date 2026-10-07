import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import sharedFixture from '../../../../test-fixtures/live-ais/v1-server-events.json'

import type { LiveAisPosition, LiveAisServerEvent } from '../api/liveAis'
import { createInitialLiveAisState, reduceLiveAisEvent } from '../api/liveAisState'
import { ACCESSIBLE_AIS_LIST_LIMIT, LiveAisVesselInspector } from './LiveAisVesselInspector'

const events = sharedFixture.events as LiveAisServerEvent[]
const state = events.slice(0, 2).reduce(reduceLiveAisEvent, createInitialLiveAisState())

describe('LiveAisVesselInspector', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-20T12:00:10Z'))
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('does not expose stale positions when transport is disconnected', () => {
    render(
      <LiveAisVesselInspector
        state={state}
        transportConnected={false}
        selectedMmsi={null}
        onSelect={vi.fn()}
      />,
    )

    expect(screen.getByText('DATA UNAVAILABLE')).toBeInTheDocument()
    expect(screen.getByText(/WebSocket is disconnected/)).toBeInTheDocument()
    expect(screen.queryByText('MMSI 999000001')).not.toBeInTheDocument()
  })

  it('selects a TEST DATA observation and presents units, provenance, and limitations', () => {
    const onSelect = vi.fn()
    const { rerender } = render(
      <LiveAisVesselInspector
        state={state}
        transportConnected
        selectedMmsi={null}
        onSelect={onSelect}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /MMSI 999000001/ }))
    expect(onSelect).toHaveBeenCalledWith(state.positions['999000001'])

    rerender(
      <LiveAisVesselInspector
        state={state}
        transportConnected
        selectedMmsi="999000001"
        onSelect={onSelect}
      />,
    )
    expect(
      screen.getByRole('region', { name: 'Selected live AIS observation' }),
    ).toBeInTheDocument()
    expect(screen.getByText('40.70000°, -74.01000° · WGS 84')).toBeInTheDocument()
    expect(screen.getByText('12.4 kn')).toBeInTheDocument()
    expect(screen.getByText('91.2 °')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'TEST DATA only' })).toHaveAttribute(
      'href',
      'https://example.test/live-ais',
    )
    expect(screen.getByText('Quality flags: TEST DATA')).toBeInTheDocument()
    expect(screen.getByText(/fallible observations/)).toBeInTheDocument()
  })

  it('keeps no coverage distinct from an empty covered result', () => {
    const noCoverage = {
      ...state,
      status: {
        ...state.status!,
        coverage: {
          ...state.status!.coverage,
          state: 'NO COVERAGE' as const,
          description: 'TEST DATA outside the bounded region.',
          bounds: null,
        },
      },
    }
    const { rerender } = render(
      <LiveAisVesselInspector
        state={noCoverage}
        transportConnected
        selectedMmsi={null}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('NO COVERAGE')).toBeInTheDocument()

    rerender(
      <LiveAisVesselInspector
        state={{ ...state, positions: {} }}
        transportConnected
        selectedMmsi={null}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('No current observations')).toBeInTheDocument()
    expect(screen.getByText(/does not prove vessel absence/)).toBeInTheDocument()
  })

  it('does not describe a disconnected or expired cached source as an empty region', () => {
    const disconnected = {
      ...state,
      status: { ...state.status!, connection_state: 'RECONNECTING' as const },
    }
    const { rerender } = render(
      <LiveAisVesselInspector
        state={disconnected}
        transportConnected
        selectedMmsi={null}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('DATA UNAVAILABLE')).toBeInTheDocument()
    expect(screen.queryByText('No current observations')).not.toBeInTheDocument()

    rerender(
      <LiveAisVesselInspector
        state={{
          ...state,
          status: { ...state.status!, source_state: 'CACHED', cache_age_seconds: 301 },
        }}
        transportConnected
        selectedMmsi={null}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText(/cache is older than/)).toBeInTheDocument()
  })

  it('bounds the accessible list without changing the full observation count', () => {
    const base = state.positions['999000001']!
    const positions = Object.fromEntries(
      Array.from({ length: ACCESSIBLE_AIS_LIST_LIMIT + 5 }, (_, index) => {
        const mmsi = String(100_000_000 + index)
        return [mmsi, { ...base, mmsi } satisfies LiveAisPosition]
      }),
    )
    render(
      <LiveAisVesselInspector
        state={{ ...state, positions, truncated: true }}
        transportConnected
        selectedMmsi={null}
        onSelect={vi.fn()}
      />,
    )

    expect(screen.getAllByRole('button')).toHaveLength(ACCESSIBLE_AIS_LIST_LIMIT)
    expect(screen.getByText('Showing 100 of 105 current observations.')).toBeInTheDocument()
    expect(screen.getByText(/TRUNCATED/)).toBeInTheDocument()
  })

  it('hides the list and selection as soon as a fresh snapshot is required', () => {
    render(
      <LiveAisVesselInspector
        state={{ ...state, requiresSnapshot: true }}
        transportConnected
        selectedMmsi="999000001"
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('FRESH SNAPSHOT REQUIRED')).toBeInTheDocument()
    expect(
      screen.queryByRole('region', { name: 'Selected live AIS observation' }),
    ).not.toBeInTheDocument()
  })

  it('removes an observation after its five-minute display window without a new event', async () => {
    render(
      <LiveAisVesselInspector
        state={state}
        transportConnected
        selectedMmsi={null}
        onSelect={vi.fn()}
      />,
    )
    expect(screen.getByText('MMSI 999000001')).toBeInTheDocument()

    await act(async () => vi.advanceTimersByTimeAsync(5 * 60_000))

    expect(screen.queryByText('MMSI 999000001')).not.toBeInTheDocument()
    expect(screen.getByText('No current observations')).toBeInTheDocument()
  })
})
