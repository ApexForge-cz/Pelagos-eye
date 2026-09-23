import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { LiveAisGapEvent, LiveAisStatusEvent } from '../api/liveAis'

import { LiveAisStatusPanel } from './LiveAisStatusPanel'

const status: LiveAisStatusEvent = {
  protocol_version: '1.0',
  event: 'stream.status',
  stream_epoch: 'test-epoch',
  sequence: 1,
  emitted_at: '2026-09-20T12:00:03Z',
  connection_state: 'CONNECTED',
  source_state: 'LIVE',
  cache_age_seconds: null,
  availability: 'AVAILABLE',
  coverage: {
    state: 'COVERED',
    description: 'TEST DATA bounded contract region.',
    bounds: null,
    effective_at: '2026-09-20T12:00:00Z',
  },
  last_observation_at: '2026-09-20T12:00:00Z',
  retry_at: null,
  detail: 'TEST DATA stream connected.',
}

const gap: LiveAisGapEvent = {
  protocol_version: '1.0',
  event: 'stream.gap',
  stream_epoch: 'test-epoch',
  sequence: 2,
  emitted_at: '2026-09-20T12:00:40Z',
  gap_started_at: '2026-09-20T12:00:08Z',
  gap_ended_at: '2026-09-20T12:00:38Z',
  reason: 'provider_disconnect',
  dropped_updates: null,
  replay_available: false,
  detail: 'TEST DATA continuity gap.',
}

describe('LiveAisStatusPanel', () => {
  it('shows honest unavailable state before a worker event exists', () => {
    render(<LiveAisStatusPanel status={null} />)

    expect(screen.getAllByText('DATA UNAVAILABLE')).toHaveLength(3)
    expect(screen.getByText('DISCONNECTED')).toBeInTheDocument()
    expect(screen.getByText(/Phase 4 remains planned/)).toBeInTheDocument()
  })

  it('renders connected status and continuity gaps without raw payloads', () => {
    render(<LiveAisStatusPanel status={status} gap={gap} />)

    expect(screen.getByText('AVAILABLE')).toBeInTheDocument()
    expect(screen.getByText('CONNECTED')).toBeInTheDocument()
    expect(screen.getByText('LIVE')).toBeInTheDocument()
    expect(screen.getByText('COVERED')).toBeInTheDocument()
    expect(screen.getByText('STREAM GAP')).toBeInTheDocument()
    expect(screen.getByText('provider disconnect')).toBeInTheDocument()
    expect(screen.getByText('Fresh snapshot required')).toBeInTheDocument()
    expect(screen.queryByText('test-epoch')).not.toBeInTheDocument()
  })
})
