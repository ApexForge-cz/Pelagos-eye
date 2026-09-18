import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

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
})
