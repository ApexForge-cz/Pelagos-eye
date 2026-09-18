import { afterEach, describe, expect, it, vi } from 'vitest'

import { loadSpatialSnapshot } from './spatial'

afterEach(() => vi.unstubAllGlobals())

describe('loadSpatialSnapshot', () => {
  it('propagates cancellation instead of converting it to unavailable data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_input: string | URL | Request, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () => {
              reject(new DOMException('The operation was aborted', 'AbortError'))
            })
          }),
      ),
    )
    const controller = new AbortController()
    const request = loadSpatialSnapshot(
      { west: 100, south: 10, east: 130, north: 40 },
      controller.signal,
    )

    controller.abort()

    await expect(request).rejects.toMatchObject({ name: 'AbortError' })
  })
})
