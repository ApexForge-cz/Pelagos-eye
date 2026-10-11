import { hasSupportedLiveAisEnvelope, type LiveAisServerEvent } from './liveAis'

const PRODUCT_SOCKET_PATH = '/live-ais/ws'

export function liveAisSocketUrl(pageUrl: string): string {
  const url = new URL(pageUrl)
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new TypeError('Live AIS requires an HTTP(S) product origin')
  }

  const socketUrl = new URL(PRODUCT_SOCKET_PATH, url.origin)
  socketUrl.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return socketUrl.toString()
}

export interface LiveAisWebSocket {
  onopen: (() => void) | null
  onmessage: ((event: { data: unknown }) => void) | null
  onclose: (() => void) | null
  onerror: (() => void) | null
  close: (code?: number, reason?: string) => void
}

export interface LiveAisSocketOptions {
  pageUrl: string
  onEvent: (event: LiveAisServerEvent) => void
  onConnectionChange: (connected: boolean) => void
  onMalformedFrame?: () => void
  createWebSocket?: (url: string) => LiveAisWebSocket
  signal?: AbortSignal
}

export interface LiveAisSocketController {
  close: () => void
}

/**
 * Open one same-origin product socket. Reconnection policy belongs to the page
 * controller so this transport cannot create unbounded connection attempts.
 */
export function openLiveAisSocket({
  pageUrl,
  onEvent,
  onConnectionChange,
  onMalformedFrame,
  createWebSocket = (url) => new WebSocket(url) as unknown as LiveAisWebSocket,
  signal,
}: LiveAisSocketOptions): LiveAisSocketController {
  const socket = createWebSocket(liveAisSocketUrl(pageUrl))
  let closed = false
  let connected = false

  const setConnected = (value: boolean) => {
    if (connected === value) return
    connected = value
    onConnectionChange(value)
  }

  const close = () => {
    if (closed) return
    closed = true
    socket.onopen = null
    socket.onmessage = null
    socket.onclose = null
    socket.onerror = null
    socket.close(1000, 'client_shutdown')
    setConnected(false)
    signal?.removeEventListener('abort', close)
  }

  socket.onopen = () => {
    if (!closed) setConnected(true)
  }
  socket.onmessage = (message) => {
    if (closed) return
    if (typeof message.data !== 'string') {
      onMalformedFrame?.()
      close()
      return
    }
    let value: unknown
    try {
      value = JSON.parse(message.data) as unknown
    } catch {
      onMalformedFrame?.()
      close()
      return
    }
    if (!hasSupportedLiveAisEnvelope(value)) {
      onMalformedFrame?.()
      close()
      return
    }
    onEvent(value as LiveAisServerEvent)
  }
  socket.onerror = () => setConnected(false)
  socket.onclose = () => {
    if (closed) return
    closed = true
    setConnected(false)
    signal?.removeEventListener('abort', close)
  }
  if (signal?.aborted) {
    close()
  } else {
    signal?.addEventListener('abort', close, { once: true })
  }

  return { close }
}
