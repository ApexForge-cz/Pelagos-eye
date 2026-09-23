import { CircleAlert, Radio, ShieldCheck } from 'lucide-react'

import type { LiveAisGapEvent, LiveAisStatusEvent } from '../api/liveAis'

interface LiveAisStatusPanelProps {
  status: LiveAisStatusEvent | null
  gap?: LiveAisGapEvent | null
}

export function LiveAisStatusPanel({ status, gap = null }: LiveAisStatusPanelProps) {
  const connection = status?.connection_state ?? 'DISCONNECTED'
  const sourceState = status?.source_state ?? 'OFFLINE'
  const availability = status?.availability ?? 'DATA UNAVAILABLE'
  const coverage = status?.coverage.state ?? 'DATA UNAVAILABLE'
  const detail = status?.detail ?? 'Live AIS worker is not connected. Phase 4 remains planned.'
  const isAvailable = availability === 'AVAILABLE'

  return (
    <section className="live-ais-status" aria-label="Live AIS status">
      <div className="live-ais-status-heading">
        <div>
          <p className="panel-kicker">LIVE AIS / PHASE 4</p>
          <h3>Vessel stream</h3>
        </div>
        <Radio size={17} className={isAvailable ? 'live-ais-icon is-live' : 'live-ais-icon'} />
      </div>

      <div className="live-ais-state" data-state={isAvailable ? 'available' : 'unavailable'}>
        {isAvailable ? <ShieldCheck size={14} /> : <CircleAlert size={14} />}
        <strong>{availability}</strong>
        <span>{connection}</span>
      </div>

      <dl className="live-ais-facts">
        <div>
          <dt>Source freshness</dt>
          <dd>{sourceState}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{coverage}</dd>
        </div>
        <div>
          <dt>Last observation</dt>
          <dd>
            {status?.last_observation_at
              ? formatUtc(status.last_observation_at)
              : 'DATA UNAVAILABLE'}
          </dd>
        </div>
      </dl>

      <p className="live-ais-detail">{detail}</p>

      {gap && (
        <div className="live-ais-gap">
          <strong>STREAM GAP</strong>
          <span>{gap.reason.replaceAll('_', ' ')}</span>
          <small>{gap.replay_available ? 'Replay available' : 'Fresh snapshot required'}</small>
        </div>
      )}
    </section>
  )
}

function formatUtc(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'DATA UNAVAILABLE'
  return `${new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(date)} UTC`
}
