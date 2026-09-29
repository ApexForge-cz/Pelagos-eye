import { describe, expect, it } from 'vitest'

import sharedFixture from '../../../../test-fixtures/live-ais/v1-server-events.json'

import type { LiveAisServerEvent } from './liveAis'
import { createInitialLiveAisState, reduceLiveAisEvent } from './liveAisState'

const events = sharedFixture.events as LiveAisServerEvent[]
const snapshot = requiredEvent(0)
const status = requiredEvent(1)
const position = requiredEvent(2)
const gap = requiredEvent(3)

describe('reduceLiveAisEvent', () => {
  it('requires a snapshot before accepting incremental events', () => {
    const state = reduceLiveAisEvent(createInitialLiveAisState(), status)

    expect(state.requiresSnapshot).toBe(true)
    expect(state.positions).toEqual({})
    expect(state.status?.event).toBe('stream.status')
    expect(state.continuityIssue).toBe('snapshot_required')
  })

  it('builds latest position state from a snapshot and position update', () => {
    const afterSnapshot = reduceLiveAisEvent(createInitialLiveAisState(), snapshot)
    const afterStatus = reduceLiveAisEvent(afterSnapshot, status)
    const state = reduceLiveAisEvent(afterStatus, position)

    expect(state.requiresSnapshot).toBe(false)
    expect(state.lastSequence).toBe(2)
    expect(Object.keys(state.positions)).toEqual(['999000001'])
    expect(state.positions['999000001']?.observation_id).toBe('test:position:0002')
    expect(state.status?.connection_state).toBe('CONNECTED')
  })

  it('clears positions and requires a fresh snapshot after a gap', () => {
    const beforeGap = events.slice(0, 3).reduce(reduceLiveAisEvent, createInitialLiveAisState())
    const state = reduceLiveAisEvent(beforeGap, gap)

    expect(state.requiresSnapshot).toBe(true)
    expect(state.positions).toEqual({})
    expect(state.gap?.reason).toBe('provider_disconnect')
    expect(state.gap?.replay_available).toBe(false)
  })

  it('rejects skipped sequences and changed epochs until a snapshot arrives', () => {
    const afterSnapshot = reduceLiveAisEvent(createInitialLiveAisState(), snapshot)
    const skipped = reduceLiveAisEvent(afterSnapshot, { ...position, sequence: 9 })

    expect(skipped.requiresSnapshot).toBe(true)
    expect(skipped.positions).toEqual({})
    expect(skipped.continuityIssue).toBe('sequence_discontinuity')

    const changedEpoch = reduceLiveAisEvent(afterSnapshot, {
      ...status,
      stream_epoch: 'new-test-epoch',
    })
    expect(changedEpoch.requiresSnapshot).toBe(true)
    expect(changedEpoch.continuityIssue).toBe('stream_epoch_changed')
  })

  it('does not mutate the previous state', () => {
    const afterSnapshot = reduceLiveAisEvent(createInitialLiveAisState(), snapshot)
    const originalPosition = afterSnapshot.positions['999000001']

    const next = reduceLiveAisEvent(afterSnapshot, position)

    expect(afterSnapshot.positions['999000001']).toBe(originalPosition)
    expect(next.positions).not.toBe(afterSnapshot.positions)
  })
})

function requiredEvent(index: number): LiveAisServerEvent {
  const event = events[index]
  if (!event) throw new Error(`Missing TEST DATA event at index ${index}`)
  return event
}
