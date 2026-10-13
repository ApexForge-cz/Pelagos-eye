import '@testing-library/jest-dom/vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { LiveAisServerEvent } from './api/liveAis'

const liveAisSocketMock = vi.hoisted(() => ({ open: vi.fn() }))

vi.mock('./api/liveAisSocket', () => ({
  openLiveAisSocket: liveAisSocketMock.open,
}))

import { App } from './App'

vi.mock('./components/MapWorkspace', async () => {
  const React = await import('react')
  return {
    MapWorkspace: ({
      onBoundsChange,
      onSelection,
    }: {
      onBoundsChange: (bounds: { west: number; south: number; east: number; north: number }) => void
      onSelection: (selection: unknown) => void
    }) => {
      React.useEffect(() => {
        onBoundsChange({ west: 100, south: 10, east: 130, north: 40 })
      }, [onBoundsChange])
      return (
        <div aria-label="OceanScope 交互式海事地图">
          <button
            type="button"
            onClick={() => onSelection({ kind: 'coordinate', longitude: 120.5, latitude: 30.25 })}
          >
            TEST DATA coordinate
          </button>
        </div>
      )
    },
  }
})

vi.mock('./components/GlobeWorkspace', () => ({
  GlobeWorkspace: ({ onUnavailable }: { onUnavailable: () => void }) => (
    <div aria-label="OceanScope 交互式三维地球">
      <button type="button" onClick={onUnavailable}>
        TEST DATA WebGL unavailable
      </button>
    </div>
  ),
}))

const checkedAt = '2026-09-18T03:00:00Z'
const provenance = {
  source_slug: 'test-source',
  source_display_name: 'TEST DATA Source',
  source_url: 'https://example.test/source.csv',
  attribution_text: 'TEST DATA attribution',
  data_version: 'TEST-DATA-1',
  schema_version: 'test-schema-v1',
  published_at: checkedAt,
  retrieved_at: checkedAt,
  ingested_at: checkedAt,
  normalized_at: checkedAt,
  source_state: 'LIVE',
  cache_age_seconds: null,
}

const systemStatus = {
  service: 'oceanscope-api',
  version: '0.1.0',
  overall_state: 'READY',
  checked_at: checkedAt,
  database: { state: 'LIVE', detail: 'Database connectivity verified' },
}

const sourceCatalog = {
  generated_at: checkedAt,
  sources: [
    {
      slug: 'unece-unlocode',
      display_name: 'UNECE UN/LOCODE',
      official_url: 'https://unece.org/trade/cefact/unlocode-code-list-country-and-territory',
      terms_url: null,
      attribution_text: 'TEST DATA attribution',
      license_identifier: null,
      redistribution_status: 'allowed',
      state: 'LIVE',
      availability: 'AVAILABLE',
      has_usable_data: true,
      cache_age_seconds: null,
      freshness: {
        age_seconds: 120,
        live_ttl_seconds: 86400,
        delayed_ttl_seconds: 86400,
        cache_ttl_seconds: null,
      },
      latest_run: null,
      latest_usable_run: null,
      latest_version: null,
      quality_issues: [],
    },
  ],
}

const portResponse = {
  generated_at: checkedAt,
  total: 1,
  limit: 100,
  offset: 0,
  records: [
    {
      id: '00000000-0000-0000-0000-000000000001',
      source_record_id: 'TST',
      record_type: 'unlocode',
      name: 'TEST DATA Port',
      country_code: 'TS',
      un_locode: 'TSTST',
      longitude: 120.5,
      latitude: 30.25,
      coordinate_accuracy: 'published_degrees_minutes',
      function_code: '1-------',
      source_status: 'AA',
      source_updated_value: '2609',
      quality_flags: ['coverage_unknown'],
      provenance,
    },
  ],
}

beforeEach(() => {
  liveAisSocketMock.open.mockReset()
  liveAisSocketMock.open.mockReturnValue({ close: vi.fn() })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('loads the viewport and exposes real record provenance outside the map', async () => {
    let portRequests = 0
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path =
          typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
        let body: object = { generated_at: checkedAt, total: 0, limit: 100, offset: 0, records: [] }
        if (path.includes('/system/status')) body = systemStatus
        if (path.includes('/data/sources')) body = sourceCatalog
        if (path.includes('/ports?')) {
          portRequests += 1
          body = portResponse
        }
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
      }),
    )

    render(<App />)

    expect(screen.getByText('OceanScope')).toBeInTheDocument()
    expect(screen.getByText('REAL DATA')).toBeInTheDocument()
    const portButton = await screen.findByRole('button', { name: /TEST DATA Port/ })
    fireEvent.click(portButton)
    expect(await screen.findByText('TSTST · TS')).toBeInTheDocument()
    expect(screen.getByText(/TEST DATA Source · LIVE/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'TEST DATA attribution' })).toHaveAttribute(
      'href',
      'https://example.test/source.csv',
    )
    expect(screen.getByText(/coverage_unknown/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '刷新数据' }))
    await waitFor(() => expect(portRequests).toBe(2))
  })

  it('shows DATA UNAVAILABLE rather than placeholder values when APIs fail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('', { status: 503 }))),
    )

    render(<App />)

    expect((await screen.findAllByText('DATA UNAVAILABLE')).length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('OceanScope 交互式海事地图')).toHaveLength(1)
  })

  it('labels an empty exact-coordinate forecast as NO COVERAGE', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path =
          typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
        let body: object = { generated_at: checkedAt, total: 0, limit: 100, offset: 0, records: [] }
        if (path.includes('/system/status')) body = systemStatus
        if (path.includes('/data/sources')) body = sourceCatalog
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
      }),
    )

    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'TEST DATA coordinate' }))

    expect(await screen.findByText(/NO COVERAGE/)).toBeInTheDocument()
  })

  it('switches to 3D and explicitly falls back to 2D when WebGL is unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path =
          typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
        let body: object = { generated_at: checkedAt, total: 0, limit: 100, offset: 0, records: [] }
        if (path.includes('/system/status')) body = systemStatus
        if (path.includes('/data/sources')) body = sourceCatalog
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
      }),
    )

    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: '3D' }))
    expect(await screen.findByLabelText('OceanScope 交互式三维地球')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'TEST DATA WebGL unavailable' }))
    expect(await screen.findByLabelText('OceanScope 交互式海事地图')).toBeInTheDocument()
    expect(screen.getByText(/3D WEBGL 不可用/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '2D' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('connects product events to the status and accessible vessel inspector', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path =
          typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
        let body: object = { generated_at: checkedAt, total: 0, limit: 100, offset: 0, records: [] }
        if (path.includes('/system/status')) body = systemStatus
        if (path.includes('/data/sources')) body = sourceCatalog
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
      }),
    )

    render(<App />)
    const options = liveAisSocketMock.open.mock.calls[0]?.[0] as
      | {
          onConnectionChange: (connected: boolean) => void
          onEvent: (event: LiveAisServerEvent) => void
        }
      | undefined
    expect(options).toBeDefined()
    const now = new Date().toISOString()
    const [snapshot, statusEvent] = liveAisTestEvents(now)

    act(() => {
      options!.onConnectionChange(true)
      options!.onEvent(snapshot)
      options!.onEvent(statusEvent)
    })

    expect(await screen.findByText('AVAILABLE')).toBeInTheDocument()
    const vessel = screen.getByRole('button', { name: /MMSI 230000001/ })
    fireEvent.click(vessel)
    expect(screen.getByRole('heading', { name: 'MMSI 230000001' })).toBeInTheDocument()
    expect(screen.getByText(/AIS identity and dynamic fields are fallible/)).toBeInTheDocument()

    act(() => options!.onConnectionChange(false))
    expect(screen.queryByText('AVAILABLE')).not.toBeInTheDocument()
    expect(screen.getAllByText('DATA UNAVAILABLE').length).toBeGreaterThan(0)
  })
})

function liveAisTestEvents(now: string): [LiveAisServerEvent, LiveAisServerEvent] {
  const coverage = {
    state: 'COVERED' as const,
    description: 'TEST DATA fixed Gulf coverage.',
    bounds: { west: 23.5, south: 59.5, east: 26.5, north: 60.5 },
    effective_at: now,
  }
  const position = {
    observation_id: 'TEST-DATA-observation',
    mmsi: '230000001',
    observed_at: now,
    longitude: 24.5,
    latitude: 60,
    speed_over_ground_knots: 10,
    course_over_ground_deg: 90,
    true_heading_deg: 90,
    navigational_status_code: null,
    quality_flags: ['TEST DATA'],
    provenance: {
      source_slug: 'test-source',
      source_url: 'https://example.test/live-ais',
      attribution_text: 'TEST DATA attribution',
      data_version: 'TEST-DATA-1',
      schema_version: 'test-v1',
      provider_message_type: 'TEST DATA',
      source_event_id: 'TEST-DATA-event',
      ingested_at: now,
      normalized_at: now,
      source_state: 'LIVE' as const,
      cache_age_seconds: null,
    },
  }
  return [
    {
      protocol_version: '1.0',
      event: 'vessel.snapshot',
      stream_epoch: '11111111-1111-4111-8111-111111111111',
      sequence: 0,
      emitted_at: now,
      availability: 'AVAILABLE',
      source_state: 'LIVE',
      cache_age_seconds: null,
      coverage,
      positions: [position],
      truncated: false,
    },
    {
      protocol_version: '1.0',
      event: 'stream.status',
      stream_epoch: '11111111-1111-4111-8111-111111111111',
      sequence: 1,
      emitted_at: now,
      connection_state: 'CONNECTED',
      source_state: 'LIVE',
      cache_age_seconds: null,
      availability: 'AVAILABLE',
      coverage,
      last_observation_at: now,
      retry_at: null,
      detail: 'TEST DATA stream connected.',
    },
  ]
}
