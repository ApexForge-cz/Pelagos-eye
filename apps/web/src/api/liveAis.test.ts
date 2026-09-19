import { describe, expect, it } from 'vitest'

import { hasSupportedLiveAisEnvelope } from './liveAis'

describe('hasSupportedLiveAisEnvelope', () => {
  const envelope = {
    protocol_version: '1.0',
    event: 'stream.status',
    stream_epoch: 'db066135-a9e2-45c5-a17f-90c8ab436f37',
    sequence: 7,
    emitted_at: '2026-09-19T12:00:00Z',
  }

  it('recognizes the frozen v1 envelope', () => {
    expect(hasSupportedLiveAisEnvelope(envelope)).toBe(true)
  })

  it('rejects unsupported versions and event names', () => {
    expect(hasSupportedLiveAisEnvelope({ ...envelope, protocol_version: '2.0' })).toBe(false)
    expect(hasSupportedLiveAisEnvelope({ ...envelope, event: 'provider.raw' })).toBe(false)
  })

  it('rejects negative and fractional sequence values', () => {
    expect(hasSupportedLiveAisEnvelope({ ...envelope, sequence: -1 })).toBe(false)
    expect(hasSupportedLiveAisEnvelope({ ...envelope, sequence: 1.5 })).toBe(false)
  })
})
