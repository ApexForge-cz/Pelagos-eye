import { CircleAlert, Navigation, Ship, TimerReset } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import type { LiveAisPosition } from '../api/liveAis'
import type { LiveAisClientState } from '../api/liveAisState'
import { LIVE_AIS_MAP_LIMIT, visibleLiveAisPositions } from './liveAisVesselLayer'

export const ACCESSIBLE_AIS_LIST_LIMIT = 100

interface LiveAisVesselInspectorProps {
  state: LiveAisClientState
  transportConnected: boolean
  selectedMmsi: string | null
  onSelect: (position: LiveAisPosition) => void
}

export function LiveAisVesselInspector({
  state,
  transportConnected,
  selectedMmsi,
  onSelect,
}: LiveAisVesselInspectorProps) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15_000)
    return () => window.clearInterval(timer)
  }, [])

  const visiblePositions = useMemo(
    () => visibleLiveAisPositions(state, now, transportConnected),
    [state, now, transportConnected],
  )
  const listedPositions = visiblePositions.slice(0, ACCESSIBLE_AIS_LIST_LIMIT)
  const selected = visiblePositions.find((position) => position.mmsi === selectedMmsi) ?? null
  const unavailable = availabilityMessage(state, transportConnected, now)

  return (
    <section className="live-ais-vessels" aria-label="Live AIS vessel observations">
      <div className="live-ais-vessels-heading">
        <div>
          <p className="panel-kicker">CURRENT OBSERVATIONS</p>
          <h3>Vessel positions</h3>
        </div>
        <span>{visiblePositions.length}</span>
      </div>

      {unavailable ? (
        <div className="live-ais-vessels-empty" data-state={unavailable.label}>
          <CircleAlert size={15} />
          <div>
            <strong>{unavailable.label}</strong>
            <p>{unavailable.detail}</p>
          </div>
        </div>
      ) : visiblePositions.length === 0 ? (
        <div className="live-ais-vessels-empty" data-state="EMPTY">
          <Ship size={15} />
          <div>
            <strong>No current observations</strong>
            <p>
              The covered region returned no usable positions. This does not prove vessel absence.
            </p>
          </div>
        </div>
      ) : (
        <>
          <p className="live-ais-list-note">
            Showing {listedPositions.length} of {visiblePositions.length} current observations.
          </p>
          {(state.truncated || Object.keys(state.positions).length > LIVE_AIS_MAP_LIMIT) && (
            <p className="live-ais-truncated">
              TRUNCATED · The available snapshot or display limit is incomplete.
            </p>
          )}
          <ul className="live-ais-vessel-list" aria-label="Current AIS observation list">
            {listedPositions.map((position) => (
              <li key={position.mmsi}>
                <button
                  type="button"
                  aria-pressed={selected?.mmsi === position.mmsi}
                  onClick={() => onSelect(position)}
                >
                  <span className="live-ais-vessel-symbol" aria-hidden="true">
                    <Navigation size={12} />
                  </span>
                  <span>
                    <strong>MMSI {position.mmsi}</strong>
                    <small>{formatUtc(position.observed_at)}</small>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {selected ? (
        <VesselObservationDetail position={selected} />
      ) : (
        visiblePositions.length > 0 && (
          <p className="live-ais-selection-help">
            Select an observation for its evidence and units.
          </p>
        )
      )}
    </section>
  )
}

function VesselObservationDetail({ position }: { position: LiveAisPosition }) {
  const sourceLink = position.provenance.source_url.startsWith('https://')
  return (
    <section className="live-ais-observation" aria-label="Selected live AIS observation">
      <div className="live-ais-observation-title">
        <Ship size={16} />
        <div>
          <p className="panel-kicker">AIS IDENTITY OBSERVATION</p>
          <h4>MMSI {position.mmsi}</h4>
          <span>{formatUtc(position.observed_at)}</span>
        </div>
      </div>
      <dl className="live-ais-observation-facts">
        <Fact label="Position" value={formatCoordinate(position.latitude, position.longitude)} />
        <Fact
          label="Speed over ground"
          value={formatMeasure(position.speed_over_ground_knots, 'kn')}
        />
        <Fact
          label="Course over ground"
          value={formatMeasure(position.course_over_ground_deg, '°')}
        />
        <Fact label="True heading" value={formatMeasure(position.true_heading_deg, '°')} />
        <Fact
          label="Navigation status code"
          value={position.navigational_status_code?.toString() ?? 'DATA UNAVAILABLE'}
        />
        <Fact label="Source state" value={position.provenance.source_state} />
      </dl>
      <div className="live-ais-observation-source">
        <TimerReset size={13} aria-hidden="true" />
        <span>Ingested {formatUtc(position.provenance.ingested_at)}</span>
        {sourceLink ? (
          <a href={position.provenance.source_url} target="_blank" rel="noreferrer">
            {position.provenance.attribution_text}
          </a>
        ) : (
          <span>{position.provenance.attribution_text}</span>
        )}
      </div>
      {position.quality_flags.length > 0 && (
        <p className="live-ais-quality">Quality flags: {position.quality_flags.join(', ')}</p>
      )}
      <p className="live-ais-caution">
        AIS identity and dynamic fields are fallible observations, not proof of intent, safety, or
        wrongdoing.
      </p>
    </section>
  )
}

function availabilityMessage(state: LiveAisClientState, transportConnected: boolean, now: number) {
  if (!transportConnected) {
    return { label: 'DATA UNAVAILABLE', detail: 'The product WebSocket is disconnected.' }
  }
  if (state.requiresSnapshot) {
    return {
      label: 'FRESH SNAPSHOT REQUIRED',
      detail: 'Positions stay hidden until continuity is restored.',
    }
  }
  if (!state.status || state.status.availability === 'DATA UNAVAILABLE') {
    return {
      label: 'DATA UNAVAILABLE',
      detail: state.status?.detail ?? 'No usable AIS status is available.',
    }
  }
  if (state.status.coverage.state === 'NO COVERAGE') {
    return { label: 'NO COVERAGE', detail: state.status.coverage.description }
  }
  if (
    state.status.connection_state !== 'CONNECTED' ||
    state.status.source_state === 'OFFLINE' ||
    state.status.source_state === 'DELAYED'
  ) {
    return { label: 'DATA UNAVAILABLE', detail: state.status.detail }
  }
  if (state.status.source_state === 'CACHED') {
    const elapsed = (now - Date.parse(state.status.emitted_at)) / 1_000
    const effectiveCacheAge =
      state.status.cache_age_seconds === null || !Number.isFinite(elapsed)
        ? Number.POSITIVE_INFINITY
        : state.status.cache_age_seconds + Math.max(0, elapsed)
    if (effectiveCacheAge > 300) {
      return {
        label: 'DATA UNAVAILABLE',
        detail: 'The last verified AIS cache is older than the five-minute display window.',
      }
    }
  }
  return null
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function formatUtc(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'DATA UNAVAILABLE'
  return `${new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'medium',
    timeZone: 'UTC',
  }).format(date)} UTC`
}

function formatCoordinate(latitude: number, longitude: number) {
  return `${latitude.toFixed(5)}°, ${longitude.toFixed(5)}° · WGS 84`
}

function formatMeasure(value: number | null, unit: string) {
  return value === null ? 'DATA UNAVAILABLE' : `${value.toFixed(1)} ${unit}`
}
