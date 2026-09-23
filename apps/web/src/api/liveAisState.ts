import type {
  LiveAisGapEvent,
  LiveAisPosition,
  LiveAisServerEvent,
  LiveAisStatusEvent,
} from './liveAis'

export type LiveAisContinuityIssue =
  'snapshot_required' | 'stream_epoch_changed' | 'sequence_discontinuity'

export interface LiveAisClientState {
  streamEpoch: string | null
  lastSequence: number | null
  requiresSnapshot: boolean
  positions: Readonly<Record<string, LiveAisPosition>>
  status: LiveAisStatusEvent | null
  gap: LiveAisGapEvent | null
  truncated: boolean
  continuityIssue: LiveAisContinuityIssue | null
}

export function createInitialLiveAisState(): LiveAisClientState {
  return {
    streamEpoch: null,
    lastSequence: null,
    requiresSnapshot: true,
    positions: {},
    status: null,
    gap: null,
    truncated: false,
    continuityIssue: null,
  }
}

export function reduceLiveAisEvent(
  state: LiveAisClientState,
  event: LiveAisServerEvent,
): LiveAisClientState {
  if (event.event === 'vessel.snapshot') {
    return {
      streamEpoch: event.stream_epoch,
      lastSequence: event.sequence,
      requiresSnapshot: false,
      positions: Object.fromEntries(event.positions.map((position) => [position.mmsi, position])),
      status: state.streamEpoch === event.stream_epoch ? state.status : null,
      gap: null,
      truncated: event.truncated,
      continuityIssue: null,
    }
  }

  if (state.streamEpoch === null || state.requiresSnapshot) {
    return rejectUntilSnapshot(state, event, 'snapshot_required')
  }

  if (event.stream_epoch !== state.streamEpoch) {
    return rejectUntilSnapshot(state, event, 'stream_epoch_changed')
  }

  const expectedSequence = (state.lastSequence ?? -1) + 1
  if (event.sequence !== expectedSequence) {
    return rejectUntilSnapshot(state, event, 'sequence_discontinuity')
  }

  if (event.event === 'stream.gap') {
    return {
      ...state,
      lastSequence: event.sequence,
      requiresSnapshot: true,
      positions: {},
      gap: event,
      truncated: false,
      continuityIssue: 'snapshot_required',
    }
  }

  if (event.event === 'stream.status') {
    return {
      ...state,
      lastSequence: event.sequence,
      status: event,
      continuityIssue: null,
    }
  }

  return {
    ...state,
    lastSequence: event.sequence,
    positions: { ...state.positions, [event.position.mmsi]: event.position },
    continuityIssue: null,
  }
}

function rejectUntilSnapshot(
  state: LiveAisClientState,
  event: Exclude<LiveAisServerEvent, { event: 'vessel.snapshot' }>,
  continuityIssue: LiveAisContinuityIssue,
): LiveAisClientState {
  return {
    ...state,
    streamEpoch: event.stream_epoch,
    lastSequence: null,
    requiresSnapshot: true,
    positions: {},
    status: event.event === 'stream.status' ? event : state.status,
    gap: event.event === 'stream.gap' ? event : state.gap,
    truncated: false,
    continuityIssue,
  }
}
