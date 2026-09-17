import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'

const systemStatus = {
  service: 'oceanscope-api',
  version: '0.1.0',
  overall_state: 'READY',
  checked_at: '2026-09-17T14:00:00Z',
  database: { state: 'LIVE', detail: 'Database connectivity verified' },
}

const sourceCatalog = {
  generated_at: '2026-09-17T14:00:00Z',
  sources: [
    {
      slug: 'noaa-marinecadastre-ais',
      display_name: 'NOAA MarineCadastre Historical AIS',
      official_url: 'https://marinecadastre.gov/ais/',
      terms_url: 'https://example.test/terms',
      attribution_text: 'TEST DATA attribution',
      license_identifier: null,
      redistribution_status: 'restricted',
      state: 'CACHED',
      availability: 'AVAILABLE',
      has_usable_data: true,
      cache_age_seconds: 1501,
      freshness: {
        age_seconds: 1501,
        live_ttl_seconds: 86400,
        delayed_ttl_seconds: 86400,
        cache_ttl_seconds: null,
      },
      latest_run: {
        id: '00000000-0000-0000-0000-000000000001',
        status: 'partial',
        source_state: 'CACHED',
        cache_age_seconds: 1381,
        started_at: new Date(Date.now() - 120_000).toISOString(),
        finished_at: '2026-09-17T14:00:00Z',
        records_received: 100,
        records_accepted: 50,
        records_rejected: 0,
      },
      latest_usable_run: {
        id: '00000000-0000-0000-0000-000000000001',
        status: 'partial',
        source_state: 'CACHED',
        cache_age_seconds: 1381,
        started_at: new Date(Date.now() - 120_000).toISOString(),
        finished_at: '2026-09-17T14:00:00Z',
        records_received: 100,
        records_accepted: 50,
        records_rejected: 0,
      },
      latest_version: {
        data_version: 'TEST-DATA-v1',
        schema_version: 'TEST-DATA-schema',
        source_url: 'https://example.test/archive',
        published_at: null,
        retrieved_at: '2026-09-17T13:58:00Z',
      },
      quality_issues: [
        {
          code: 'coverage_unknown',
          severity: 'warning',
          record_count: 50,
          message: 'TEST DATA capped rows',
        },
      ],
    },
  ],
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders real source state, freshness, and quality evidence from the APIs', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string | URL | Request) => {
        const path =
          typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
        const body = path.includes('/system/status') ? systemStatus : sourceCatalog
        return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))
      }),
    )

    render(<App />)

    expect(screen.getByText(/正在读取/)).toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { name: 'NOAA MarineCadastre Historical AIS' }),
    ).toBeInTheDocument()
    expect(screen.getByText('CACHED')).toBeInTheDocument()
    expect(screen.getByText('coverage_unknown')).toBeInTheDocument()
    expect(screen.getByText('50 / 0')).toBeInTheDocument()
    expect(screen.getByText(/25 分钟/)).toBeInTheDocument()
  })

  it('shows DATA UNAVAILABLE rather than placeholder values when a request fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('', { status: 503 }))),
    )

    render(<App />)

    expect(await screen.findByRole('alert')).toHaveTextContent('DATA UNAVAILABLE')
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument()
  })
})
