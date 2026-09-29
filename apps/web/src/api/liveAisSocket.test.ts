import { describe, expect, it } from 'vitest'

import { liveAisSocketUrl } from './liveAisSocket'

describe('liveAisSocketUrl', () => {
  it('keeps the fixed product path on the current HTTP origin', () => {
    expect(liveAisSocketUrl('http://localhost:5173/map?mmsi=999000001#selected')).toBe(
      'ws://localhost:5173/live-ais/ws',
    )
  })

  it('uses a secure product socket under HTTPS without forwarding page parameters', () => {
    expect(liveAisSocketUrl('https://oceanscope.example/ports?token=TEST_DATA#details')).toBe(
      'wss://oceanscope.example/live-ais/ws',
    )
  })

  it('rejects non-web origins', () => {
    expect(() => liveAisSocketUrl('file:///local/index.html')).toThrow('HTTP(S)')
  })

  it('does not forward URL credentials to the socket', () => {
    const page = new URL('https://oceanscope.example/map')
    page.username = 'TEST_DATA'
    page.password = 'TEST_DATA'
    expect(liveAisSocketUrl(page.toString())).toBe(
      'wss://oceanscope.example/live-ais/ws',
    )
  })
})
