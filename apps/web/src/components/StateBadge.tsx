type State = 'LIVE' | 'CACHED' | 'DELAYED' | 'OFFLINE' | 'READY' | 'DEGRADED'

export function StateBadge({ state }: { state: State }) {
  return <span className={`state-badge state-${state.toLowerCase()}`}>{state}</span>
}
