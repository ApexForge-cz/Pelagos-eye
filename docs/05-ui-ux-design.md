# UI/UX Design Direction

## Experience statement

OceanScope should feel like a calm, precise maritime command workspace: dark, spatial, information-dense, and credible. It must not resemble a decorative wallboard. The visual system uses depth and restrained motion to organize real information, while timestamps, coverage, and uncertainty stay visible.

The Phase 3 primary surface is the **Oceanic Spatial Intelligence Command Center**. The
reference video informs only its central 3D Earth, globe-to-region camera movement, spatial
highlighting, route context, HUD layering, side-rail hierarchy, bottom navigation, and
map/data interaction. OceanScope must not copy aviation names, data, icons, assets, or copy.
Impact comes from depth, camera, lighting, motion, and truthful data density rather than
permanent glow, scan lines, flashing, or fabricated telemetry.

Phase 2 has passed its Real Data Foundation gate, but the current frontend remains a minimal
source/status surface. Command Center, map layers, Data Explorer, `NO COVERAGE`, and
`MODEL DATA` presentation are planned follow-up work and must not be described as currently
implemented.

## Design principles

1. **Map first:** the geospatial workspace owns the largest continuous area; panels support a question rather than frame every edge.
2. **Hierarchy before glow:** typography, spacing, grouping, and contrast do the work. Cyan light is an accent, not a border around everything.
3. **Progressive disclosure:** overview first, inspection on demand, deep detail in drawers/routes.
4. **Operational calm:** animation communicates change, selection, or time; nothing pulses merely to look active.
5. **Evidence in context:** source, effective time, freshness, and warnings appear beside the value they qualify.
6. **Dense but legible:** compact controls, aligned numbers, meaningful whitespace, and consistent units.

## Visual language

### Color intent

Initial tokens are planning values and require contrast testing:

| Role | Direction |
| --- | --- |
| Canvas | near-black blue-gray, not pure black |
| Elevated surface | desaturated navy/slate with subtle transparency |
| Primary text | soft cool white |
| Secondary text | blue-gray |
| Action/live accent | controlled cyan |
| Selected route/track | brighter ice blue |
| Warning/delayed | muted amber |
| Critical/offline | coral/red used sparingly |
| Cached | violet or neutral-blue label, always textual |
| Land/water | subdued contrast that keeps data layers dominant |

Never rely on hue alone. Every health state includes a text label and, where useful, an icon or pattern.

### Typography

- Use a modern, readable sans-serif for interface text and a tabular-numeral face/feature for coordinates, time, speed, and counts.
- Limit display typography to page/section moments; dense panels use quiet weights and consistent line heights.
- Avoid all-uppercase paragraphs. Uppercase is reserved for short status labels.
- Chinese and Latin fallbacks must have compatible weight and x-height; verify glyph coverage before release.

### Depth and glass

- Use one or two elevation levels, fine separators, soft shadows, and controlled backdrop blur.
- Glass surfaces must retain legibility over bright map content using an opaque fallback.
- Avoid stacked translucent panels that reduce contrast or GPU performance.

## Layout system

### Desktop

- Top command bar: OceanScope, `GLOBAL`/`REGION`/`PORT`/`VESSEL`/`HISTORY`, UTC,
  data/connection state, performance mode, and command search.
- Left context rail: changes with the active context rather than repeating one dashboard.
- Central spatial workspace: primary interaction surface and roughly 55%-65% of desktop.
- Right intelligence rail: selection-driven evidence, charts, warnings, and provenance.
- Bottom module dock: Overview, Vessels, Ports, Regions, Environment, Traffic, History,
  Risk, and Data; icon + label with a restrained active underline.
- Floating map controls: grouped, keyboard reachable, away from attribution.

Visual layers are L0 space background, L1 Earth/map, L2 spatial data, L3 HUD/information,
and L4 selection/alert. SceneDirector camera presets are configuration, not duplicated hard
code. User map input immediately cancels an automated camera transition.

### Tablet and small screens

- Replace simultaneous side panels with one modal sheet/drawer at a time.
- Prioritize search, selection details, layer toggles, and a simplified time controller.
- Reduce or replace expensive 3D effects when device capability or motion preference indicates.
- Tables become prioritized cards or horizontally scrollable grids with pinned identity columns.

## Planned screen behaviors

| Screen | Primary question | Dominant surface | Key evidence |
| --- | --- | --- | --- |
| Overview | What is available and current? | globe + health summaries | source states and timestamps |
| Live | What is happening in this area now? | map + live inspector | position/source/lag |
| Vessel Explorer | Which vessel am I looking for? | search/results + map | identity observations |
| Vessel Detail | What is known about this vessel and track? | track map + facts | field provenance and recency |
| Ports | Which ports match this need/area? | map + filters | WPI/UNLOCODE version |
| Port Detail | What reference information exists? | port context + attributes | source-specific caveats |
| Ocean | What modeled conditions apply? | raster/vector layer + time | model, valid time, resolution |
| History | What occurred in the selected archive window? | playback map + timeline | coverage and sampling |
| Analytics | How does traffic compare? | coordinated charts/map | denominator and method |
| Risk | Which events/rules need review? | event map + queue | evidence and uncertainty |
| Data | Can I trust and reuse this view? | source catalog | license, coverage, freshness |
| System | Is the platform healthy? | health matrix | last success, lag, errors |

## Geospatial interaction

- A single layer registry defines name, source, legend, visibility, zoom range, freshness, attribution, pick behavior, and renderer.
- Hover is optional enrichment; click/tap and keyboard selection expose essential details.
- Selected objects use both visual emphasis and a stable inspector state.
- Declutter labels by priority, collision handling, and zoom—not by hiding provenance.
- Preserve camera and filters when moving between list/detail routes where practical.
- Provide reset view, locate selected item, scale/context, and coordinate readout where useful.

## Charts and analytics

- Every chart has a question-led title, units, time zone, source/coverage note, and accessible summary.
- Avoid gauge walls and decorative counters. KPIs must have scope, denominator, effective time, and comparison basis.
- Coordinated brushing between chart, timeline, and map must show active filters.
- Use uncertainty bands or quality indicators when the source supports them.
- Tooltips supplement; they do not contain the only available value.

## Motion

- Target short, eased transitions for panel entry, camera focus, selection, and time playback.
- Vessel motion should interpolate only between known observations and must not imply measured intermediate positions; gaps remain visible.
- Respect `prefers-reduced-motion`; provide nonanimated state changes.
- Pause expensive/background animation when the tab is hidden or the layer is not visible.
- No constant blinking, ticker strips, excessive neon, ornamental particles over data, or unbounded globe auto-rotation.

## Data states

Each external-data component supports loading, empty, and error states plus the controlled
source states `LIVE`, `CACHED`, `DELAYED`, and `OFFLINE`. `NO COVERAGE`, `MODEL DATA`,
`DERIVED`, and `TEST DATA` are separate coverage/content labels where applicable; they are
not source states.
Empty means a successful covered query with no matching records; `NO COVERAGE` means the
source does not support the requested space/time; unavailable means no valid answer could be
established. Skeletons must not resemble real values, and color never replaces text.

## Accessibility

- Target WCAG 2.2 AA for UI contrast, focus, labels, error identification, and keyboard operation.
- Offer a logical non-map representation for selected objects and core results.
- Announce live updates selectively; do not flood assistive technology with every AIS message.
- Minimum pointer target and text size are tested at responsive breakpoints.
- Patterns, labels, and shapes supplement color for categorical and risk encodings.

## Performance UX

- Show aggregation/clustering honestly and disclose sampling/downsampling.
- Keep interaction responsive while data loads; cancel obsolete viewport requests.
- Use route/layer lazy loading so 3D and analytical engines are not loaded everywhere.
- Degrade effects before data fidelity: reduce bloom, shadows, terrain detail, animation frequency, then layer density only with a visible notice.

## Design deliverables for implementation phases

- Token sheet and component-state matrix
- Desktop/tablet/mobile wireframes for all planned routes
- Layer registry and map interaction specification
- Motion and reduced-motion specification
- Data status/freshness component contract
- Accessibility checklist and keyboard map
- Reference screenshots at agreed viewports

## UI acceptance criteria

- A user can identify source and freshness for every externally sourced value.
- The map, inspectors, charts, and timeline share filter/time context.
- No screen uses invented KPIs or placeholder numbers in production mode.
- Essential workflows are keyboard reachable outside inherently spatial camera manipulation, with equivalent controls.
- Performance mode and reduced motion preserve meaning.
- Visual review finds no clipped labels, illegible glass, uncontrolled glow, or overlapping attribution.
