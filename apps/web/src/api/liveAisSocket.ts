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
