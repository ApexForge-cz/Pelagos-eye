# OceanScope 双人每日 Git 与 GitHub 工作流程

> 版本 1.0 | 2026-09-20 | 适用于 Developer A 和 Developer B

本文规定两位开发者每天打开项目后，从同步代码、进入自己的功能分支，到开发、检查、提交、推送、Pull Request 和合并后清理的完整流程。

本文中的“自己的分支”是当前 Issue 对应的短期功能分支，例如 `test/provider-contract-regression`，不是长期存在的个人分支。任何人都不得直接向 `main` push。

## 1. 每日工作原则

1. 一个 Issue 对应一个主要分支和一个聚焦 PR。
2. 每天开始先检查本地改动，再执行同步；不要在不清楚工作区状态时运行 `pull` 或切换分支。
3. 新任务必须从最新的 `main` 创建分支；继续已有任务时，先拉取自己的远端分支，再合入最新的 `origin/main`。
4. 只修改 Issue 中列出的允许路径，不顺手格式化、重命名或重构无关文件。
5. 不修改另一位开发者正在负责的文件。共享合同、迁移和根配置必须串行处理。
6. 每次提交前检查 diff、运行相关测试，并确认没有密钥、缓存、原始受限数据或构建产物。
7. 所有改动通过 Pull Request 进入 `main`；只有 required checks 和评审通过后才能合并。

## 2. 分支命名

根据任务类型选择短期分支前缀：

| 类型 | 分支格式 | 示例 |
| --- | --- | --- |
| 前端/UI | `ui/<task>` | `ui/vessel-status-panel` |
| GIS/地图 | `gis/<task>` | `gis/live-vessel-layer` |
| API | `api/<task>` | `api/source-health-summary` |
| 数据/采集 | `data/<task>` | `data/ingestion-run-diagnostics` |
| AIS | `ais/<task>` | `ais/offline-position-normalizer` |
| 历史分析 | `history/<task>` | `history/bounded-import-benchmark` |
| 基础设施 | `infra/<task>` | `infra/backend-release-smoke` |
| 测试 | `test/<task>` | `test/provider-contract-regression` |
| 合同 | `contract/<task>` | `contract/live-ais-v1` |
| 文档 | `docs/<task>` | `docs/daily-git-workflow` |
| Bug 修复 | `fix/<task>` | `fix/status-query-bound` |

禁止使用长期 `developer-a`、`developer-b`、`my-branch` 或 `work` 分支。

## 3. 每天打开项目后的第一步

打开 PowerShell，进入项目目录：

```powershell
cd C:\Users\Administrator\Desktop\oceanscope-maritime-intelligence
```

先查看当前分支和未提交改动：

```powershell
git status --short --branch
git branch --show-current
```

根据结果处理：

- 工作区干净：可以继续同步。
- 有自己昨天未提交的改动：先确认仍在正确的功能分支，然后继续该任务或先提交一个完整的小步骤。
- 有来源不明或属于另一人的改动：不要删除、覆盖、stash 或切换分支，先与对方确认。
- 当前在 `main` 且有未提交改动：不要直接提交，也不要立刻 `pull`；先确认这些改动应属于哪个 Issue 和功能分支。

永远不要为“快速恢复干净”运行：

```text
git reset --hard
git clean -fd
git checkout -- <file>
```

这些命令可能永久删除尚未保存的工作。需要恢复文件时先确认目标和可恢复来源。

## 4. 新任务第一天的流程

只有当工作区干净，或者现有未提交改动已经得到妥善处理后，才能开始以下步骤。

### 4.1 获取远端最新状态

```powershell
git fetch --prune origin
```

### 4.2 更新本地 main

```powershell
git switch main
git pull --ff-only origin main
```

`--ff-only` 可以避免在本地 `main` 上意外产生合并提交。如果命令失败，不要改用强制命令，应先检查本地 `main` 是否存在不该有的提交或修改。

### 4.3 创建 Issue 指定的功能分支

```powershell
git switch -c <branch-name>
```

例如 Developer B 的 B2 Issue 必须使用：

```powershell
git switch -c test/provider-contract-regression
```

确认分支正确：

```powershell
git status --short --branch
git branch --show-current
```

### 4.4 首次推送分支

完成第一个可说明的提交后，将分支推送到 GitHub 并建立跟踪关系：

```powershell
git push -u origin <branch-name>
```

B2 示例：

```powershell
git push -u origin test/provider-contract-regression
```

不得执行 `git push origin main`。

## 5. 继续已有任务的每日流程

如果功能分支已经存在于本地和 GitHub，第二天不要重新创建分支。

### 5.1 检查工作区

```powershell
git status --short --branch
```

执行后续 `pull` 或 `merge` 前，工作区必须干净。如果存在自己尚未完成的改动，先不要同步；继续完成一个可独立说明的小步骤并提交，或者联系 Developer A 确认处理方式。不得为了同步而删除或隐藏不清楚的改动。

### 5.2 获取远端更新

```powershell
git fetch --prune origin
```

### 5.3 切换到自己的任务分支

```powershell
git switch <branch-name>
```

B2 示例：

```powershell
git switch test/provider-contract-regression
```

### 5.4 拉取自己的远端分支

```powershell
git pull --ff-only origin <branch-name>
```

B2 示例：

```powershell
git pull --ff-only origin test/provider-contract-regression
```

### 5.5 合入最新 main

```powershell
git merge --no-edit origin/main
```

选择 merge 而不是对已经共享的分支随意 rebase，可以避免初学阶段误用 force push。项目最终使用 squash merge 时，功能分支中的同步提交不会污染 `main` 的最终历史。

如果出现冲突：

- 只涉及自己负责的测试或模块：仔细解决冲突，重新运行相关检查，再提交合并结果。
- 涉及合同、迁移、README、AGENTS、根配置或另一人的模块：停止解决，不要随意选择 `ours` 或 `theirs`，通知 Developer A 决定合并顺序。
- 不要使用 `git push --force`。只有项目负责人明确要求并解释原因时，才可考虑 `--force-with-lease`。

## 6. 开始编码前的确认

打开 Issue 和相关计划文档，确认以下内容：

- 当前阶段已授权。
- Issue 的目标、非目标和验收标准明确。
- 分支名与 Issue 一致。
- 允许路径和禁止路径明确。
- 没有另一位开发者正在修改相同文件。
- 依赖的 contract 或 migration 已经合并进 `main`。
- 外部数据任务已经确认官方文档、条款、coverage 和凭据边界。

运行：

```powershell
git status --short --branch
git log -5 --oneline
```

确认自己位于正确分支，并且该分支基于预期的最新提交。

## 7. 开发过程中的规则

### 7.1 保持改动聚焦

- 一次只完成一个可验证的小结果。
- 不进行仓库级格式化。
- 不把发现的无关问题顺手修进当前 PR；为它创建新 Issue。
- FastAPI route 保持薄，业务逻辑放在 service，数据库访问放在 repository/provider。
- 前端组件保持模块化，不绕过公共 typed contract。

### 7.2 保护数据与密钥

- 不提交 `.env`、API key、token、password 或真实凭据。
- 不提交数据库 volume、本地 cache、原始受限数据或大体积下载文件。
- 测试 fixture 只能位于测试路径，明确标记 `TEST DATA`。
- 性能合成数据明确标记 `SYNTHETIC BENCHMARK`，并与生产存储隔离。
- Provider 失败只能返回有效且标龄的缓存或 `DATA UNAVAILABLE`，不能生成假值或用 0 填充。

### 7.3 定期检查当前改动

```powershell
git status --short
git diff
```

如果出现计划外文件，先查明原因，不要等到提交前才处理。

## 8. 每天结束前的质量检查

检查范围应与改动风险匹配。至少运行聚焦检查；后端行为或共享合同变化时运行完整检查。

### 8.1 仓库统一检查

```powershell
python scripts/check.py
git diff --check
```

### 8.2 后端聚焦检查示例

在仓库根目录运行：

```powershell
uv run --directory apps/api ruff format --check .
uv run --directory apps/api ruff check .
uv run --directory apps/api mypy src tests
uv run --directory apps/api pytest <related-test-files>
```

B2 示例：

```powershell
uv run --directory apps/api pytest tests/test_port_parsers.py tests/test_port_providers.py tests/test_earthquake_feed.py tests/test_marine_forecast.py tests/test_historical_ais.py
```

### 8.3 前端聚焦检查示例

```powershell
npm run web:format:check
npm run web:lint
npm run web:test
npm run web:build
```

如果具体脚本名称变化，以 `package.json`、`apps/api/pyproject.toml` 和 CI 为准。不得通过删除测试、降低类型要求或跳过检查来得到绿色结果。

## 9. 暂存与提交

### 9.1 提交前查看差异

```powershell
git status --short
git diff
git diff --check
```

### 9.2 精确暂存文件

优先明确列出本次提交的文件：

```powershell
git add <file-1> <file-2>
```

不要习惯性使用 `git add .`，它可能把 `.env`、缓存、临时文件或另一项任务的改动一起加入提交。

查看即将提交的内容：

```powershell
git diff --cached
git status --short
```

### 9.3 创建提交

提交信息应描述结果，而不是“update”或“work”。推荐格式：

```text
<type>(<area>): <outcome>
```

示例：

```powershell
git commit -m "test(api): add provider contract regression coverage"
git commit -m "fix(api): bound source status summary queries"
git commit -m "docs: add daily GitHub collaboration workflow"
```

常用类型包括 `feat`、`fix`、`test`、`docs`、`refactor`、`perf` 和 `chore`。

## 10. 推送到 GitHub

首次推送使用：

```powershell
git push -u origin <branch-name>
```

之后继续推送同一分支：

```powershell
git push
```

推送前再次确认：

```powershell
git branch --show-current
git status --short --branch
```

必须确认当前不是 `main`。不得使用普通 `--force` 绕过远端历史。

## 11. 创建 Pull Request

在 GitHub 上从功能分支向 `main` 创建 PR。一个 PR 只对应一个清晰结果，并关联 Issue。

PR 至少写明：

- 实现了什么用户或工程结果。
- 关联的 Issue、阶段和分支。
- 修改和明确未修改的范围。
- 执行过的命令及结果。
- 正常、边界和失败场景。
- 数据来源、freshness、coverage 和 fixture 影响。
- 安全、性能、迁移和回滚影响。
- 剩余限制。

UI/GIS 改动提供截图或录屏；数据和后端改动提供测试、查询或运行摘要。复选框不是证据，必须记录实际结果。

尚未完成但希望尽早讨论时，可以创建 Draft PR。Draft PR 不得标记为可合并或完成。

## 12. 处理 CI、Bugbot 和人工评审

### 12.1 CI 失败

1. 打开失败 job，找到第一条与本 PR 相关的错误。
2. 在本地复现对应命令。
3. 修复根因并补充测试。
4. 提交到同一功能分支并 `git push`。
5. 不删除测试、不降低标准、不把失败 job 改成可选。

### 12.2 Bugbot 或评审意见

- 对每条意见判断是否正确、是否属于当前 Issue。
- 属于当前范围且结论明确：在同一分支修复、运行测试并回复证据。
- 属于独立问题：创建后续 Issue，并在 PR 中说明为什么不扩大当前范围。
- 涉及架构、合同、迁移或数据语义：由 Developer A 最终决定。
- 不只回复“已修复”，应写明修改位置和验证结果。

## 13. 合并规则

只有满足以下条件才能合并：

- Issue 验收标准全部满足。
- required checks 全部通过。
- 没有未解决的 review thread。
- 数据、测试、文档和实际实现一致。
- 没有秘密、受限数据或计划外文件。
- Developer A 已完成需要的所有权、合同、迁移和集成复核。

默认使用 squash merge，使一个聚焦 PR 在 `main` 中形成一个清晰提交。不得为了赶进度绕过分支保护或直接 push `main`。

## 14. PR 合并后的清理

确认 GitHub PR 已经合并后执行：

```powershell
git fetch --prune origin
git switch main
git pull --ff-only origin main
git branch -d <branch-name>
```

只有确认分支已经合并后，才能删除本地分支。若 GitHub 没有自动删除远端分支，可以执行：

```powershell
git push origin --delete <branch-name>
```

然后：

- 在 Issue 中确认交付物和验证证据。
- 将项目板状态从 `Review` 更新为 `Done`。
- 检查 `README.md` 或路线图是否真的需要由 Developer A 更新状态。
- 从最新 `main` 创建下一个 Issue 的新分支，不复用已经合并的旧分支。

## 15. 两位开发者的冲突隔离

### Developer A 主要路径

```text
apps/web
UI、GIS、地图和可视化
核心 API contracts
架构、集成、README、演示和发布
```

### Developer B 主要路径

```text
providers
ingestion/workers
data pipelines
backend data operations
infrastructure
provider/backend tests
performance pipelines
```

### 共享且必须串行的路径

```text
apps/api/src/oceanscope_api/api/contracts
apps/api/alembic/versions
README.md
AGENTS.md
根配置和 lockfiles
Docker Compose
.github
```

同一时间只有一人修改共享合同或 migration。Developer B 可以提交 schema proposal，但最终 Alembic migration 由 Developer A 创建或复核。

## 16. Developer B 当前 B2 的每日命令

### B2 第一天

```powershell
cd C:\Users\Administrator\Desktop\oceanscope-maritime-intelligence
git status --short --branch
git fetch --prune origin
git switch main
git pull --ff-only origin main
git switch -c test/provider-contract-regression
git status --short --branch
```

完成一个可验证的小步骤后：

```powershell
git diff --check
git add <B2-files>
git diff --cached
git commit -m "test(api): add provider contract regression coverage"
git push -u origin test/provider-contract-regression
```

### B2 后续每天

```powershell
cd C:\Users\Administrator\Desktop\oceanscope-maritime-intelligence
git status --short --branch
git fetch --prune origin
git switch test/provider-contract-regression
git pull --ff-only origin test/provider-contract-regression
git merge --no-edit origin/main
git status --short --branch
```

每天结束：

```powershell
uv run --directory apps/api ruff format --check .
uv run --directory apps/api ruff check .
uv run --directory apps/api mypy src tests
uv run --directory apps/api pytest tests/test_port_parsers.py tests/test_port_providers.py tests/test_earthquake_feed.py tests/test_marine_forecast.py tests/test_historical_ais.py
git diff --check
git status --short
```

只暂存 B2 允许路径，检查 staged diff，提交后执行 `git push`。

## 17. 每日快速检查表

### 开始工作

- [ ] 已进入正确仓库。
- [ ] 已运行 `git status --short --branch`。
- [ ] 没有来源不明的未提交改动。
- [ ] 已运行 `git fetch --prune origin`。
- [ ] 新任务从最新 `main` 创建分支；已有任务已拉取自己的分支并合入 `origin/main`。
- [ ] 当前分支名与 Issue 一致。
- [ ] 已确认允许路径、禁止路径和依赖。

### 结束工作

- [ ] 已查看 `git diff` 和 `git status`。
- [ ] 已运行相关 format、lint、type、test 和 build。
- [ ] 已运行 `git diff --check`。
- [ ] 没有密钥、受限数据、缓存、volume 或计划外文件。
- [ ] 使用明确文件路径完成暂存。
- [ ] 已检查 `git diff --cached`。
- [ ] 提交信息描述了实际结果。
- [ ] 已推送到自己的功能分支，而不是 `main`。
- [ ] PR 或 Draft PR 状态与实际完成度一致。

## 18. 遇到不确定情况时

出现以下情况时停止操作并联系 Developer A：

- 不知道未提交改动来自谁。
- `pull`、`merge` 或切换分支发生冲突。
- 需要修改公共合同、migration、README、AGENTS 或根配置。
- 需要新依赖、真实 API key、生产网络或受限数据。
- CI 与本地结果不一致且无法解释。
- 认为必须使用 `reset --hard`、`clean -fd`、普通 force push 或跳过检查。
- Issue 范围与实际需要修改的模块不一致。

暂停并确认不会影响任务完成度。保护他人工作、数据真实性和可恢复性优先于快速提交。
