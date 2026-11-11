import { useCallback, useEffect, useState } from 'react'
import type { Map as MapLibreMap, MapEventType } from 'maplibre-gl'

import type { LiveAisPosition } from '../api/liveAis'

interface LiveAisFollowControlProps {
  map: MapLibreMap
  position: LiveAisPosition
}

// Mount only for a displayable selection; remount on selection or snapshot change.
export function LiveAisFollowControl({ map, position }: LiveAisFollowControlProps) {
  const [following, setFollowing] = useState(false)
  const { longitude, latitude } = position
  const locate = useCallback(() => {
    // No interpolation or camera animation, including for reduced-motion users.
    map.jumpTo({ center: [longitude, latitude], zoom: Math.max(map.getZoom(), 7) })
  }, [map, longitude, latitude])

  useEffect(() => {
    if (following) locate()
  }, [following, locate])

  useEffect(() => {
    const pause = (event: MapEventType['movestart']) => {
      if (event.originalEvent) setFollowing(false)
    }
    map.on('movestart', pause)
    return () => {
      map.off('movestart', pause)
    }
  }, [map])

  return (
    <div className="map-ais-follow" role="group" aria-label="Selected AIS observation map controls">
      <button type="button" onClick={locate}>
        定位船舶
      </button>
      <button type="button" aria-pressed={following} onClick={() => setFollowing(!following)}>
        {following ? '停止跟随' : '跟随船舶'}
      </button>
      <span role="status">{following ? '跟随中 · 手动移动地图可退出' : '2D · 跟随已停止'}</span>
    </div>
  )
}
