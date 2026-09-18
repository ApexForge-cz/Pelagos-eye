# OceanScope

## 全球港航态势感知与智能分析平台

### 项目规划、双人协作与开发路线图

**Version 2.1**<br>
**审计基线：2026-09-18**<br>
**状态：Phase 0-2 Complete；Phase 3 Next Major Development Stage**<br>
**开发方式：Dual-Developer / Codex-Assisted Software Engineering**<br>
**项目性质：Non-commercial / Learning & Research / GitHub Portfolio / Software Engineering Project**

> OceanScope 是研究、学习与工程作品集项目，不是导航、碰撞规避、应急调度、政府监管或执法系统。任何界面、指标与说明均不得暗示可以替代海图、航行通告、船舶设备、主管机关或专业判断。

本文档以当前仓库代码、迁移、测试、验证记录和工作区状态为依据。旧版规划书只作为历史输入，不能覆盖真实实现。项目最初由 Developer A 单人启动并完成 Phase 0、Phase 1 及 Phase 2 的主要工作；Developer B 自当前阶段加入，后续采用有明确所有权的双人并行开发。

---

# 目录

1. Executive Summary
2. Project Background
3. Positioning / Scope / Boundaries
4. Product & Feature Architecture
5. System Architecture
6. Data Architecture
7. Real Data Sources
8. UI / UX & 3D Spatial Design
9. Two-Developer Collaboration
10. Current Repository & Development State
11. Phase 0 Retrospective
12. Phase 1 Hardening
13. Phase 2 Complete & Follow-up
14. Phase 3 Digital Earth
15. Phase 4 Live AIS
16. Phase 5 Historical Intelligence
17. Phase 6 Risk & Anomaly
18. Phase 7 Advanced Visualization
19. Phase 8 Intelligence
20. Phase 9 Quality & Security
21. Phase 10 Release
22. Feature Coverage Matrix
23. Data Coverage Matrix
24. Innovation Roadmap
25. Testing Strategy
26. Security
27. GitHub / Codex Workflow
28. Risk Register
29. Decision Log
Appendix A. Design Tokens
Appendix B. Status Vocabulary
Appendix C. Audit Evidence and Open Confirmations
Appendix D. Official Source References

---

# 1. Executive Summary

OceanScope 的目标是构建一个以地图为主要交互界面的港航态势探索与分析平台，将真实来源、空间范围、时间窗口、数据质量和可追溯性放在视觉表达之前。当前仓库已经完成研究规划、工程基础与 Phase 2 Real Data Foundation，并实现五类官方数据源的受限采集、验证、标准化、PostGIS 持久化和来源状态能力；三个公开只读数据查询也已经存在。Phase 2 不是“只下载了数据文件”，而是已经形成经过门禁验证的可运行数据链路；完整地图用户体验属于后续阶段。

当前状态必须区分为：

| Phase | 真实状态 | 结论 |
| --- | --- | --- |
| Phase 0 | COMPLETED；V2.1 已执行 retrospective review | 不重做；只修正文档、覆盖矩阵、创新路线和双人基线 |
| Phase 1 | COMPLETED；Engineering Hardening 持续 | 不重新初始化；保留现有 React、FastAPI、PostGIS、Redis、Docker 与 CI |
| Phase 2 | COMPLETED | Real Data Foundation 门禁已通过；人工响应式视觉检查作为非阻塞后续项记录 |
| Phase 3 | NEXT MAJOR DEVELOPMENT STAGE | 仅允许准备 UI shell、设计系统、Cesium POC 与地图架构；不得宣称已进入正式实现 |

仓库审计显示：UN/LOCODE、WPI、USGS、Open-Meteo Marine、MarineCadastre 都有真实实现证据，但能力边界不同。UN/LOCODE 可通过 `/ports` 公开查询；WPI 只允许内部导入和状态展示，公开记录受再分发状态阻断；USGS 可通过带时间和空间边界的 `/earthquakes` 查询；Open-Meteo 可通过精确坐标和时间窗口的 `/ocean/forecast` 查询，但当前尚未覆盖 swell 字段；MarineCadastre 只支持受限的美国水域历史 AIS 导入，没有公开记录 API、轨迹、回放或全球覆盖声明。

双人路线不是平均分工。Developer A 继续作为 Project Lead + Full-Stack GIS Engineer，承担约 65%-70% 总体工作量并掌握产品、架构、核心前端、GIS、3D、核心 API contract、分析、集成和发布。Developer B 作为 Data & Platform Engineer，承担约 30%-35%，拥有数据源、采集、验证、规范化、后端数据服务、基础设施、测试和性能流水线等完整独立模块。`Existing Ownership Wins`：已有稳定模块不因新职责表而迁移，新增功能才按新所有权落位。

核心原则：

- Real data before impressive numbers.
- Correctness before visual decoration.
- Map interaction should drive analysis.
- Every important number must be traceable.
- No data is not zero; no coverage is not no vessel.
- Model data is not observation; derived metrics are not official facts.
- AI explains evidence; AI does not invent evidence.

---

# 2. Project Background

港航信息分散在实时 AIS、历史 AIS 归档、港口参考数据、海洋数值模型、地震事件和系统运行状态中。这些来源的协议、时效、空间覆盖、字段语义、质量和授权不同。如果只追求“视觉大屏”，很容易把缓存当实时、把无覆盖当零、把模型结果当现场观测、把异常指标当事实结论。

OceanScope 的工程价值来自四个闭环：

1. **Source to Screen**：官方来源经过适配、验证、标准化、持久化、API 和前端呈现。
2. **Evidence to Claim**：每个重要值能追溯到来源、版本、时间、覆盖和质量。
3. **Map to Analysis**：区域、时间和选择状态贯通地图、图表、事件和详情。
4. **Code to Portfolio**：架构、测试、风险、决策、限制和演示都与真实实现同步。

项目历史必须准确表达：OceanScope 最初由 Developer A 单人启动。Phase 0 建立范围与规划，Phase 1 建立工程基础，Phase 2 的主要实现也由 Developer A 完成。Developer B 在当前阶段加入，不改写项目历史，而是从 Phase 2 hardening 与 Phase 3 preparation 开始拥有独立模块。

---

# 3. Positioning / Scope / Boundaries

## 3.1 产品定位

正式名称：**OceanScope - 全球港航态势感知与智能分析平台**。英文：**Global Maritime Situational Awareness & Analytics Platform**。

OceanScope 面向学习研究、技术展示和可复现的空间数据探索，不提供海上安全保证。首要用户包括：希望检查港口、海洋环境、事件和船舶上下文的探索者；验证数据质量与来源的研究者；诊断采集和缓存状态的维护者；审查架构、测试和工程取舍的教师或招聘评审者。

## 3.2 明确边界

OceanScope 不是：

- 真实导航系统、电子海图系统或驾驶台设备；
- 碰撞规避、航行决策或应急指挥系统；
- 政府监管、执法、调查或定罪系统；
- 对船舶意图、违法行为、危险程度的权威判定系统；
- 全球历史 AIS 数据库；
- “实时全球 AIS”产品，直到 Phase 4 完成真实接入、条款复核和端到端验收。

## 3.3 功能层级

| 层级 | 功能 |
| --- | --- |
| CORE | Real Data、Data Provenance、System Health、Data Explorer、3D Earth、Port、Region、Environment、Live Vessel、Vessel Search、History、Traffic Analytics |
| ADVANCED | Corridor Intelligence、Compare Mode、Risk、Data Confidence、Source Lens、Particles、3D Analysis、Spatiotemporal Lens |
| RESEARCH | ML Anomaly、Traffic Forecast Experiment、Natural Language Spatial Query、Evidence AI、Situation Report |

每个 Phase 使用 `Must / Should / Future / Research` 约束范围。高级能力不得早于数据可靠性、可追溯性和覆盖语义。

## 3.4 Definition of Real Feature

| 状态 | 判定合同 |
| --- | --- |
| Implemented | 同时具备真实数据、backend、frontend、error state、source display、test、documentation |
| Backend Ready | 后端、真实数据和测试可用，但没有完成用户前端闭环 |
| Prototype | 只有 UI 或 proof-of-concept，不能写成已实现业务功能 |
| Development Only | 使用明确隔离的 DEV / TEST DATA，仅用于开发或测试 |
| Planned | 已进入路线图但没有实现证据 |
| Research | 仍需验证数据、方法、条款或产品价值 |

---

# 4. Product & Feature Architecture

OceanScope 的产品主轴不是页面数量，而是共享空间上下文。`Current Region Context` 与 `Time Window` 形成 Spatiotemporal Lens，驱动 Port、Vessel、Environment、History、Traffic、Risk、Coverage 和 Event Timeline。地图选择更新图表，图表筛选反向更新地图；URL 保存相同上下文以支持可复现分享。

```diagram
PRODUCT CONTEXT FLOW

User intent
   |
   v
Command Palette / Search / Map / URL Workspace
   |
   v
Current Context: GLOBAL | REGION | PORT | VESSEL | HISTORY
   |
   +--------------------+--------------------+
   |                    |                    |
   v                    v                    v
Region Geometry     Time Window          Selected Entity
   |                    |                    |
   +---------- Spatiotemporal Lens ----------+
                         |
         +---------------+---------------+
         v               v               v
       Map Layers      Charts          Event Timeline
         |               |               |
         +------ Source + Coverage + Quality ------+
```

## 4.1 Primary workspaces

- `/`：OceanScope Command Center，地图占主要视觉区域，显示当前上下文、来源、覆盖和选择。
- `/data`：Data Sources，展示来源、版本、条款、归属、质量、时效、缓存和运行记录。
- `/system`：System Health，展示 API、数据库、Redis、provider、ingestion 和前端连接状态。
- `/data/explorer`：真实数据探索，支持 Port、Location、Earthquake、Marine、Coordinate、Region 和 Source Metadata 查询。
- `/ports`、`/ports/:id`：港口搜索、详情、环境、附近活动、历史和来源。
- `/regions`：自定义或预设区域的交通、港口、环境、历史、事件、覆盖和风险上下文。
- `/ocean`：模型海洋环境图层、时间轴、Location Inspector 和 Region Environmental Profile。
- `/vessels`、`/vessels/:id`：Phase 4 的真实船舶搜索、详情、轨迹、时间与来源。
- `/history`、`/analytics`、`/risk`：后续的历史回放、交通分析和可解释指标。

## 4.2 实用功能优先

Phase 2-3 的实用价值优先来自：坐标查询、区域查询、无覆盖说明、来源抽屉、Freshness、共享 Region Context、可复制 URL、Command Palette 和性能模式。它们让用户能回答“这里有哪些真实可用数据、何时有效、来自哪里、为什么没有结果”，而不是只看到装饰性地球。

---

# 5. System Architecture

## 5.1 Architecture V2

继续采用 clean-ish modular monolith。除非存在量化的扩展、隔离或团队所有权证据，否则不拆微服务。API/handler 保持薄，服务层承载业务编排与状态策略，repository/data layer 承载数据库访问，provider adapter 隔离外部协议与原始字典。

```diagram
SYSTEM ARCHITECTURE V2

Browser
  React + TypeScript
  Command Center / Data / System / Explorer / Domain Features
  CesiumJS | MapLibre | deck.gl | ECharts  [planned by phase]
        |
        | HTTPS / WebSocket
        v
FastAPI Modular Monolith
  Routes -> Typed Contracts -> Services -> Repositories
                         |          |
                         |          +--> PostgreSQL 17 + PostGIS
                         |          +--> Redis cache / stream coordination
                         |
                         +--> Provider Adapters
                               UN/LOCODE | WPI | USGS | Open-Meteo
                               MarineCadastre | AISStream [Phase 4]
        |
        +--> Import / Analytics Workers [independently runnable when justified]

Cross-cutting: UTC | WGS 84 | provenance | freshness | quality | limits | logs
```

## 5.2 当前实现与后续边界

当前仓库真实结构是 `apps/api`、`apps/web`、`infra`、`scripts`、`docs` 和 `.github`。不存在必须补齐的平行 `backend/`、`frontend/`、`packages/` 或 `workers/` 目录；新增 worker 只有在 Phase 4-5 出现真实异步负载时才创建。PostGIS 用于空间持久化和查询；Redis 已在 Compose 中存在，但当前业务使用仍需要 hardening evidence。

## 5.3 Spatial and temporal rules

- 内部统一 UTC；展示层明确 UTC 或用户时区。
- 来源边界使用 WGS 84；米制计算使用 PostGIS geography 或合适投影，禁止把角度当米。
- 昂贵查询必须有空间、时间、分页或记录数边界。
- 跨反经线、极区、空几何、无效坐标和边界相交必须显式测试。
- 任何聚合、抽样、插值、分段或下采样都必须可见并记录方法。

---

# 6. Data Architecture

## 6.1 Real Data Pipeline

```diagram
REAL DATA PIPELINE

Official Source
   |
   v
Typed Provider Adapter -- terms / attribution / limits / coverage
   |
   v
Checksummed Raw Artifact or Response Reference
   |
   v
Transport + Schema + Semantic Validation
   |                 \
   |                  -> rejected counts / quality issues / failed run
   v
Canonical Normalization -- UTC / WGS 84 / units / identifiers
   |
   v
PostGIS / Redis -- versioned writes / idempotency / bounded cache
   |
   v
Thin API -> Service policy -> Public redistribution gate
   |
   v
UI -- value + unit + effective time + source + state + coverage + warning
```

## 6.2 Provenance contract

每条外部数据至少保留：source slug/display name、official/terms URL、attribution、license/redistribution status、source record ID、source/event/update/valid time、retrieved/ingested/normalized time、data/schema/normalization version、checksum/raw artifact reference、source state、cache age、quality flags 和 ingestion run。派生结果还必须保存算法和规则版本、参数、输入版本、代码 revision、空间时间范围、单位、分母和完成状态。

## 6.3 Status and failure semantics

统一状态是 `LIVE`、`CACHED`、`DELAYED`、`OFFLINE`、`NO COVERAGE`、`MODEL DATA`、`DERIVED`、`TEST DATA`。颜色只作为辅助，文本标签不可省略。

- `LIVE`：在来源特定 freshness window 内有可用数据。
- `DELAYED`：仍可使用但已超过正常更新窗口。
- `CACHED`：刷新失败或使用已验证本地副本，必须显示 age。
- `OFFLINE`：没有在政策内可接受的数据，显示 `DATA UNAVAILABLE`。
- `NO COVERAGE`：查询成功，但该来源不覆盖请求区域/时间；不能返回 0 代替。
- `MODEL DATA`：数值模型，不是现场传感器观测。
- `DERIVED`：透明公式或算法生成，不能写成官方事实。
- `TEST DATA`：只能出现在测试路径，生产构建不得作为 fallback。

```diagram
FALLBACK DECISION

Provider response valid?
   | yes -> validate -> persist -> LIVE / DELAYED
   |
   no
   v
Verified cache exists and is inside policy?
   | yes -> CACHED + age + source/version
   |
   no
   v
Spatial/temporal request outside known coverage?
   | yes -> NO COVERAGE
   |
   no -> OFFLINE + DATA UNAVAILABLE

Never: random value | zero fill | unrelated value | silent stale fallback
```

---

# 7. Real Data Sources

## 7.1 Current source assessment

| Dataset | Current status | Implemented evidence | Remaining boundary |
| --- | --- | --- | --- |
| UNECE UN/LOCODE | Implemented / public bounded query | release download, function-code port filtering, validation, versioned PostGIS rows, `/ports` | port entity resolution、radius/BBOX query、detail UI |
| NGA WPI | Implemented internally / Needs Hardening | official CSV import, validation, version/checksum/provenance, WPI rows in PostGIS | redistribution `unreviewed`; public records blocked; facilities/services need typed public contract |
| USGS Earthquake | Implemented / public bounded query | event ID uniqueness, provider revision update, PostGIS geography, `/earthquakes` | scheduler, retraction/deletion policy, map/proximity UI |
| Open-Meteo Marine | Implemented subset / public point query | bounded request, model/grid/units/valid time, PostGIS rows, `/ocean/forecast` | no scheduler; no dense map; swell fields not in current canonical contract; `MODEL DATA` UI needed |
| NOAA MarineCadastre AIS | Implemented internal bounded import | official daily archive, checksum, U.S.-water bounds, time/record cap, dedup, PostGIS | no public record API, track/playback/analytics; restricted; not global |
| AISStream | Planned Phase 4 | configuration names only; no live feed implementation | terms, display/cache/retention rights, key, limits, worker, WebSocket, UI |

## 7.2 Source-specific rules

**UN/LOCODE**：它是全球运输地点代码，不是港口全集。只有 function code 支持的条目进入港口候选。保留 location code、country、name、function、coordinates、status、update value、data version 和 source。

**World Port Index**：用于港口坐标、设施、服务和属性。当前内部导入可用，但对外发布必须等待当前条款与再分发审查；WPI 不替代当前海图或出版物。

**USGS**：保存 event ID、magnitude、depth、longitude、latitude、event time、provider updated time、tsunami metadata 和 detail URL。官方更新同一事件时更新原事件，不重复插入。`tsunami` 字段不是 OceanScope 影响预测或警报。

**Open-Meteo Marine**：当前保存 wave height/direction/period、sea surface temperature、ocean current velocity/direction 和 sea level。必须显示 `MODEL DATA`、valid time、model/source、fetch time、cache state 和 coastal limitations。Swell 属于产品目标，但当前代码没有 swell canonical fields，因此状态是 Planned Hardening，而非 Implemented。

**MarineCadastre**：只允许描述为 `United States waters historical AIS`。当前证据是一个有边界、有上限、可重现的历史切片，不代表完整接收覆盖，也不支持“没有记录即没有船舶”。

**AISStream**：仍属于 Phase 4。接入前复核 terms、display rights、cache rights、retention、API key 和 connection/rate limits；Phase 4 前 README 或 Dashboard 禁止出现 `LIVE GLOBAL AIS`。

---

# 8. UI / UX & 3D Spatial Design

## 8.1 Design position

正式视觉定位：**Oceanic Spatial Intelligence Command Center**。关键词：cinematic、scientific、professional、high-density、spatial、readable、modern。界面保持 calm、map-first、dark maritime，不做传统廉价蓝色数据大屏，不使用全屏霓虹、持续闪烁、无限扫描线或无意义跳动数字。

参考视频可借鉴的只有：中央 3D Earth、global-to-region camera movement、空间高亮、路线可视化、HUD layering、左右信息轨、底部模块导航、地图与数据联动和高信息密度。必须去除航空名称、航班/机场/飞机语义、原素材、原图标、原文案和过度装饰。OceanScope 使用自己的 Maritime Spatial Intelligence Design Language。

## 8.2 Visual depth

| Layer | Purpose |
| --- | --- |
| L0 Space Background | 深海/太空背景与克制星场 |
| L1 Earth / Map | 地球、海陆、光照、大气、底图 |
| L2 Spatial Data | 港口、事件、环境、覆盖、轨迹、区域 |
| L3 HUD / Information | Top Bar、Context Rail、Inspector、Dock、Legend |
| L4 Selection / Alert | 当前选择、警告、焦点路径、交互反馈 |

震撼感来自 depth、camera、lighting、motion 和真实数据密度，不来自大量发光边框。

## 8.3 Command Center layout

```diagram
OCEANSCOPE COMMAND CENTER - DESKTOP

+-----------------------------------------------------------------------+
| Logo | GLOBAL / REGION / PORT / VESSEL | UTC | DATA | MODE | Search   |
+-----------+---------------------------------------------+-------------+
| Context   |                                             | Intelligence|
| Rail      |          Central Spatial Workspace          | Rail        |
|           |             55%-65% viewport                |             |
| layers    |        Cesium globe / MapLibre map          | evidence    |
| sources   |        selection / region / routes          | charts      |
| coverage  |                                             | provenance  |
+-----------+---------------------------------------------+-------------+
| Overview | Vessels | Ports | Regions | Environment | History | Data   |
+-----------------------------------------------------------------------+

Tablet/mobile: one contextual sheet at a time; map remains primary.
```

**Top Command Bar**：左侧 Logo 与 OceanScope；中间显示 GLOBAL / REGION / PORT / VESSEL / HISTORY；右侧显示 UTC、data status、connection status 和 CINEMATIC / BALANCED / PERFORMANCE。点击状态打开 Data Provenance Drawer。

**Left Context Rail**：内容随上下文改变。Global 显示 Layers、Data Sources、Recent Events；Region 显示 Selected Region、Traffic、Environment、Coverage；Port、Vessel、History 显示各自相关信息。

**Right Intelligence Rail**：随选择改变，不允许每个页面固定同一批卡片。数据、单位、有效时间、来源和警告放在其所限定值的附近。

**Bottom Module Dock**：Overview、Vessels、Ports、Regions、Environment、Traffic、History、Risk、Data，使用 icon + label；hover 轻微抬升，active 使用 cyan underline，不跳动、不大面积 glow。

## 8.4 Scene Director and motion

SceneDirector 通过配置管理 `GLOBAL`、`ASIA`、`EUROPE`、`NORTH_AMERICA`、`REGION`、`PORT`、`VESSEL`、`HISTORY_REGION`。普通 camera transition 为 800-1600 ms，大范围 globe fly 为 1500-2500 ms；用户开始拖动后立即取消自动 tour。

Motion token：Micro 120-180 ms；Panel 180-280 ms；Drawer 220-320 ms；Map fly 800-2500 ms；Pulse 1200-2200 ms。动画只表达选择、移动、状态变化、新事件或导航。`prefers-reduced-motion` 直接进入最终状态。

## 8.5 Performance modes

| Mode | Behavior |
| --- | --- |
| CINEMATIC | atmosphere、可控 bloom、animated trails、particles；仍需保持标签和来源可读 |
| BALANCED | atmosphere、basic trails、moderate effects；默认模式 |
| PERFORMANCE | no bloom、minimal particles、reduced labels、lower density、2D fallback |

降级顺序先视觉效果，后数据密度；任何采样或密度降低必须可见说明。

---

# 9. Two-Developer Collaboration

## 9.1 Roles and workload

| Developer | Formal role | Workload | Primary ownership |
| --- | --- | ---: | --- |
| Developer A | Project Lead + Full-Stack GIS Engineer | 65%-70% | 产品、架构、核心 React/TypeScript、UI/UX、Cesium/MapLibre/deck.gl/ECharts、3D Earth、Camera、SceneDirector、Layer Registry、Region Workspace、核心 API contract、核心 analytics、集成、README、Demo、Release |
| Developer B | Data & Platform Engineer | 30%-35% | providers、ingestion、validation、normalization、provenance、quality、Redis、PostGIS data ops、AIS/history pipelines、workers、backend data services、infra、CI/CD、backend/provider tests、performance pipeline、health/risk backend |

这不是绩效评价，而是减少重新交接成本和 Git 冲突。Developer B 不是 assistant/helper/secondary programmer，而是拥有完整独立模块的正式开发成员。

## 9.2 Existing Ownership Wins

Developer A 已实现的稳定 backend 模块保持现有 owner。不要为了职责表整齐而迁移、改名或重写。新的功能按新职责划分；跨 owner 改动必须有 Issue、contract 和 review。

```diagram
REPOSITORY OWNERSHIP

Developer A primary                 Developer B primary
apps/web                            providers / ingestion modules
GIS / map / visualization          workers / batch pipelines
UI design system                   backend data operations
core API contracts                 infra / performance pipelines
architecture / integration         provider + backend tests
               \                 /
                \               /
                 Shared surfaces
  root config | contracts | migrations | README | AGENTS | GitHub
                 |
        independent small PR + review
```

## 9.3 Contract-first parallel workflow

```diagram
CONTRACT-FIRST WORKFLOW

Issue: user outcome + scope + allowed paths + owner
   |
   v
Developer A defines/reviews typed contract + UX states
   |
   +------------------------------+
   |                              |
   v                              v
A: frontend against DEV fixture   B: backend/provider against contract tests
   |                              |
   +---------------+--------------+
                   v
          integration PR / real API only
                   |
                   v
     source + freshness + error + tests + docs

DEV fixture is allowed only in isolated development/test paths.
Production uses real API and never fixture fallback.
```

## 9.4 Dual-developer workflow

```diagram
DUAL DEVELOPER WORKFLOW

Backlog -> Ready contract -> Two short feature branches
                         /                         \
             Developer A UI/GIS          Developer B data/platform
                         \                         /
                          CI + owner review
                                  |
                             integration
                                  |
                       acceptance evidence / merge

No long-lived developer-a or developer-b branch.
No simultaneous migration creation.
No direct push to main.
```

---

# 10. Current Repository & Development State

## 10.1 Audit snapshot

本轮审计基线为 `main` 的 `48076ce feat: add real-data status UI (#15)`，随后完成并验证 Phase 2 收口变更。仓库目录以真实结构为准，没有为符合旧规划而创建平行目录。

| Area | Current evidence | Assessment |
| --- | --- | --- |
| Repository | root docs/config；`apps/api`、`apps/web`、`infra`、`scripts` | coherent modular monolith |
| Backend | FastAPI routes、services、repositories、providers、typed contracts | Implemented foundation + Phase 2 domain modules |
| Database | Alembic 0001-0006；PostGIS geography/indexes | Implemented；migration ownership must be serialized |
| Frontend | React 19 + TS 6 + Vite；minimal source/status surface | Phase 2 status UI only；no map or Data Explorer |
| Infra | Dockerfiles、Compose PostGIS/Redis/API/Web、Nginx | Implemented local foundation；production hardening pending |
| CI | Ruff、mypy strict、pytest/coverage、Prettier、ESLint、Vitest、build、Gitleaks | Implemented |
| Locks | `uv.lock`、`package-lock.json` | Implemented |
| Documentation | source verification、ADRs、phase records、risk/governance | strong evidence base；master PDF was stale V1.0 |
| PDF source | only V1.0 binary was present | V2.1 introduces maintainable Markdown source and reproducible build script |

## 10.2 Current System State

```diagram
CURRENT SYSTEM STATE - 2026-09-18

IMPLEMENTED
  Engineering foundation + CI + Compose + PostGIS migrations
  Provenance / source versions / ingestion runs / quality issues
  Official bounded imports: UN/LOCODE, WPI, USGS, Open-Meteo, MarineCadastre
  APIs: health, system status, data sources, ports, earthquakes, ocean forecast
  Minimal data/source status web UI
  Reproducibility manifest export + complete quality/Compose/smoke gate

POST-PHASE-2 FOLLOW-UP
  manual browser visual, responsive and accessibility review
  Data Explorer + NO COVERAGE / MODEL DATA user semantics

PLANNED
  Cesium/MapLibre spatial shell, region workspace, live AIS, history playback,
  analytics, risk, advanced visualization, evidence-first intelligence
```

## 10.3 API inventory

当前 FastAPI 暴露：`/health/live`、`/health/ready`、`/system/status`、`/data/sources`、`/ports`、`/earthquakes` 和 `/ocean/forecast`。其中 `/health/ready` 当前只报告进程级 ready，不探测数据库；实际依赖状态在 `/system/status`。这不是 Phase 1 失败，但属于 hardening backlog，需要保持文案准确。

---

# 11. Phase 0 Retrospective

**Status：COMPLETED。** 不重做 Phase 0。V2.1 retrospective 只检查并修正以下内容：

| Review item | Result |
| --- | --- |
| Project positioning | 非商业、学习研究、GitHub Portfolio、非导航边界已明确 |
| Real data principle | 已成为仓库永久规则；没有允许生产伪造的 fallback |
| Data licensing | 来源文档和 redistribution gate 已存在；WPI/AISStream 仍需复核 |
| Maritime terminology | 正文保持海事语义；参考视频航空语义不迁移 |
| Historical AIS coverage | 明确 MarineCadastre 仅美国水域、历史、非完整覆盖 |
| Real-time AIS plan | 保持 Phase 4，当前不得声明 LIVE GLOBAL AIS |
| Risk wording | 使用 indicator / rule hit / requires review，不推断违法、危险或意图 |
| AI boundary | evidence-first，模型不得生成确定性数值 |
| GitHub positioning | 公开作品集但不假装完成或生产可用 |
| Two-developer collaboration | Developer A 65%-70%；Developer B 30%-35%；Existing Ownership Wins |
| UI baseline | Oceanic Spatial Intelligence Command Center + map-first + restrained motion |
| Feature/data coverage | 本文档新增双矩阵和明确状态词典 |

Retrospective 新增交付物：Feature Coverage Matrix、Data Coverage Matrix、Innovation Roadmap、Collaboration Baseline、UI Design Baseline。

---

# 12. Phase 1 Hardening

**Status：COMPLETED，Engineering Hardening Review 持续。** 禁止重新初始化 React、FastAPI、PostgreSQL、Redis 或 Docker。

| Capability | Current state | Hardening action |
| --- | --- | --- |
| TypeScript strict | Implemented via project tsconfig/build | 保持；新 GIS 类型纳入相同门禁 |
| Python type checking | mypy strict implemented | 保持；provider/worker 不得绕过 |
| lint / format | Ruff、ESLint、Prettier implemented | 禁止 feature PR 全项目格式化 |
| unit/integration tests | pytest、Vitest、PostGIS integration evidence | 增加 browser E2E、Redis、地图交互和性能测试 |
| CI / secret scan | GitHub Actions + Gitleaks implemented | 增加 dependency/container/security checks as phases require |
| structured logging | structlog + correlation ID implemented | 增加 ingestion/provider metric context |
| health endpoint | live/ready + system status exist | 明确 `/health/ready` 依赖语义或保持进程级并改名/文档化 |
| environment isolation | typed settings + `.env.example` | 保持 keys server-side；前端无 provider secret |
| Docker reproducibility | API/Web images + Compose | 添加 image scanning、release digest/SBOM later |
| dependency locking | uv + npm locks | 保持依赖引入理由与 license review |

Phase 1 不因新开发者加入而重建。任何缺口作为独立 hardening issue，不与 Phase 3 功能 PR 混合。

---

# 13. Phase 2 Complete & Follow-up

**Status：COMPLETED。** `docs/26-phase-2-gate-verification.md` 已记录最终自动化、迁移、Compose、真实查询和 manifest export 证据。该结论不自动授权 Phase 3；正式启动仍需 owner 明确批准。

## 13.1 Implemented

- source catalog、source version、ingestion run、quality issue、freshness/cache policy；
- UN/LOCODE、WPI、USGS、Open-Meteo、MarineCadastre 的真实受限导入；
- checksum、raw artifact reference、idempotent/version-aware persistence；
- PostGIS geography 与空间索引；
- `/data/sources`、`/system/status`、`/ports`、`/earthquakes`、`/ocean/forecast`；
- minimal real-data status UI；
- internal reproducibility manifest contract；
- WPI/MarineCadastre public redistribution gates；
- test-only fixtures 隔离并标注 `TEST DATA`。

## 13.2 Gate evidence and follow-up

**Completed gate evidence**：

- 已完成真实 ingestion run 的 production-container manifest export；
- 已完成 backend/frontend quality gate、一次性 PostGIS migration test、Compose health 和 public query smoke checks；
- 已同步 README、API docs、risk 和 Phase 2 gate record；
- 已确认 production 没有 fixture fallback、fake/random/zero fill；
- 自动化环境没有可用浏览器，因此人工视觉、响应式和可访问性检查作为非阻塞限制保留。

**Post-Phase-2 follow-up / Phase 3 input**：

- 实现 `/data/explorer` 的 Port、Earthquake、Marine、Coordinate 基础查询；
- 为无覆盖结果显示 `NO COVERAGE`，为模型值显示 `MODEL DATA`；
- Region BBOX 查询和数据覆盖说明；
- System Health 对 Redis、provider/latest run 的更完整状态；
- Open-Meteo swell contract 或明确保持为后续字段；
- 自动调度设计和失败重试策略，未实现前继续标为 operator initiated。

**Future**：

- WPI public records after terms review；canonical port entity resolution；dense environment tiles；historical AIS public queries、tracks、playback。

## 13.3 Current Phase 2 ownership

| Developer A - Phase 2 Lead | Developer B - Data & Platform |
| --- | --- |
| Data Sources UI、System Health UI、Data Explorer、Coordinate/Region Query UI、Design Tokens、Status Components、Source Badge、Freshness/Cache/Offline/NO COVERAGE、frontend adapters、API contracts、Command Center shell preparation | review current providers、UN/LOCODE/WPI/USGS/Open-Meteo validation、provenance/freshness/cache backend、system health backend、region spatial query、provider contract tests、API tests |

Developer A 不需等待全部 backend hardening 才开始 Phase 3 preparation，但准备工作不能被宣传为 Phase 3 已完成。

---

# 14. Phase 3 Digital Earth

**Status：NEXT；Phase 2 gate 已通过，但正式进入仍需 owner 明确批准。**

**Must**：OceanScope Command Center、Cesium globe、MapLibre analytical mode、SceneDirector、Camera presets、Layer Registry、Region Workspace、Top Bar、Left/Right Rails、Bottom Dock、Port Layer、Earthquake Layer、Environment Layer、Source Lens、Data Confidence UI、Command Palette、URL Workspace State、reduced motion、BALANCED/PERFORMANCE。

**Should**：Global/Region/Port scene presets、linked map/inspector、coordinate readout、responsive drawers、basic chart-map interaction、visual regression and reference-hardware profiling。

**Future**：cinematic startup、advanced camera tour、GPU particles、3D analytical layers。

```diagram
REGION WORKSPACE FLOW

Draw Rectangle | Draw Polygon | Preset | BBOX Input | Existing Region
                              |
                              v
                Validate WGS 84 geometry and limits
                              |
                              v
                   Set Current Region Context
                              |
        +----------+----------+----------+----------+
        v          v          v          v          v
      Ports      Events   Environment  Coverage   History/Traffic
        |          |          |          |          |
        +----------+----------+----------+----------+
                              v
              shared map / charts / URL state / provenance
```

```diagram
SPATIOTEMPORAL LENS

Region Geometry + Time Window + Source/Layer Filters
                         |
                         v
              One deterministic query context
                         |
        +----------------+----------------+
        v                v                v
      Map              Charts          Indicators
        ^                |                |
        |                v                v
        +--------- linked selection / brushing --------+

No result -> EMPTY or NO COVERAGE or DATA UNAVAILABLE,
never an invented zero or percentage.
```

**Developer A**：主导 UI/GIS、Cesium/MapLibre、camera、layer registry、HUD、region context、source/confidence lens、command palette、map/chart interaction。<br>
**Developer B**：BBOX/viewport/PostGIS queries、port optimization、environment proxy、earthquake query、region summary、cache、provider health、backend tests。

---

# 15. Phase 4 Live AIS

**Objective**：通过后端代理接入真实 AISStream，形成有边界、可恢复、可观察的实时船舶体验。

**Must**：terms and rights review、server-side key、AIS adapter、validation/normalization/deduplication、Redis latest state、PostGIS bounded storage、WebSocket gateway、reconnect/backpressure/bounded queue、retention、Vessel Explorer/Detail、search、LOD、track gap、observation/ingestion times、connection UI。

**Should**：viewport/MMSI filtering、camera follow、recent track、cluster/density、identity conflict display、load/soak/failure tests。

**Future**：selected-vessel 3D model、multi-provider abstraction、advanced trail animation。

LOD 标准：World 使用 density/cluster；Region 使用 GPU marker；Local 使用 oriented vessel marker；Selected 才显示 heading、track 和可选详细模型。禁止全球渲染数万复杂 3D 船模。

Track 视觉标准：Observed Position = solid point；Observed Track = solid line；Interpolated Segment = lower opacity；Data Gap = dashed/visible gap；Aggregated Flow = thicker separate style；Analysis Boundary = cyan thin polygon；Warning = amber；Route 不得与 Observed Track 混淆。

**Developer A**：Vessel Explorer/Layer/Inspector/Detail/Search、track、cluster、LOD、heading、animation、gap、camera follow、connection UI。<br>
**Developer B**：AISStream adapter、ingestion、validation、normalization、dedup、Redis/PostGIS、recent track/search backend、WebSocket、reconnect/backpressure/queue/retention。

---

# 16. Phase 5 Historical Intelligence

**Objective**：把受限的美国水域 MarineCadastre 归档变成可复现的历史回放和交通分析，不扩大数据覆盖声明。

**Must**：manifest/checksum、streaming import、partition/dedup、track segmentation、historical API、Time Machine、Play/Pause/Seek、1x/5x/20x/60x、dataset/coverage/time/record/unique-vessel/source 显示、density and traffic aggregates。

**Should**：Traffic Heatmap、Vessel Density、type/speed/hour/day/direction distributions、port vicinity traffic、period comparison、Corridor Intelligence、chart-map linking、sampling disclosure。

**Future**：additional compliant archives、export after terms review、longer-term materialized aggregates。

Corridor / Traffic Gate 允许用户绘制虚拟截线或选择航道，统计真实轨迹 crossing count、unique vessels、direction、speed、type、hour distribution 和 trend。覆盖不足时显示 `INSUFFICIENT COVERAGE`，不能自动编差异百分比。

**Developer A**：History UI、timeline、playback、heatmap、flow map、Traffic Intelligence、Compare、Spatiotemporal Lens、Corridor UI、chart-map linking。<br>
**Developer B**：MarineCadastre importer、manifest/checksum、Polars/DuckDB pipeline、partition/dedup、segmentation、historical API、aggregation、traffic/corridor computation。

---

# 17. Phase 6 Risk & Anomaly

**Objective**：提供可解释、可复算、需要人工审查的指标，而不是“危险船舶检测器”。

**Must rules**：Geofence Entry/Exit、Speed Threshold、Course Change、Loitering、Observation Gap、Environment Threshold、Nearby Earthquake。每个结果保存 rule ID/version、threshold、window、supporting observations、source、coverage quality、reason 和 review state。

**Allowed language**：indicator、rule hit、observation gap、unusual pattern、requires review。禁止在没有权威证据时使用 criminal、illegal、dangerous vessel、smuggling、collision risk 等结论。

Environmental Context 将 vessel speed/course 与 wave/current/valid time 对齐，只表达 context/correlation，不宣称环境导致行为。Port Activity Index 只能作为透明 `DERIVED` metric，公开公式、窗口、输入和版本，不能写成 Official Congestion Index。

**Developer A**：Risk Center/Layer、Geofence UI、Evidence Drawer、Event Timeline、Rule Explanation、Environmental Context UI。<br>
**Developer B**：geofence/speed/course/loitering/gap engines、evidence storage、rule version/recompute、backend calibration support。

---

# 18. Phase 7 Advanced Visualization

**Objective**：在不改变数值与语义的前提下增强多尺度空间分析和演示质量。

**Must**：GPU heatmap/hexbin/flow、server aggregation、adaptive LOD、legend/unit/range、visual correctness tests、capability detection、performance budgets、accessible fallback。

**Should**：3D Data Columns、current particles、scene presets、camera tour、cinematic mode、linked compare view、binary/optimized payloads。

**Constraints**：particle animation 不得扭曲物理意义；3D column height 必须对应真实值；任何 density、scale、sampling、range 都可见；reduce-motion 和 PERFORMANCE 模式保留分析意义。

**Developer A**：约 80% 主导 GPU visualization、heatmap/hexbin/flow/columns/particles、tour/presets、advanced interaction、visual polish。<br>
**Developer B**：server aggregation、precomputation、optimized payload、query optimization、cache、profiling。

---

# 19. Phase 8 Intelligence

**Objective**：构建 Evidence-first Intelligence，而不是普通聊天包装器。

用户请求“总结选中区域过去 24 小时情况”时，系统先由 deterministic backend 查询 traffic、environment、events、coverage 和 explainable indicators，生成 Structured Evidence Package；模型只能 summarize、explain、organize，不能自行生成 vessel count、wave height、earthquake count 或 risk count。

Natural Language Spatial Query 属于 Research。模型只解析 region、filter、metric、threshold、time，并由用户确认后执行真实 query。Situation Report 可针对 Port、Region、Vessel 生成 Current State、Traffic、Environment、Events、Data Quality、Notable Changes，每个重要结论链接来源。

**Developer A**：use cases、evidence UX、report/summary presentation、citation and refusal UI、integration/release。<br>
**Developer B**：structured evidence backend、deterministic query assembly、data access policy、evaluation datasets、cost/latency telemetry。两者共同完成 grounding/security/evaluation review。

---

# 20. Phase 9 Quality & Security

**Must**：threat model、SAST/dependency/container/secret scans、API and WebSocket limits、browser matrix、WCAG 2.2 AA review、load/soak/failure tests、PostGIS query regression、migration rollback、backup/restore、incident and disaster runbooks、SBOM。

**Acceptance**：无未处理的 critical/high finding；支持浏览器、可访问性、恢复、负载和故障目标有证据；文档与行为一致。Phase 9 不能代替前面各 Phase 的持续测试，它是发布候选的系统级收口。

---

# 21. Phase 10 Release

**Objective**：发布真实、可回滚、成本可控、公开声明准确的第一个生产版本。

**Must**：terms/attribution review、production config、TLS/DNS/security headers、migrations、smoke/source-state checks、monitoring and budget alerts、backup schedule、rollback rehearsal、release notes、screenshots/demo、known limitations、SECURITY/CITATION/CHANGELOG/third-party notices。

只有 Phase 9 gate 通过、所有公开来源条款适合部署、fresh deployment 验证成功后，才能标记 v1.0.0。任何 planning snapshot、prototype 或 backend-only 能力都不能写成 production feature。

---

# 22. Feature Coverage Matrix

| Feature | User value | Real source | Backend | Frontend | Phase | Owner | Test | Current status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Command Center | 统一空间入口 | all visible sources | Planned | Planned | 3 | A lead / B queries | visual/E2E/perf | Planned |
| Data Sources | 判断来源与时效 | source catalog | Implemented | minimal status surface | 2 | A UI / B backend | API/component | Partially Implemented |
| System Health | 诊断依赖与状态 | runtime probes | API+DB implemented | minimal | 2 | A UI / B backend | API/component | Partially Implemented |
| Data Explorer | 用坐标/条件查询真实数据 | ports/USGS/Open-Meteo | three queries implemented | Missing | 2 | A lead / B spatial | contract/E2E | Backend Ready |
| Port | 搜索港口参考记录 | UN/LOCODE; WPI internal | bounded search | Missing | 2-3 | A UI / B optimization | API/GIS/E2E | Backend Ready |
| Region | 共享空间分析上下文 | multi-source | Missing | Missing | 3 | A context / B query | geometry/E2E | Planned |
| Environment | 检查模型海况 | Open-Meteo | point query subset | Missing | 2-3 | A UI / B provider | unit/API/GIS | Backend Ready |
| Vessel | 船舶搜索与详情 | AISStream later | Missing | Missing | 4 | A UI / B backend | stream/E2E/load | Planned |
| Live AIS | 实时船舶态势 | AISStream | Missing | Missing | 4 | A map / B worker | contract/soak | Planned |
| History | 受限美国水域回放 | MarineCadastre | internal import only | Missing | 5 | A UI / B pipeline | reproducibility/perf | Partially Implemented |
| Traffic | 密度、组成、趋势 | historical/live AIS | Missing | Missing | 5 | A UI / B aggregate | numeric/perf | Planned |
| Corridor | 截线流量统计 | trajectory data | Missing | Missing | 5 | A UI / B compute | geometry/coverage | Planned |
| Compare | 区域或时段对比 | deterministic APIs | Missing | Missing | 5 | A lead / B aggregate | equivalence/E2E | Planned |
| Risk | 可解释规则指标 | AIS/events/environment | Missing | Missing | 6 | A UI / B rules | boundary/recompute | Planned |
| Source Lens | 当前画面来源与覆盖 | provenance | metadata exists | Missing | 3 | A lead / B metadata | UI/contract | Planned |
| Data Confidence | 区分无船与无数据 | health/age/density | Missing | Missing | 3-6 | A UI / B formula | calibration/UX | Planned |
| Evidence AI | 基于证据解释 | structured evidence | Missing | Missing | 8 | A product / B evidence | grounding/security | Research |

---

# 23. Data Coverage Matrix

| Dataset | Provider | Geographic coverage | Temporal coverage | Mode | Update | License / terms | Cache | Used by | Limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UN/LOCODE | UNECE | global transport locations | release snapshot `2025-1` in verification | reference | release-based | official terms; public rows allowed by current catalog | 400-day max policy | ports/data | not every entry is a port; coordinates may be absent |
| World Port Index | NGA | global named ports | content-addressed snapshot | reference | official publication/service | attribution required; redistribution remains `unreviewed` | 180-day max policy | internal ports/status | not navigation authoritative; public records blocked |
| Earthquake GeoJSON | USGS | global events in selected feed | imported past-hour snapshots | event / near-real-time summary | about one minute feed updates | public-domain USGS policy with attribution | 1-hour max | events/data | feed revisions; not historical completeness or tsunami prediction |
| Marine Forecast | Open-Meteo | requested model grid points | imported hourly forecast window | MODEL DATA | model-dependent, commonly 6-24 h | free endpoint non-commercial; CC BY 4.0 attribution | 48-hour max | ocean/data | model/coastal uncertainty; current contract lacks swell |
| Historical AIS | NOAA MarineCadastre | United States waters only | selected dated archives, bounded slice | historical | archive-based | current redistribution recorded restricted | checksum-pinned cache | internal history | receiver gaps; capped sample; not global or complete |
| Live AIS | AISStream | provider-defined subscription bounds | future live stream | realtime | streaming | must reverify display/cache/retention rights | not defined | vessels/live | no current implementation, no SLA or durable replay claim |

---

# 24. Innovation Roadmap

创新以解决真实分析问题为标准，不以使用多少 AI 或视觉效果为标准。

```diagram
INNOVATION ROADMAP

FOUNDATION
  provenance -> freshness -> coverage -> bounded spatial queries
       |
       v
CORE SPATIAL INNOVATION
  1 Region Workspace
  2 Spatiotemporal Lens
  3 Data Confidence Layer
  4 Corridor Intelligence
  5 Source Lens
       |
       v
ANALYTICAL EXPERIENCE
  6 Compare Mode
  7 Environmental Context
  8 Explainable Anomaly
       |
       v
EVIDENCE INTELLIGENCE
  9 Evidence-based Intelligence
 10 Natural Language Spatial Query [Research]
```

## 24.1 Data Confidence Layer

Data Confidence 解决 `NO VESSEL` 与 `NO DATA` 不同的问题。初始等级可以是 HIGH / MEDIUM / LOW / NO COVERAGE，依据 source availability、data age、observation density、provider health 和 known coverage。公式、阈值、窗口、版本与输入必须公开；在没有验证前只显示诊断维度，不产生看似权威的综合分数。

## 24.2 Source Lens

开启后突出 provider、coverage、last update、data age、cache、quality、license/attribution。用户应能从当前地图直接回答“画面是谁的数据、何时有效、是否缓存、能否用于公开展示”。

## 24.3 Event Timeline

统一事件类型：Earthquake、Provider Offline/Delayed、Geofence、Anomaly Indicator、Data Gap、System Event、future Intelligence Report。点击事件跳转到 location、time 和 context，并保留来源和证据。

## 24.4 URL Workspace State and Scene Presets

在没有账号系统时，将 camera、region、layers、time、filters、selected entity 编码到 URL。Scene Presets 只保存 scene + layer configuration，包括 Global Overview、Port Intelligence、Live Traffic、Historical Playback、Ocean Environment、Risk Review、Traffic Analysis；preset 不得包含 fake data。

---

# 25. Testing Strategy

## 25.1 Quality layers

| Layer | Required evidence |
| --- | --- |
| Static | Ruff format/lint、mypy strict、ESLint、Prettier、TypeScript build、secret scan |
| Unit | 时间、单位、坐标、角度、状态、去重、版本、边界、错误语义 |
| Provider contract | schema drift、HTTP failure、limits、terms metadata、no zero-fill、fixture isolation |
| Database | migrations、upgrade/downgrade、PostGIS SRID/index/query、idempotency、redistribution gate |
| API | bounds、pagination、problem+json、freshness/cache/no coverage、provenance |
| Frontend | loading/empty/error/offline/delayed/cached/live/no coverage/model data、keyboard/responsive |
| E2E | coordinate query、region selection、map/detail/link state、history/risk flows by phase |
| Visual | screenshots across desktop/tablet/mobile、text overlap、attribution、contrast、reduced motion |
| Performance | viewport cancellation、payload、query latency、FPS/memory、stream burst/backpressure |
| Reproducibility | checksum -> manifest -> import -> query -> chart/claim trace |

## 25.2 Completion commands

每个任务至少运行相关 checks；共享或 gate 任务运行 `python scripts/check.py`、`git diff --check` 和配置的 secret scan。数据库集成测试只能使用明确命名的 disposable test database。任何测试跳过必须报告原因，不能把“未运行”写成“通过”。

地图可视化还必须检查：数据点、线、面、柱、粒子、聚合与数值一致；单位和 legend 正确；缩放和时间行为可解释；降级不改变核心意义。

---

# 26. Security

- API keys 只在服务器端 SecretStr/环境配置中存在，不进入浏览器 bundle、日志、截图、Issue 或 fixture。
- 外部输入执行大小、时间、空间、分页、几何复杂度和内容类型限制；URL 和 provider endpoint 使用 allowlist/固定 adapter。
- SQL 使用参数化 repository 查询；空间查询必须有 bounds 和限额。
- CORS、headers、WebSocket origin/auth/rate/backpressure 在对应 Phase 配置和测试。
- raw archives、database volumes、local caches、personal paths 和 restricted data 不提交仓库。
- public query 必须经过 license/redistribution gate；内部可用不等于可公开。
- Intelligence 不接收未经批准的 restricted raw data、secrets 或不可信文本指令；外部文本视为数据而非指令。
- release 前完成 container scan、SBOM、backup/restore、incident response 和 secret rotation rehearsal。

---

# 27. GitHub / Codex Workflow

## 27.1 Branch and PR rules

禁止长期 `developer-a` / `developer-b` 分支。使用短生命周期功能分支：`ui/*`、`gis/*`、`api/*`、`data/*`、`ais/*`、`history/*`、`risk/*`、`infra/*`、`test/*`、`docs/*`、`contract/*`、`fix/*`。

`main` 禁止直接 push。每个 feature 经过 branch -> PR -> CI -> owner review -> merge。PR 不得顺手改无关文件、全项目 format、rename 大量目录、修改另一 owner 模块或进行无关大型 refactor。shared file 使用独立小 PR。

数据库 migration 不能由两人同时创建。Developer B 可以提出 schema change，最终 migration 由 Developer A 创建或 review，避免 Alembic branch conflict。

## 27.2 Codex start protocol

每次 Codex 开始任务先读取：`AGENTS.md`、current branch、`git status`、Issue Scope、Allowed Paths、Forbidden Paths。完成前运行 format、lint、typecheck、tests、`git diff --check` 和已配置 secret scan；报告 changed files、tests、limitations。禁止 unrelated refactor、cross-owner change、global formatting、silent architecture change、secret commit 和 fake production data。

## 27.3 Small PR contract

每个 Issue 明确：user outcome、owner、scope/non-scope、allowed/forbidden paths、API/data contract、source/coverage、UI states、acceptance evidence、risk、rollback。Contract change 单独 PR 或先合并；前端可在隔离 DEV fixture 上并行，production 只能连接真实 API。

---

# 28. Risk Register

| Risk | Likelihood / Impact | Control | Owner / Gate |
| --- | --- | --- | --- |
| AIS outage / no replay | High / High | reconnect、gap labels、bounded queue、cache semantics、no invented positions | B / Phase 4 |
| API rate limit / schema drift | Medium / High | typed adapters、bounds、backoff、schema tests、version pinning | B / every source |
| Data licensing / redistribution | Medium / Critical | terms review、catalog gate、attribution、block public records | A decision + B evidence |
| Historical data volume | High / High | bounded region/time/cap、streaming、partition、benchmarks | B / Phase 5 |
| GPU/browser performance | Medium / High | LOD、capability detection、modes、2D fallback、profiling | A / Phase 3+ |
| Secret leakage | Low / Critical | server-only keys、Gitleaks、redaction、rotation | shared / CI+release |
| Data freshness confusion | Medium / High | controlled states、age、source-specific policy、no silent fallback | shared / Phase 2 |
| AI hallucination | High / High | deterministic evidence、citations、schemas、refusal、evaluation | shared / Phase 8 |
| Merge conflict | Medium / Medium | ownership、allowed paths、small PR、short branches | shared / continuous |
| Contract drift | Medium / High | contract-first PR、schema tests、versioning、integration check | A contract / B impl |
| Duplicate implementation | Medium / Medium | Existing Ownership Wins、issue inventory、owner review | A / planning |
| New developer onboarding | Medium / Medium | module map、runbook、starter issue、paired contract review | A / current |
| Codex unrelated changes | Medium / High | AGENTS rules、allowed/forbidden paths、diff review | task owner / every PR |
| Frontend/backend mismatch | Medium / High | typed contract、fixture schema、contract tests、same-PR integration | shared / Phase 2+ |
| Migration conflict | Medium / High | one migration author at a time、A create/review、serialized PR | A / database |
| No coverage interpreted as zero | High / High | explicit NO COVERAGE、confidence layer、coverage tests | shared / Phase 2+ |
| Model data treated as observation | Medium / High | MODEL DATA label、valid time/model/source/warning | shared / ocean UI |

---

# 29. Decision Log

| ID | Decision | Status / rationale |
| --- | --- | --- |
| D-01 | Modular monolith is default | Accepted；当前规模不支持提前微服务化 |
| D-02 | PostGIS for spatial operations | Accepted；geography/WGS 84 boundary and metric correctness |
| D-03 | Real-data-first; no production fixture fallback | Accepted；永久规则 |
| D-04 | Phase 0 and Phase 1 remain completed | Accepted；不因新成员或文档升级重建 |
| D-05 | Phase 2 Real Data Foundation gate passed | Accepted；`docs/26` 记录验收证据，人工浏览器检查为非阻塞后续项 |
| D-06 | Developer A remains Project Lead, 65%-70% | Accepted；保护产品/架构连续性 |
| D-07 | Developer B owns meaningful data/platform modules, 30%-35% | Accepted；支持真正并行而非辅助角色 |
| D-08 | Existing Ownership Wins | Accepted；避免无价值迁移与冲突 |
| D-09 | Contract-first + small PR + no direct main push | Accepted；双人协作基线 |
| D-10 | MarineCadastre means U.S.-water historical AIS only | Accepted；禁止全球历史覆盖声明 |
| D-11 | AISStream remains Phase 4 | Accepted；条款与真实接入前不宣称 live global AIS |
| D-12 | OceanScope Command Center is Phase 3 primary surface | Accepted；map-first 55%-65% viewport |
| D-13 | Innovation order follows coverage and provenance | Accepted；Region/Time/Confidence before AI |
| D-14 | PDF V2.1 source is Markdown with reproducible ReportLab build | Accepted；旧仓库只有二进制 V1.0，无源文件 |

---

# Appendix A. Design Tokens

| Token | Value | Meaning |
| --- | --- | --- |
| `--bg-space` | `#02060D` | space background |
| `--bg-deep` | `#050B14` | main dark canvas |
| `--surface-1` | `#071421` | base surface |
| `--surface-2` | `#0A1929` | secondary surface |
| `--surface-elevated` | `#0D2236` | elevated panel |
| `--surface-glass` | `rgba(7,20,33,0.78)` | readable glass |
| `--border-subtle` | `rgba(75,170,220,0.20)` | low emphasis border |
| `--border-active` | `rgba(57,216,255,0.60)` | selected border |
| `--cyan` | `#39D8FF` | selected / active / observation |
| `--blue` | `#4C7DFF` | normal spatial data |
| `--blue-strong` | `#245EEB` | high emphasis normal data |
| `--green` | `#42E6A4` | healthy |
| `--amber` | `#F4B942` | warning / delayed |
| `--red` | `#FF5A6B` | critical / offline |
| `--violet` | `#A878FF` | derived / model / analysis |
| `--text-primary` | `#E9F7FF` | primary text |
| `--text-secondary` | `#95AEC1` | secondary text |
| `--text-muted` | `#637D91` | muted text |

颜色必须具有语义，不能为了漂亮随机分配。所有状态同时使用文字、颜色和必要的形状/图标。

---

# Appendix B. Status Vocabulary

| Status | User meaning | Required UI evidence |
| --- | --- | --- |
| LIVE | 当前 freshness policy 内可用 | source、effective time、last update |
| CACHED | 使用政策内已验证副本 | cache label、age、original source/version |
| DELAYED | 数据超出正常更新但仍在可用窗口 | delay/age、warning |
| OFFLINE | 无可接受当前或缓存数据 | DATA UNAVAILABLE、last attempt/error summary |
| NO COVERAGE | 来源不覆盖请求空间/时间 | coverage boundary/reason；不得显示 0 |
| MODEL DATA | 数值模型结果 | model、valid time、grid/source、uncertainty |
| DERIVED | 算法或规则结果 | formula/version/input/window |
| TEST DATA | 测试专用 | isolated path and visible label；never production fallback |

---

# Appendix C. Audit Evidence and Open Confirmations

## C.1 Evidence inspected

- Git branch/status and latest 20 commits；
- root README、AGENTS、CONTRIBUTING、lockfiles、environment template；
- `.github/workflows/ci.yml` and repository templates；
- FastAPI routes, services, repositories, providers, contracts and Alembic 0001-0006；
- React source/status UI and component tests；
- Dockerfiles, Compose, Nginx and local check script；
- Phase 1 verification and Phase 2 source/query/freshness/manifest/gate records；
- V1.0 PDF（28 pages，ReportLab 生成，无可维护源文件）；
- 参考视频（110.4 s，1280 x 592），仅提取布局、镜头、空间高亮和 HUD 结构特征。

## C.2 Human confirmations still required

1. WPI 当前版本的公开再分发条款和 attribution；
2. AISStream public display、cache、retention、redistribution、rate/connection limits；
3. 首个 Phase 4 live AIS demo region 与数据保留预算；
4. Phase 3 map tile/terrain provider、terms、成本和 attribution；
5. Phase 2 支持浏览器的手工视觉/响应式/可访问性验收；
6. Data Confidence 的公式、阈值和公开解释方式；
7. Developer A/B 的 GitHub CODEOWNERS 账号映射；
8. production hosting、budget ceiling、domain、monitoring and backup owner。

## C.3 Next recommendation

Phase 2 gate 已关闭。下一步由 owner 明确批准 Phase 3 后，再由 Developer A 在独立 branch 开始 design tokens、Command Center shell、Cesium proof-of-concept、Layer Registry contract 和 Region Workspace interaction spec；Developer B 可以实现 BBOX/viewport/region-summary contract。浏览器视觉验收、Data Explorer、NO COVERAGE 和 MODEL DATA 用户语义继续作为明确的后续工作，不得被误写为已实现。

---

# Appendix D. Official Source References

- AISStream documentation: [https://aisstream.io/documentation](https://aisstream.io/documentation)
- NOAA MarineCadastre AIS: [https://marinecadastre.gov/ais/](https://marinecadastre.gov/ais/)
- MarineCadastre AccessAIS: [https://marinecadastre.gov/accessais/](https://marinecadastre.gov/accessais/)
- UNECE UN/LOCODE publications: [https://unlocode.unece.org/publications/](https://unlocode.unece.org/publications/)
- NGA World Port Index: [https://msi.nga.mil/Publications/WPI](https://msi.nga.mil/Publications/WPI)
- Open-Meteo Marine API: [https://open-meteo.com/en/docs/marine-weather-api](https://open-meteo.com/en/docs/marine-weather-api)
- Open-Meteo terms: [https://open-meteo.com/en/terms](https://open-meteo.com/en/terms)
- USGS GeoJSON feeds: [https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)

这些链接是审计时使用的官方入口。集成或公开发布前必须重新核对当前 terms、limits、schema、attribution 和 redistribution rights；文档链接本身不构成授权。
