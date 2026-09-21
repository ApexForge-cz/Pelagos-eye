# OceanScope Phase 4+ 双人协作与分阶段交付计划

> 版本 1.1 | 2026-09-22 | 面向 Developer A 与 Developer B 的执行文档
>
> **状态：协作规划。** 本文不改变 `README.md` 中的阶段授权，也不把计划中的能力写成已实现。Phase 4 Live AIS 仍为 `Planned`；Pelyr 来源权利已完成文档核验，但 Issue `#37` 的自助凭据、来源目录和覆盖 smoke 门禁通过前不得开始生产接入。

本文以原 `OceanScope Phase 4+ 全面优化与负责人增量路线图` 为产品方向基线，重新安排双人协作方式。Developer A 继续负责产品、架构、前端、GIS、集成和发布；Developer B 的总任务比例保持约 30%–35%，但改为更适合大一阶段的渐进式任务：先通过测试和诊断理解现有系统，再进入数据处理、性能验证和受门禁保护的实时数据工作。

## 1. 当前基线与目标

截至 2026-09-22：

- Phase 0、Phase 1、Phase 2 和 Phase 3 已完成；不得重复初始化或改写既有完成记录。
- Phase 4 Live AIS 仍为 `Planned`。芬兰湾固定边界、Pelyr `/v1` position-only、单后端连接、原始消息零持久化和无轨迹尾迹只是已冻结的规划边界，不代表已实现。
- Pelyr API Terms 1.5 与 Data Licence 1.1 已核验；项目 Issue `#37` 仍需 Developer A 完成自助 Key、`welcome.sources[]`、有效 limits、署名和芬兰湾覆盖 smoke。完成前禁止生产 provider、路由、存储或公开 Live AIS 声明。
- Developer B 的 B1 与 B2 已完成并合并，后续阶段从 B3 继续，不重做已验收阶段。
- 本计划只重新安排未来工作颗粒度，不改变历史所有权，也不把双人分工改成 50/50。

本计划的目标是同时满足四件事：

1. Developer B 获得连续且可验收的学习路径，而不是一次承担完整数据平台。
2. Developer A 与 Developer B 在大多数时间修改不同目录，可以同步开发。
3. 合同、迁移和公共配置仍串行处理，避免高风险冲突。
4. 每项能力只有在代码、测试、来源、状态、性能和文档证据齐全后才改变完成状态。

## 2. 固定角色与工作量

| 角色 | 总体比例 | 主责 | 不转移的最终责任 |
| --- | ---: | --- | --- |
| Developer A / Project Lead | 65%–70% | 产品方向、架构、核心合同、`apps/web`、GIS/地图、可视化、跨模块集成、演示和发布 | 阶段授权、合同接受、迁移复核、最终验收和发布声明 |
| Developer B / Data & Platform Engineer | 30%–35% | provider 测试、ingestion 诊断、数据质量、历史导入性能、后端失败测试、基础设施 smoke、获批后的实时数据适配 | 自己阶段内的实现、测试、证据文档和 PR 说明 |

比例按 Phase 4–10 的总工作量计算，不要求每个阶段机械地达到同一百分比。任务数量也不等于工作量：Developer B 可以有更多小阶段，但每个阶段范围更窄；Developer A 仍承担主要设计、集成、前端、GIS 和发布风险。

### 适合 Developer B 的学习顺序

Developer B 按“读懂行为 -> 写测试 -> 写只读诊断 -> 做有界数据处理 -> 做受监督的实时模块 -> 做性能与运维”的顺序前进。每一步只增加一种主要难度，且必须能在没有生产密钥和大规模数据的环境中验证。

每个阶段默认只允许一个主要 PR。发现额外问题时先开 Issue，不在当前 PR 顺手重构。

## 3. 产品方向保持不变

原 Phase 4+ 计划中的产品方向继续有效，但不是 Developer B 的前端任务：

- 中央地图或数字地球保持 55%–65% 主视区，继续采用 calm、map-first、dark maritime 的界面方向。
- 3D 与 2D 视图必须使用真实 WGS 84 数据；位置、单位、覆盖范围和不确定性不得被视觉效果改变。
- 来源状态只使用 `LIVE`、`CACHED`、`DELAYED` 和 `OFFLINE`。
- `NO COVERAGE`、`MODEL DATA`、`DERIVED` 和 `TEST DATA` 是独立内容或覆盖标签，不得混入来源状态。
- 空结果、无覆盖和数据不可用必须分开；不得用 0、随机值或无关来源填充。
- 异常只表示需要复核的指标，不表示意图、违法、碰撞或紧急事件。
- 航空能力只作为未来版本预留，不进入当前海事模块，也不显示虚构航班或 KPI。

Developer A 负责船舶体验、地图图层、搜索、详情、follow、状态呈现、历史播放、风险证据界面、高级可视化和最终集成。Developer B 通过稳定、可追溯、有界的后端交付支持这些界面。

## 4. Developer B 分阶段路线

| 阶段 | 状态 | 难度 | 主要学习目标 | 推荐分支 |
| --- | --- | --- | --- | --- |
| B1 系统健康与来源状态加固 | 已完成 | 入门到中等 | FastAPI 分层、Redis、来源新鲜度、失败测试 | `api/phase-2-real-data-gate` |
| B2 现有 provider 契约回归测试 | 已完成并合并（PR `#36`） | 入门 | pytest、fixture、边界值、外部数据失败语义 | `test/provider-contract-regression` |
| B3 ingestion 运行诊断 | 下一阶段，可开始 | 入门到中等 | service/repository 边界、CLI、结构化结果 | `data/ingestion-run-diagnostics` |
| B4 有界历史导入性能基线 | B3 后 | 中等 | 流式处理、资源测量、性能回归 | `history/bounded-import-benchmark` |
| B5 Live AIS 离线规范化 | 被门禁阻塞 | 中等 | provider adapter、字段映射、时间与单位 | `ais/offline-position-normalizer` |
| B6 Live AIS 连接监督与背压 | B5 验收后 | 中等到进阶 | async、重连、队列上限、故障恢复 | `ais/bounded-worker-supervision` |
| B7 历史聚合后端切片 | Phase 5 授权后 | 中等 | 有界查询、聚合口径、可复现性 | `history/bounded-traffic-summary` |
| B8 后端发布与运维验收 | 发布候选期 | 中等 | smoke、故障演练、runbook、回滚证据 | `infra/backend-release-smoke` |

### B1 系统健康与来源状态加固

**状态：已完成并验收。**

Developer B 已通过 Issue `#16` 和 PR `#17` 完成第一阶段，主要提交为 `1b14ae8`，合并提交为 `7e0f96a`。交付包括 Redis 连通性、provider freshness、来源状态、最近 ingestion run、service/repository 分层以及后端测试。验收证据位于 `docs/27-phase-2-system-health-hardening-verification.md`。

合并后的 Bugbot 审查发现 `/system/status` 会读取完整历史。Developer A 通过 Issue `#32`、PR `#33` 和提交 `12d7b1b` 补充了有界摘要查询。这个后续修复不撤销 B1 的完成状态，但形成一条学习结论：API 返回结果有界并不等于数据库读取有界，后续阶段必须同时检查 SQL 数量和读取规模。

**B1 验收结论：** 已合并、CI 已通过、后续性能问题已修复，可以进入 B2；不需要组员重做。

### B2 现有 provider 契约回归测试

**状态：已完成并验收。** PR `#36` 已合并到 `main`，合并提交为 `8e7b9f4`。

**目标：** 先通过测试理解端口、地震、海洋预报和历史 AIS 的现有 provider 行为，不接入新来源、不改公共 API。

**建议工作：**

- 为已有 parser/provider 补充 4–8 个高价值回归测试，优先覆盖缺字段、非法时间、越界坐标、未知 schema 字段、上游不可用和空结果。
- fixture 只能放在 `apps/api/tests` 下，明确标记 `TEST DATA`，且测试应证明它不能进入生产配置。
- 网络测试默认 mock 或使用已有已批准样本，不调用真实 provider，不记录原始受限数据。
- 若测试暴露真实缺陷，可以在同一模块做最小修复；超过一个模块时拆出后续 Issue。

**允许路径：**

- `apps/api/tests/test_port_parsers.py`
- `apps/api/tests/test_port_providers.py`
- `apps/api/tests/test_earthquake_feed.py`
- `apps/api/tests/test_marine_forecast.py`
- `apps/api/tests/test_historical_ais.py`
- `apps/api/tests/fixtures/`，仅在确有需要时新建
- `docs/b-deliveries/B2-provider-contract-regression.md`

**禁止路径：** `apps/web`、公共 Live AIS contract、Alembic、根配置、README 和生产 provider 配置。不得新增依赖。

**交付物与验收：** 一个测试 PR、测试矩阵、失败前后说明、聚焦测试命令、完整后端测试结果、Ruff、mypy、`git diff --check` 和 secret scan。测试必须至少包含一个正常、一个边界和一个失败案例。

**与 A 并行：** A 可继续 `apps/web`、GIS、UI 或独立文档工作；A 同期避免修改上述五个测试文件。B2 不需要等待前端。

**B2 验收结论：** 五类现有 provider 的正常、边界和失败语义均获得新增回归覆盖，CI 已通过；下一步进入 B3，不需要重做或扩大 B2。

### B3 ingestion 运行诊断

**目标：** 为现有 ingestion 增加只读、可重复的运行摘要，让组员学习 service/repository/CLI 分层，而不承担调度器或数据库迁移。

**建议工作：**

- 从现有 provenance 和 ingestion run 记录生成有界摘要：run id、来源、开始/结束时间、成功/失败状态、读取/接受/拒绝数量和失败类别。
- 在 service 层计算展示字段，在 repository 层完成有界查询，在 CLI 层只负责参数与输出。
- 没有数据时返回明确空结果；数据库不可用时返回错误，不生成零填充记录。
- 所有时间保持 UTC；输出保留来源与 schema/data version。

**允许路径：** `apps/api/src/oceanscope_api/provenance/`、对应的 `apps/api/tests/test_ingestion_manifest.py` 和 `test_provenance_service.py`、`docs/b-deliveries/B3-ingestion-run-diagnostics.md`。

**禁止路径：** API 公共合同、前端、provider 网络代码、Alembic、根配置和 GitHub workflow。若发现必须迁移，B 只写 schema proposal，由 A 创建或最终复核迁移。

**交付物与验收：** 一个只读诊断命令或 service 方法、类型完整的结果、正反例测试、固定查询上限证据和使用文档。不得让诊断查询随历史总量线性返回全部记录。

**与 A 并行：** A 可开发 Web/GIS 和接口消费层；A 在该 PR 合并前不修改 `provenance` 模块。若 A 需要新字段，先单独提交 contract PR 并合并，再开始 B3。

### B4 有界历史导入性能基线

**目标：** 只测量并加固现有 bounded MarineCadastre importer，不提前实现 Phase 5 播放、聚合或全球历史覆盖。

**建议工作：**

- 建立小、中两档可重复基线，记录解析行数、拒绝行数、耗时和峰值内存。
- 性能输入使用已批准的小型样本或隔离的 `SYNTHETIC BENCHMARK`；合成数据不得进入生产存储。
- 验证空间和时间边界、幂等性、失败恢复，以及大输入不会被一次性全部读入内存。
- 只有测量证明需要时才做局部优化；不得进行仓库级重构。

**允许路径：** `apps/api/src/oceanscope_api/history/`、`apps/api/tests/test_historical_ais.py`、独立性能脚本或测试目录、`docs/b-deliveries/B4-bounded-history-benchmark.md`。

**禁止路径：** 新数据库 schema、Phase 5 UI、扩大 MarineCadastre 到美国水域之外、提交原始大文件或数据库缓存。

**交付物与验收：** 可复现命令、环境说明、输入标签、基线表、约束检查和测试。若结果仅是测量，也可以完成本阶段；不为了显示优化而制造虚假提升。

**与 A 并行：** A 可继续地图与前端；双方不得同时修改 `history` 合同。需要合同变化时先暂停，以独立 contract PR 串行处理。

### B5 Live AIS 离线规范化

**状态：被门禁阻塞。** 只有 Developer A 完成 Issue `#37` 的 Pelyr 自助凭据 smoke、记录有效 limits/来源目录/署名/覆盖，并明确 Phase 4 授权后才能开始。当前不得提前创建生产 provider 或真实连接。

**目标：** 在不接网络、不处理密钥的前提下，将已核验的 Pelyr `/v1` position frame 映射到 provider-neutral v1 contract，并保留每条记录的 licence id、来源和署名。

**建议工作：**

- 先提交字段映射表，列出 provider 字段、规范字段、类型、单位、可空性和拒绝规则。
- 使用经过审查的最小化 `TEST DATA` fixture 实现离线 parser/normalizer。
- 正确处理 UTC、经纬度、节、角度、AIS sentinel 和未知字段；不可推断缺失身份。
- 原始 provider dictionary 不得穿过 adapter 边界进入 route 或前端。

**允许路径：** 经 A 批准的新 `apps/api/src/oceanscope_api/live_ais/` adapter/normalizer 文件、对应后端测试、`docs/b-deliveries/B5-live-ais-normalizer.md`。

**禁止路径：** 真实网络连接、密钥、FastAPI route、WebSocket、Redis/PostGIS、Alembic、`apps/web` 和生产 fixture。

**交付物与验收：** 字段与许可证映射、离线 normalizer、合法/非法/null/未知字段/未知 licence id 测试和来源条款引用。共享合同如需改变，必须由 A 先审查并单独合并。

**与 A 并行：** 合同冻结后，A 可在 `apps/web` 使用现有共享 `TEST DATA` 开发状态和地图体验；B 只改 adapter 与后端测试。两人不同时修改 contract fixture。

### B6 Live AIS 连接监督与背压

**状态：B5 验收且 Phase 4 正式授权后开始。** 这是 Developer B 路线中第一个需要结对设计复核的阶段。

**目标：** 在芬兰湾固定边界（`23.50, 59.50, 26.50, 60.50`）、Pelyr `/v1` position-only、单后端连接和原始消息零持久化约束下实现有界 worker 行为。

**建议拆成两个小 PR：**

1. `ais/bounded-worker-supervision`：连接、`welcome` 来源目录、heartbeat/loss、超时、指数退避、停止、指标和 gap 状态，不包含公共 WebSocket。
2. `ais/bounded-fanout-backpressure`：固定队列、同 MMSI 合并、动态署名、慢客户端策略、sequence/epoch 和负载测试，只允许同源产品传输，不包含前端或数据导出。

**允许路径：** 获批后的 `live_ais` worker/provider、后端 gateway/service、对应 tests、运行手册和 B 交付文档。

**禁止路径：** `apps/web`、扩大订阅边界、原始消息持久化、未批准迁移、在日志输出密钥或原始完整 payload。

**交付物与验收：** 断线、重连、突发、慢消费者、队列满、陈旧数据和不可用测试；每个队列、批次和超时必须有固定上限。真实 smoke 仅在受保护环境运行，不把密钥注入 fork PR。

**与 A 并行：** A 负责船舶图层、详情、follow 和连接状态 UI。B 的 backend contract 合并前，A 只用冻结 fixture；backend ready 后由 A 负责集成验收。

### B7 历史聚合后端切片

**状态：等待 Phase 5 授权。**

**目标：** 在一个批准的美国水域、时间窗口和已知数据版本上，实现一个小型交通摘要，不直接承担完整历史分析平台。

范围只包含一个问题，例如“按固定时间桶统计有效位置记录数并公开分母与缺失率”。所有查询必须具有空间、时间和数量边界，结果标明来源、采样、单位和 `DERIVED`。

**允许路径：** `history` service/repository、后端测试、性能记录和 B 交付文档。**禁止路径：** 前端、全球覆盖声明、风险判断、未经批准导出和并行迁移。

**验收：** 已知小数据集可复现；边界、空结果、无覆盖和不可用分开；聚合结果可回代；查询计划和资源预算有记录。

### B8 后端发布与运维验收

**状态：等待发布候选。**

**目标：** 将已实现的后端能力整理成任何一位开发者都能重复执行的 smoke 与故障恢复步骤。

Developer B 负责 PostGIS/Redis/API 启动检查、只读健康验证、后端测试矩阵、受控故障场景和 runbook 草稿。Developer A 负责安全范围、最终发布清单、用户界面、截图、版本和回滚批准。

不得在 smoke 中破坏真实环境；迁移回环只能使用明确命名的 disposable database。验收需要记录命令、环境、预期结果、实际结果和剩余限制。

## 5. Developer A 主线与同步关系

Developer A 的主线沿用原 Phase 4+ 计划，并承担约 65%–70% 的工作量：

| 产品阶段 | Developer A 主线 | 对 Developer B 的已冻结输入 |
| --- | --- | --- |
| 当前维护 | 产品与架构决策、Phase 3 UI/GIS 维护、合同审查 | B2 测试范围和现有 provider 行为 |
| Phase 4 | 有界船舶地图、详情、follow、来源/署名、连接/覆盖/空状态、集成验收 | provider-neutral v1 contract、固定芬兰湾边界、Pelyr 动态来源目录 |
| Phase 5 | 时间轴、播放、筛选、密度和图表联动 | 有界历史查询合同、数据版本和聚合口径 |
| Phase 6 | 规则详情、证据时间线、地图高亮和人工复核体验 | 确定性规则输出和可追溯证据合同 |
| Phase 7 | 3D/2D 高级可视化、LOD、比较模式和 fallback | 聚合 payload、tiles、缓存状态和性能数据 |
| Phase 8–10 | 产品集成、智能证据界面、可访问性、安全、演示和发布 | 后端 smoke、运行手册、测试与性能证据 |

### 可直接并行的组合

| Developer A | Developer B | 冲突风险 |
| --- | --- | --- |
| `apps/web` UI/GIS | B2 provider tests | 低，目录完全分开 |
| `apps/web` UI/GIS | B3 `provenance` 诊断 | 低，不改公共合同即可 |
| 地图渲染性能 | B4 `history` importer 基线 | 低，合同保持不变 |
| Phase 4 状态 UI 和 fixture 消费 | B5 adapter/normalizer | 中，必须先冻结 contract |
| 船舶图层与详情 | B6 worker/gateway | 中，按 contract 串行集成 |
| Phase 5 历史 UI | B7 聚合 service/repository | 中，查询合同先合并 |
| 发布页面与前端 E2E | B8 backend smoke/runbook | 低，最后由 A 统一验收 |

### 必须串行的事项

- `apps/api/src/oceanscope_api/api/contracts/` 与共享 fixture：A 冻结并先合并，B 再实现。
- `apps/api/alembic/versions/`：任何时刻只能有一个迁移作者；B 提 proposal，A 创建或最终复核。
- `README.md`、`AGENTS.md`、根配置、lockfile、Docker Compose、GitHub workflow：单独小 PR，不能夹在功能 PR 中顺手修改。
- 阶段状态、公共能力声明和发布文档：由 A 在验收证据齐全后更新。
- 同一 service/repository 文件：先在 Issue 中声明占用者，另一人等待合并后再开始。

## 6. 分支、路径与 Pull Request 规则

### 分支规则

- 不建立长期 `developer-a` 或 `developer-b` 分支，也不直接 push `main`。
- 每个阶段从最新 `main` 创建短生命周期功能分支。
- A 优先使用 `ui/*`、`gis/*`、`contract/*`、`docs/*` 和 `fix/*`。
- B 优先使用 `test/*`、`data/*`、`history/*`、`ais/*` 和 `infra/*`。
- 一个分支只完成一个可验收结果；B6 明确拆成两个分支。

### 开始任务前

1. 在 Issue 中写清目标、非目标、允许路径、禁止路径、依赖和验收命令。
2. 运行 `git status`，确认没有把其他人的未提交修改带入分支。
3. 检查 `main` 是否已经包含依赖的 contract 或 migration。
4. 在项目板上把任务设为 `In progress`；每人最多一个主要阶段和一个小维护项。
5. 若允许路径与对方正在修改的文件重合，先暂停并重新拆分，不通过抢先提交解决。

### PR 交付模板

每个 Developer B PR 至少写明：

- 关联 Issue、阶段编号和学习目标。
- 修改路径与明确未修改的边界。
- 正常、边界、失败场景及相应测试。
- 数据来源、fixture 标签、freshness/coverage 影响。
- 查询、内存或队列上限；不适用时说明原因。
- 执行过的格式、lint、type、test、`git diff --check` 和 secret scan。
- 剩余限制、回滚方式和是否需要 A 的合同/迁移/集成动作。

### 冲突处理

提交评审前先同步最新 `main`。如果冲突只发生在自己的阶段文件，B 可以解决并重新运行测试；如果冲突发生在合同、迁移、README、根配置或 A 正在开发的模块，B 不自行选择一方内容，应暂停并由 A 确认合并顺序。

## 7. 阶段验收门槛

| 验收域 | 必须证明 |
| --- | --- |
| 范围 | 只修改 Issue 中允许的路径，没有顺手重构和后续阶段实现 |
| 真实性 | 无生产假数据、随机 fallback、零填充或无关 provider 替代 |
| 来源 | 外部数据保留来源、时间、版本、coverage、cache state 和质量标记 |
| 架构 | route/CLI 薄，业务逻辑在 service，数据访问在 repository/provider |
| 测试 | 重要逻辑具有正常、边界和失败测试；fixtures 明确为 `TEST DATA` |
| 性能 | 查询、批次、内存、队列和时间窗口有界，并按风险提供测量 |
| 安全 | 无密钥、原始受限数据、数据库 volume、本地 cache 或完整敏感 payload |
| 文档 | 阶段状态、命令、证据和剩余限制与实际实现一致 |
| 协作 | 未修改对方所有权模块；共享文件已经单独评审 |

最低本地检查按改动范围选择，但交付报告必须记录结果：

```text
Ruff format/check
strict mypy
focused pytest
full backend pytest when backend behavior changes
frontend lint/type/test/build when shared contract affects frontend
git diff --check
configured secret scan
```

CI 失败时先判断是否由当前 PR 引起。不得删除测试、放宽类型或跳过检查来获得绿色结果。

## 8. 当前行动顺序

1. Developer B 的 B2 已通过 PR `#36` 合并；下一步执行 B3 ingestion 运行诊断，不重做 B2。
2. Developer A 完成 Issue `#37` 的 Pelyr 自助凭据与芬兰湾 smoke，只记录无敏感元数据，不提交 Key 或原始 AIS payload。
3. B3 合并后再进入 B4，保持一次只学习一个主要系统边界。
4. B5 和 B6 继续阻塞，直到 A 明确记录 Phase 4 授权、有效来源目录/署名/覆盖证据和安全凭据路径。
5. 每个阶段由 A 根据 PR 证据验收；只有验收完成后才在本计划或路线图中更新状态。

## 9. 停止条件与升级机制

遇到以下任一情况，Developer B 应停止实现并在 Issue 中请求 A 决策：

- 需要新依赖、公共合同、数据库迁移或根配置变化。
- 官方 provider 文档、条款、字段或许可无法确认。
- 测试需要真实密钥、生产网络或受限原始数据。
- 任务范围扩展到 `apps/web`、GIS、架构或发布声明。
- 性能问题只有通过大规模重构或改变数据语义才能解决。
- 发现现有数据可能被错误标记为 `LIVE`、0、`NO COVERAGE` 或 `DATA UNAVAILABLE`。
- 发现 secret、个人信息、受限数据或不可恢复的破坏性操作风险。

停止并记录问题不等于阶段失败。对初学者来说，能够识别所有权边界、数据不确定性和需要升级的风险，本身就是本计划要求的工程能力。

## 10. 参考与维护

本计划应与以下文件一起使用：

- `README.md`：当前实现状态和阶段授权的最高项目级来源。
- `AGENTS.md`：长期工程、数据、架构和协作约束。
- `docs/06-development-roadmap.md`：Phase 0–10 的正式范围与门禁。
- `docs/09-github-strategy.md`：分支、PR、所有权和 CI 规则。
- `docs/12-definition-of-done.md`：功能、数据、后端、前端和阶段完成标准。
- `docs/27-phase-2-system-health-hardening-verification.md`：Developer B 第一阶段验收证据。
- `docs/31-phase-4-contract-kickoff.md`：Live AIS v1 合同与实现入口门禁。
- `docs/34-phase-4-bounded-operating-policy.md`：Phase 4 已冻结但尚未授权的运行边界。
- `docs/36-pelyr-live-ais-provider-verification.md`：Pelyr 选型、混合许可证、限制和 Issue `#37` 凭据门禁。
- `docs/OceanScope_Project_Plan_Phase4Plus.md`：本计划继承的产品与视觉方向。

若这些文件发生冲突，以 `README.md` 的当前状态、`AGENTS.md` 的永久规则、官方来源证据和最新已合并验收记录为准。本文的分工比例和学习阶段可以在 A 审批后调整，但不得通过调整任务名称掩盖所有权迁移或未完成能力。
