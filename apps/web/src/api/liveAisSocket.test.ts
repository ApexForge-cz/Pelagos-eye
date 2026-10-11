import { describe, expect, it } from 'vitest'

import { liveAisSocketUrl, openLiveAisSocket, type LiveAisWebSocket } from './liveAisSocket'

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
    expect(liveAisSocketUrl(page.toString())).toBe('wss://oceanscope.example/live-ais/ws')
  })
})

describe('openLiveAisSocket', () => {
  function socketFixture() {
    const calls: Array<{ code?: number; reason?: string }> = []
    const socket: LiveAisWebSocket = {
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
      close: (code, reason) => calls.push({ code, reason }),
    }
    return { socket, calls }
  }

  it('opens the same-origin socket and forwards supported events', () => {
    const { socket } = socketFixture()
    const connected: boolean[] = []
    const events: unknown[] = []
    const controller = openLiveAisSocket({
      pageUrl: 'https://oceanscope.example/map',
      createWebSocket: (url) => {
        expect(url).toBe('wss://oceanscope.example/live-ais/ws')
        return socket
      },
      onConnectionChange: (value) => connected.push(value),
      onEvent: (event) => events.push(event),
    })

    socket.onopen?.()
    socket.onmessage?.({
      data: JSON.stringify({
        protocol_version: '1.0',
        event: 'stream.status',
        stream_epoch: 'epoch-1',
        sequence: 0,
        emitted_at: '2026-10-08T12:00:00Z',
      }),
    })

    expect(connected).toEqual([true])
    expect(events).toHaveLength(1)
    controller.close()
  })

  it('closes on malformed frames without exposing their payload', () => {
    const { socket, calls } = socketFixture()
    let malformed = 0
    let received = 0
    openLiveAisSocket({
      pageUrl: 'http://localhost:5173',
      createWebSocket: () => socket,
      onConnectionChange: () => undefined,
      onEvent: () => {
        received += 1
      },
      onMalformedFrame: () => {
        malformed += 1
      },
    })

    socket.onmessage?.({ data: '{"event":"provider.raw","secret":"TEST_DATA"}' })

    expect(malformed).toBe(1)
    expect(received).toBe(0)
    expect(calls).toEqual([{ code: 1000, reason: 'client_shutdown' }])
  })

  it('closes on abort and reports the disconnected state once', () => {
    const { socket, calls } = socketFixture()
    const connected: boolean[] = []
    const abort = new AbortController()
    openLiveAisSocket({
      pageUrl: 'http://localhost:5173',
      createWebSocket: () => socket,
      onConnectionChange: (value) => connected.push(value),
      onEvent: () => undefined,
      signal: abort.signal,
    })
    socket.onopen?.()
    abort.abort()

    expect(connected).toEqual([true, false])
    expect(calls).toEqual([{ code: 1000, reason: 'client_shutdown' }])
  })
})
