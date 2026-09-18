import { lazy, Suspense, useCallback, useEffect, useState, type ReactNode } from 'react'
import {
  Activity,
  Anchor,
  ChevronDown,
  CircleAlert,
  Clock3,
  Database,
  Globe2,
  Layers3,
  LocateFixed,
  MapPinned,
  RefreshCw,
  Search,
  ShipWheel,
  SlidersHorizontal,
  Waves,
} from 'lucide-react'

import { loadPlatformStatus, type PlatformStatus } from './api/status'
import {
  loadMarineForecast,
  loadSpatialSnapshot,
  type EarthquakeRecord,
  type LayerLoadState,
  type MarineForecastRecord,
  type PortRecord,
  type SpatialSnapshot,
  type ViewportBounds,
} from './api/spatial'
import type { MapSelection } from './components/MapWorkspace'

const MapWorkspace = lazy(async () => {
  const module = await import('./components/MapWorkspace')
  return { default: module.MapWorkspace }
})

const GlobeWorkspace = lazy(async () => {
  const module = await import('./components/GlobeWorkspace')
  return { default: module.GlobeWorkspace }
})

type SpatialMode = '3d' | '2d'

type PlatformView =
  | { kind: 'loading' }
  | { kind: 'ready'; status: PlatformStatus }
  | { kind: 'error'; message: string }

export function App() {
  const [platform, setPlatform] = useState<PlatformView>({ kind: 'loading' })
  const [refreshKey, setRefreshKey] = useState(0)
  const [bounds, setBounds] = useState<ViewportBounds | null>(null)
  const [spatial, setSpatial] = useState<SpatialSnapshot | null>(null)
  const [spatialLoading, setSpatialLoading] = useState(false)
  const [selected, setSelected] = useState<MapSelection | null>(null)
  const [marine, setMarine] = useState<LayerLoadState<MarineForecastRecord> | null>(null)
  const [portsVisible, setPortsVisible] = useState(true)
  const [earthquakesVisible, setEarthquakesVisible] = useState(true)
  const [inspectMarine, setInspectMarine] = useState(false)
  const [spatialMode, setSpatialMode] = useState<SpatialMode>(initialSpatialMode)
  const [rendererNotice, setRendererNotice] = useState<string | null>(null)

  const refresh = useCallback(() => {
    setPlatform({ kind: 'loading' })
    setSpatial(null)
    setSelected(null)
    setMarine(null)
    setRefreshKey((value) => value + 1)
  }, [])

  const selectMapItem = useCallback((selection: MapSelection) => {
    setMarine(null)
    setSelected(selection)
  }, [])

  const selectSpatialMode = useCallback((mode: SpatialMode) => {
    setRendererNotice(null)
    setSpatialMode(mode)
  }, [])

  const fallBackTo2d = useCallback(() => {
    setRendererNotice('3D WEBGL 不可用，已切换到 2D 地图')
    setSpatialMode('2d')
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void loadPlatformStatus(controller.signal)
      .then((status) => setPlatform({ kind: 'ready', status }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setPlatform({
            kind: 'error',
            message: error instanceof Error ? error.message : '平台状态请求失败',
          })
        }
      })
    return () => controller.abort()
  }, [refreshKey])

  useEffect(() => {
    if (!bounds) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setSpatialLoading(true)
      void loadSpatialSnapshot(bounds, controller.signal)
        .then(setSpatial)
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          setSpatial({
            requestedAt: new Date().toISOString(),
            ports: { kind: 'unavailable', message: '空间数据请求失败' },
            earthquakes: { kind: 'unavailable', message: '空间数据请求失败' },
          })
        })
        .finally(() => setSpatialLoading(false))
    }, 300)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [bounds, refreshKey])

  useEffect(() => {
    if (selected?.kind !== 'coordinate') {
      return
    }
    const controller = new AbortController()
    void loadMarineForecast(selected.latitude, selected.longitude, controller.signal)
      .then(setMarine)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setMarine({ kind: 'unavailable', message: '海洋预报请求失败' })
      })
    return () => controller.abort()
  }, [selected])

  const ports = spatial?.ports.kind === 'ready' ? spatial.ports.records : []
  const earthquakes = spatial?.earthquakes.kind === 'ready' ? spatial.earthquakes.records : []
  const spatialTotal =
    (spatial?.ports.kind === 'ready' ? spatial.ports.total : 0) +
    (spatial?.earthquakes.kind === 'ready' ? spatial.earthquakes.total : 0)
  const spatialLoaded = ports.length + earthquakes.length
  const sourceState = platform.kind === 'ready' ? platform.status.system.overall_state : 'DEGRADED'

  return (
    <main className="command-center">
      <header className="command-bar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <ShipWheel size={19} />
          </div>
          <div>
            <p className="brand-name">OceanScope</p>
            <p className="brand-subtitle">SPATIAL INTELLIGENCE / PHASE 3</p>
          </div>
        </div>
        <nav className="mode-nav" aria-label="工作模式">
          <button className="mode-button active" type="button">
            <MapPinned size={14} /> GLOBAL
          </button>
          <button className="mode-button" type="button">
            <Anchor size={14} /> PORTS
          </button>
          <button className="mode-button" type="button">
            <Waves size={14} /> OCEAN
          </button>
          <button className="mode-button" type="button">
            <Activity size={14} /> EVENTS
          </button>
        </nav>
        <div className="command-actions">
          <span className="utc-clock">
            <Clock3 size={14} /> {formatClock(new Date())} UTC
          </span>
          <span className="status-inline">
            <span className="status-dot" /> {sourceState}
          </span>
          <button
            className="icon-button"
            type="button"
            title="刷新数据"
            aria-label="刷新数据"
            onClick={refresh}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className="left-rail">
          <div className="rail-heading">
            <div>
              <p className="panel-kicker">CONTEXT / 01</p>
              <h1>全球态势</h1>
            </div>
            <button className="icon-button quiet" type="button" title="搜索" aria-label="搜索">
              <Search size={16} />
            </button>
          </div>
          <div className="search-field">
            <Search size={15} />
            <span>搜索港口、事件或坐标</span>
            <kbd>/</kbd>
          </div>
          <PanelSection title="空间图层" icon={<Layers3 size={15} />}>
            <LayerToggle
              label="公开港口参考"
              detail={layerDetail(spatial?.ports, 'UN/LOCODE')}
              checked={portsVisible}
              onChange={setPortsVisible}
              color="cyan"
            />
            <LayerToggle
              label="地震事件"
              detail={layerDetail(spatial?.earthquakes, 'USGS past-hour')}
              checked={earthquakesVisible}
              onChange={setEarthquakesVisible}
              color="coral"
            />
            <LayerToggle
              label="海洋预报点"
              detail="点击地图查询"
              checked={inspectMarine}
              onChange={setInspectMarine}
              color="violet"
            />
          </PanelSection>
          <PanelSection title="视口查询" icon={<SlidersHorizontal size={15} />}>
            <dl className="viewport-facts">
              <Fact label="覆盖范围" value={bounds ? formatBounds(bounds) : '等待地图视口'} />
              <Fact
                label="已载入 / 匹配"
                value={
                  spatialLoading
                    ? '查询中…'
                    : spatialLoaded === spatialTotal
                      ? `${spatialLoaded} 条`
                      : `${spatialLoaded} / ${spatialTotal} 条`
                }
              />
              <Fact
                label="请求时间"
                value={spatial ? formatUtc(spatial.requestedAt) : '尚未请求'}
              />
            </dl>
          </PanelSection>
          <PanelSection title="视口记录" icon={<Database size={15} />}>
            <ViewportRecords
              ports={ports}
              earthquakes={earthquakes}
              portsState={spatial?.ports}
              earthquakesState={spatial?.earthquakes}
              selected={selected}
              onSelect={selectMapItem}
            />
          </PanelSection>
          <div className="coverage-note">
            <CircleAlert size={15} />
            <span>地图只显示当前视口内可公开记录；缺少覆盖不代表没有活动。</span>
          </div>
        </aside>

        <section className="map-column" aria-label="空间工作区">
          <div className="map-topline">
            <div>
              <p className="panel-kicker">LIVE VIEWPORT / WGS 84</p>
              <h2>海事空间态势</h2>
            </div>
            <div className="map-topline-actions">
              <div className="spatial-mode-control" aria-label="空间视图模式">
                <button
                  type="button"
                  className={spatialMode === '3d' ? 'active' : ''}
                  aria-pressed={spatialMode === '3d'}
                  onClick={() => selectSpatialMode('3d')}
                >
                  <Globe2 size={13} /> 3D
                </button>
                <button
                  type="button"
                  className={spatialMode === '2d' ? 'active' : ''}
                  aria-pressed={spatialMode === '2d'}
                  onClick={() => selectSpatialMode('2d')}
                >
                  <MapPinned size={13} /> 2D
                </button>
              </div>
              <span className="data-label">REAL DATA</span>
            </div>
          </div>
          <div className="map-frame">
            <Suspense
              fallback={
                <div className="map-engine-loading">
                  <span className="loading-mark" /> 初始化地图引擎
                </div>
              }
            >
              {spatialMode === '3d' ? (
                <GlobeWorkspace
                  ports={ports}
                  earthquakes={earthquakes}
                  portsVisible={portsVisible}
                  earthquakesVisible={earthquakesVisible}
                  inspectMarine={inspectMarine}
                  onBoundsChange={setBounds}
                  onSelection={selectMapItem}
                  onUnavailable={fallBackTo2d}
                />
              ) : (
                <MapWorkspace
                  ports={ports}
                  earthquakes={earthquakes}
                  portsVisible={portsVisible}
                  earthquakesVisible={earthquakesVisible}
                  inspectMarine={inspectMarine}
                  onBoundsChange={setBounds}
                  onSelection={selectMapItem}
                />
              )}
            </Suspense>
            {rendererNotice && <div className="renderer-notice">{rendererNotice}</div>}
            {spatialLoading && (
              <div className="map-loading">
                <span className="loading-mark" /> 更新视口数据
              </div>
            )}
            <div className="map-legend">
              <span>
                <i className="legend-dot cyan" />
                港口
              </span>
              <span>
                <i className="legend-dot coral" />
                地震
              </span>
              <span>
                <i className="legend-dot violet" />
                预报查询
              </span>
            </div>
          </div>
        </section>

        <aside className="right-rail">
          <div className="rail-heading">
            <div>
              <p className="panel-kicker">INTELLIGENCE / 02</p>
              <h2>选择情报</h2>
            </div>
            <Database size={17} className="muted-icon" />
          </div>
          {selected ? <SelectionPanel selection={selected} marine={marine} /> : <EmptySelection />}
          <div className="right-divider" />
          <SourceHealth platform={platform} />
        </aside>
      </div>

      <nav className="module-dock" aria-label="模块导航">
        <DockItem icon={<MapPinned size={16} />} label="总览" active />
        <DockItem icon={<ShipWheel size={16} />} label="船舶" disabled />
        <DockItem icon={<Anchor size={16} />} label="港口" />
        <DockItem icon={<Waves size={16} />} label="环境" />
        <DockItem icon={<Activity size={16} />} label="事件" />
        <DockItem icon={<Clock3 size={16} />} label="历史" disabled />
        <DockItem icon={<Database size={16} />} label="数据" />
      </nav>
    </main>
  )
}

function SelectionPanel({
  selection,
  marine,
}: {
  selection: MapSelection
  marine: LayerLoadState<MarineForecastRecord> | null
}) {
  if (selection.kind === 'port') return <PortInspector record={selection.record} />
  if (selection.kind === 'earthquake') return <EarthquakeInspector record={selection.record} />
  return (
    <MarineInspector
      latitude={selection.latitude}
      longitude={selection.longitude}
      marine={marine}
    />
  )
}

function PortInspector({ record }: { record: PortRecord }) {
  return (
    <div className="inspector">
      <div className="selection-title">
        <span className="selection-icon cyan-bg">
          <Anchor size={16} />
        </span>
        <div>
          <p className="panel-kicker">PORT REFERENCE</p>
          <h3>{record.name || '未命名位置'}</h3>
          <p>
            {record.un_locode ?? record.source_record_id} · {record.country_code}
          </p>
        </div>
      </div>
      <InfoGrid
        items={[
          ['坐标', formatCoordinate(record.latitude, record.longitude)],
          ['记录类型', record.record_type.toUpperCase()],
          ['来源状态', record.provenance.source_state],
          ['数据版本', record.provenance.data_version],
        ]}
      />
      <ProvenanceNote record={record.provenance} flags={record.quality_flags} />
    </div>
  )
}

function EarthquakeInspector({ record }: { record: EarthquakeRecord }) {
  return (
    <div className="inspector">
      <div className="selection-title">
        <span className="selection-icon coral-bg">
          <CircleAlert size={16} />
        </span>
        <div>
          <p className="panel-kicker">USGS EVENT</p>
          <h3>{record.place ?? '地震事件'}</h3>
          <p>{formatUtc(record.event_time)}</p>
        </div>
      </div>
      <div className="magnitude-readout">
        <strong>{record.magnitude?.toFixed(1) ?? '—'}</strong>
        <span>MAGNITUDE</span>
      </div>
      <InfoGrid
        items={[
          ['深度', `${record.depth_km.toFixed(1)} km`],
          ['审核状态', record.provider_status ?? '未知'],
          ['海啸字段', record.tsunami ? '是' : '否'],
          ['来源状态', record.provenance.source_state],
        ]}
      />
      <ProvenanceNote record={record.provenance} flags={record.quality_flags} />
      <p className="warning-copy">
        USGS 海啸字段是提供方元数据，不是 OceanScope 的影响预测或警报。
      </p>
    </div>
  )
}

function MarineInspector({
  latitude,
  longitude,
  marine,
}: {
  latitude: number
  longitude: number
  marine: LayerLoadState<MarineForecastRecord> | null
}) {
  const point = marine?.kind === 'ready' ? marine.records[0] : null
  return (
    <div className="inspector">
      <div className="selection-title">
        <span className="selection-icon violet-bg">
          <Waves size={16} />
        </span>
        <div>
          <p className="panel-kicker">MODEL DATA / OPEN-METEO</p>
          <h3>海洋预报查询</h3>
          <p>{formatCoordinate(latitude, longitude)}</p>
        </div>
      </div>
      {!marine ? (
        <div className="inspector-loading">
          <span className="loading-mark" /> 请求精确坐标预报…
        </div>
      ) : marine.kind === 'unavailable' ? (
        <Unavailable message="此坐标没有可用的已存储预报，或来源已不可用。" />
      ) : !point ? (
        <Unavailable message="NO COVERAGE · 当前时间窗没有预报点。" />
      ) : (
        <>
          <div className="forecast-primary">
            <strong>
              {point.wave_height_m?.toFixed(1) ?? '—'} <small>m</small>
            </strong>
            <span>有效于 {formatUtc(point.valid_at)}</span>
          </div>
          <InfoGrid
            items={[
              ['海温', formatMeasure(point.sea_surface_temperature_c, '°C')],
              ['浪周期', formatMeasure(point.wave_period_s, 's')],
              ['海流速度', formatMeasure(point.ocean_current_velocity_kmh, 'km/h')],
              ['模型', point.model],
            ]}
          />
          <ProvenanceNote record={point.provenance} flags={point.quality_flags} />
        </>
      )}
    </div>
  )
}

function EmptySelection() {
  return (
    <div className="empty-selection">
      <div className="empty-crosshair">
        <LocateFixed size={22} />
      </div>
      <strong>未选择空间对象</strong>
      <p>选择港口或地震事件查看证据；开启“海洋预报点”后，点击海面查询精确坐标。</p>
    </div>
  )
}
function Unavailable({ message }: { message: string }) {
  return (
    <div className="unavailable-block">
      <strong>DATA UNAVAILABLE</strong>
      <p>{message}</p>
    </div>
  )
}
function InfoGrid({ items }: { items: [string, string][] }) {
  return (
    <dl className="info-grid">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
function ProvenanceNote({ record, flags }: { record: PortRecord['provenance']; flags: string[] }) {
  const effectiveTime = record.published_at ?? record.retrieved_at
  return (
    <div className="provenance-note">
      <span>
        {record.source_display_name} · {record.source_state}
        {record.cache_age_seconds !== null
          ? ` · 缓存 ${formatDuration(record.cache_age_seconds)}`
          : ''}
      </span>
      <span>来源时间：{formatUtc(effectiveTime)}</span>
      <a href={record.source_url} target="_blank" rel="noreferrer">
        {record.attribution_text}
      </a>
      {flags.length > 0 && <span className="quality-flag">质量提示：{flags.join(', ')}</span>}
    </div>
  )
}
function SourceHealth({ platform }: { platform: PlatformView }) {
  if (platform.kind === 'loading')
    return (
      <div className="source-health">
        <p className="panel-kicker">SOURCE LENS</p>
        <div className="health-line">
          <span className="loading-mark" />
          读取来源状态
        </div>
      </div>
    )
  if (platform.kind === 'error')
    return (
      <div className="source-health">
        <p className="panel-kicker">SOURCE LENS</p>
        <Unavailable message={platform.message} />
      </div>
    )
  const usable = platform.status.catalog.sources.filter((source) => source.has_usable_data).length
  return (
    <div className="source-health">
      <p className="panel-kicker">SOURCE LENS / PHASE 2</p>
      <div className="health-score">
        <strong>
          {usable}/{platform.status.catalog.sources.length}
        </strong>
        <span>来源可用</span>
      </div>
      <div className="health-line">
        <span className="status-dot" /> API {platform.status.system.overall_state}
      </div>
      <p className="health-time">检查于 {formatUtc(platform.status.system.checked_at)}</p>
    </div>
  )
}
function PanelSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: ReactNode
  children: ReactNode
}) {
  return (
    <section className="panel-section">
      <div className="panel-section-heading">
        <span>{icon}</span>
        <h2>{title}</h2>
        <ChevronDown size={14} />
      </div>
      {children}
    </section>
  )
}
function ViewportRecords({
  ports,
  earthquakes,
  portsState,
  earthquakesState,
  selected,
  onSelect,
}: {
  ports: PortRecord[]
  earthquakes: EarthquakeRecord[]
  portsState: LayerLoadState<PortRecord> | undefined
  earthquakesState: LayerLoadState<EarthquakeRecord> | undefined
  selected: MapSelection | null
  onSelect: (selection: MapSelection) => void
}) {
  const records = [
    ...ports.slice(0, 6).map((record) => ({
      key: `port-${record.id}`,
      kind: '港口',
      title: record.name || record.un_locode || record.source_record_id,
      detail: `${record.country_code} · ${record.provenance.source_state}`,
      active: selected?.kind === 'port' && selected.record.id === record.id,
      select: () => onSelect({ kind: 'port', record }),
    })),
    ...earthquakes.slice(0, 6).map((record) => ({
      key: `earthquake-${record.id}`,
      kind: '地震',
      title: record.place ?? record.event_id,
      detail: `M ${record.magnitude?.toFixed(1) ?? '—'} · ${formatUtc(record.event_time)}`,
      active: selected?.kind === 'earthquake' && selected.record.id === record.id,
      select: () => onSelect({ kind: 'earthquake', record }),
    })),
  ]

  if (!portsState && !earthquakesState) {
    return <p className="record-state">等待视口数据</p>
  }
  if (records.length === 0) {
    const unavailable =
      portsState?.kind === 'unavailable' && earthquakesState?.kind === 'unavailable'
    return (
      <p className={`record-state ${unavailable ? 'is-unavailable' : ''}`}>
        {unavailable ? 'DATA UNAVAILABLE' : '当前视口内没有公开记录'}
      </p>
    )
  }
  return (
    <div className="viewport-records" aria-label="当前视口记录">
      {records.map((record) => (
        <button
          key={record.key}
          className="record-row"
          type="button"
          aria-pressed={record.active}
          onClick={record.select}
        >
          <span className="record-kind">{record.kind}</span>
          <span className="record-copy">
            <strong>{record.title}</strong>
            <small>{record.detail}</small>
          </span>
        </button>
      ))}
      {ports.length + earthquakes.length > records.length && (
        <p className="record-overflow">
          另有 {ports.length + earthquakes.length - records.length} 条
        </p>
      )}
    </div>
  )
}
function LayerToggle({
  label,
  detail,
  checked,
  onChange,
  color,
}: {
  label: string
  detail: string
  checked: boolean
  onChange: (value: boolean) => void
  color: string
}) {
  return (
    <label className="layer-toggle">
      <span className={`layer-swatch ${color}`} />
      <span className="layer-copy">
        <strong>{label}</strong>
        <small>{detail}</small>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="toggle-track" aria-hidden="true">
        <span />
      </span>
    </label>
  )
}
function DockItem({
  icon,
  label,
  active = false,
  disabled = false,
}: {
  icon: ReactNode
  label: string
  active?: boolean
  disabled?: boolean
}) {
  return (
    <button className={`dock-item ${active ? 'active' : ''}`} type="button" disabled={disabled}>
      {icon}
      <span>{label}</span>
      {disabled && <small>计划</small>}
    </button>
  )
}
function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}
function layerDetail(layer: LayerLoadState<unknown> | undefined, fallback: string) {
  if (!layer) return fallback
  return layer.kind === 'ready'
    ? `${layer.total} 条${layer.truncated ? ' · 已截断' : ''}`
    : 'DATA UNAVAILABLE'
}
function formatBounds(bounds: ViewportBounds) {
  return `${bounds.west.toFixed(0)}°…${bounds.east.toFixed(0)}° / ${bounds.south.toFixed(0)}°…${bounds.north.toFixed(0)}°`
}
function formatCoordinate(latitude: number | null, longitude: number | null) {
  return latitude === null || longitude === null
    ? 'DATA UNAVAILABLE'
    : `${latitude.toFixed(4)}°, ${longitude.toFixed(4)}° WGS 84`
}
function formatMeasure(value: number | null, unit: string) {
  return value === null ? '—' : `${value.toFixed(1)} ${unit}`
}
function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds} 秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟`
  return `${Math.floor(seconds / 3600)} 小时`
}
function formatClock(date: Date) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  }).format(date)
}
function formatUtc(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? '时间不可用'
    : `${new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short', timeZone: 'UTC' }).format(date)} UTC`
}

function initialSpatialMode(): SpatialMode {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return '2d'
  return window.matchMedia('(min-width: 769px)').matches ? '3d' : '2d'
}
