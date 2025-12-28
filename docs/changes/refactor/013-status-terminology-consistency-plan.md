# Status Terminology Consistency Refactor Plan

> 状态: Draft
> 负责人: WhaleFall FE
> 创建: 2025-12-27
> 更新: 2025-12-28
> 范围: `app/templates/**`, `app/static/js/**`, `app/constants/**`, `app/models/**`, `app/services/**`, `docs/standards/terminology.md`, `docs/standards/ui/**`, `scripts/ci/**`, `.github/**`
> 关联: `docs/reports/2025-12-25_frontend-ui-ux-audit-report.md`(P2-06), `docs/standards/terminology.md`

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** For the same "status meaning", UI uses one canonical wording across the product. Remove drift like "禁用/停用"、"运行中/进行中/执行中" that increases cognitive load and causes users to infer non-existent differences.

**Architecture:** Define a canonical terminology map for common status states (启用/停用、锁定/正常、已删除、运行态/终态、健康状态等), then migrate UI strings to it. Prevent regressions via a lightweight guard and a PR checklist item.

**Tech Stack:** Jinja templates, vanilla JS modules, ripgrep-based CI guards.

---

## 1. 动机与范围

### 1.1 动机

审计报告(P2-06)指出: UI 存在术语漂移, 同一语义状态在不同页面使用不同词, 例如:

- instance status: "禁用"(见 `app/static/js/modules/views/instances/list.js`)
- tag status: "停用标签"(见 `app/templates/tags/index.html`)

影响:

- 用户会推断"禁用"与"停用"是否代表不同机制(权限/软删/不可用), 增加认知负担与误解成本.
- 支持与排障成本增加: 复述问题与检索日志/文档时更难对齐关键词.

### 1.2 范围

In-scope:

- UI 可见文案中的状态词与动作词(按钮, badge, 表格列, 统计卡片, toast).
- 覆盖当前代码中已出现的常见状态语义:
  - 激活/可用类: `is_active` / active / inactive
  - 软删除类: `deleted_at` / deleted / recycle bin
  - 锁定类: `is_locked`
  - 运行态/终态类: pending / running / paused / completed / failed / cancelled
  - 调度器 job 状态与动作: scheduled / running / paused / stopped / error + pause/resume
  - 健康状态类: healthy / warning / unhealthy / maintenance
  - 任务结果类: success / error / warning / info（含变更日志/任务统计图表等）

Out-of-scope(本次不做):

- 技术语义的 "禁用按钮/disabled" 等描述(属于实现层术语, 不等同于资源状态).
- 建立完整 i18n 体系(仅先统一中文用词).
- 调整后端状态机/枚举值/接口字段(仅统一 UI 呈现与文案映射, 必要时补充注释与标准).

### 1.3 状态盘点(来自当前代码)

> 目标是先“全量列出并统一口径”，再分阶段迁移；本小节列出当前代码中已出现的状态语义与典型文案漂移点。

#### 0) Canonical 状态词表(v1，一览)

> 说明：该表用于**“同一语义 -> 同一中文展示”**。如需在不同页面表达更细分语义，请先在本 plan 内新增“语义域”，避免直接在 UI 手写同义词漂移。

| 语义域 | 原始值/字段 | Canonical 展示 | 备注 |
| --- | --- | --- | --- |
| 资源启用态 | `is_active=true` | 启用 | 适用于 Instance/Tag/Credential/User 等（表示“启用/停用”语义） |
| 资源启用态 | `is_active=false` | 停用 | 避免用“禁用”表达资源状态 |
| 子资源存在态 | `is_active=true` | 正常 | 适用于 InstanceAccount/InstanceDatabase 等（表示“仍存在/未删除”语义） |
| 子资源存在态 | `is_active=false` | 已删除 | 同上（与启用/停用不同语义） |
| 回收站/软删 | `deleted_at!=null` | 已删除 | 与启用/停用、锁定为不同维度 |
| 锁定态 | `is_locked=true` | 已锁定 | DB 锁定/不可登录（AccountPermission 等） |
| 锁定态 | `is_locked=false` | 正常 | 锁定维度的对照词 |
| 运行态(生命周期) | `pending` | 等待中 | 统一替换 `排队中/等待/等待中` 漂移词 |
| 运行态(生命周期) | `running` | 运行中 | 统一替换 `进行中/执行中` 漂移词 |
| 运行态(生命周期) | `paused` | 已暂停 | |
| 运行态(生命周期) | `completed` | 已完成 | |
| 运行态(生命周期) | `failed` | 失败 | |
| 运行态(生命周期) | `cancelled` | 已取消 | |
| Scheduler 作业态 | `scheduled` | 已调度 | 来自 `JobStatus` 或 scheduler state 映射 |
| Scheduler 作业态 | `stopped` | 已停止 | |
| Scheduler 作业态 | `running` | 运行中 | |
| Scheduler 作业态 | `paused` | 已暂停 | |
| 实例状态 | `active` | 正常 | `InstanceStatus`（与 `is_active` 不同维度，避免混用） |
| 实例状态 | `inactive` | 不可用 | 同上 |
| 实例状态 | `maintenance` | 维护中 | 同上 |
| 实例状态 | `error` | 异常 | 同上 |
| Task/变更结果 | `success` | 成功 | `TaskStatus`/变更日志等 |
| Task/变更结果 | `error` | 错误 | |
| Task/变更结果 | `warning` | 告警 | |
| Task/变更结果 | `info` | 信息 | |
| 健康状态 | `healthy` | 正常 | |
| 健康状态 | `warning` | 告警 | |
| 健康状态 | `unhealthy` / `error` | 异常 | |
| 健康状态 | `maintenance` | 维护中 | |
| 健康状态 | `unknown` | 未知 | |

> 展示对齐说明：状态词允许为 1/2/3 个字（例如 `失败/启用/运行中`），**不要用字符串补空格**解决对齐；应当用样式（如 `.status-pill` 的 `min-width`）保证表格列内视觉对齐。

#### A) 激活状态(`is_active`)

- 语义: 资源是否对外可用/可操作（非软删、非锁定、非健康检查）。
- 代码来源: `Instance.is_active` / `Tag.is_active` / `Credential.is_active` / `User.is_active` 等。
- 当前 UI 文案(已存在漂移):
  - 状态: `启用/停用`、`禁用`、`正常`、`在线`、`可用`
  - 统计/汇总: `活跃`、`禁用实例`、`停用标签`、`关注`、`待清理`
- Canonical(v1):
  - 状态词: **启用 / 停用**
  - 动作词(按钮/操作): **启用 / 停用**
  - 约束:
    - 避免用“禁用”表示资源状态(与 UI disabled 技术语义强冲突)
    - 避免用“正常”表示 `is_active=True`(“正常”保留给健康/异常或锁定/删除的兜底展示)
    - 避免用“在线/关注”表示 `is_active`（除非该页面确实表达的是“在线/离线/连接状态”等语义）

#### B) 软删除/回收站(`deleted_at`)

- 语义: 资源已被移入回收站(可恢复)或软删除(不可见但仍在 DB)。
- 代码来源: `Instance.deleted_at` / `InstanceAccount.deleted_at` / `InstanceDatabase.deleted_at` 等。
- 当前 UI 文案:
  - 状态: `已删除`（部分子资源列表使用 `在线/已删除` 作为对照）
  - 动作: `移入回收站`、`恢复`、`显示已删除`
- Canonical(v1):
  - 状态词: **已删除**
  - 动作词: **移入回收站 / 恢复**
  - 约束: “删除”仅用于不可恢复的最终删除动作；当是可恢复回收站语义时避免用“删除”作为按钮主文案

#### C) 锁定(`is_locked`)

- 语义: 账户被 DB 锁定/不可登录(与启用/停用、删除不同维度)。
- 代码来源: `AccountPermission.is_locked`。
- 当前 UI 文案(存在两套):
  - `锁定/正常`（列表徽章）
  - `已锁定/正常`（详情徽章）
- Canonical(v1):
  - 状态词: **已锁定 / 正常**
  - 动作词(如存在): **锁定 / 解锁**

#### D) 运行态/终态(同步会话/实例记录/任务)

- 语义: 一次“执行过程”的生命周期状态(等待/运行/暂停/完成/失败/取消)。
- 代码来源:
  - `app/constants/status_types.py`：`SyncStatus` / `SyncSessionStatus` / `TaskStatus` / `InstanceStatus` / `JobStatus`
  - `SyncSession.status`、`SyncInstanceRecord.status`
- 当前 UI 文案(漂移点):
  - pending: `排队中` vs `等待中` vs `等待`
  - running: `运行中` vs `进行中` vs `执行中`
  - completed: `已完成`
  - failed: `失败`
  - cancelled: `已取消`
  - paused: `已暂停`
- Canonical(v1):
  - pending: **等待中**
  - running: **运行中**
  - paused: **已暂停**
  - completed: **已完成**
  - failed: **失败**
  - cancelled: **已取消**
- 备注(允许的语义分裂): “单实例执行结果”若明确为成功/失败结果，可用 `成功/失败`（而不是 `已完成/失败`），避免用户把“完成”理解为“只是结束，不代表成功”。

#### E) 调度器 Job 状态与动作

- 语义: Scheduler 中 job 的运行状态与管理动作。
- 代码来源:
  - job.state（如 `STATE_RUNNING/STATE_EXECUTING/STATE_PAUSED/STATE_ERROR`）+ pause/resume 行为
  - `app/constants/status_types.py::JobStatus`（scheduled/running/paused/stopped）
- 当前 UI 文案(漂移点):
  - 状态: `运行中`、`已暂停`、`失败`、`进行中的任务`、`已暂停的任务`
  - 动作: `暂停任务`、`启用任务`、toast `任务已禁用/任务已启用`
- Canonical(v1):
  - 状态词: **已调度 / 运行中 / 已暂停 / 已停止 / 失败 / 未知**
  - 动作词: **暂停 / 恢复**（避免用“启用/禁用”表达 pause/resume，与 `is_active` 维度混用）

#### F) 健康状态(分区/系统)

- 语义: 系统/组件健康检查结果(非业务对象激活/锁定/删除维度)。
- 代码来源: Partition health API（`healthy/warning/unhealthy/maintenance`）+ Dashboard 健康展示。
- 当前 UI 文案:
  - `正常 / 告警 / 异常 / 维护中 / 未知`
  - 失败类兜底: `健康检查失败`
- Canonical(v1): **正常 / 告警 / 异常 / 维护中 / 未知**

#### G) 数据新鲜度/采集状态(台账/容量采集)

- 语义: 数据是否已采集、是否过期需要刷新（不是任务“运行中”）。
- 代码来源: `DatabaseLedgerService._resolve_sync_status`（`pending/running/completed/failed` + label: `待采集/待刷新/已更新/超时`）与 UI 兜底 `未采集`。
- Canonical(v1): **待采集 / 已更新 / 待刷新 / 超时 / 未采集**

#### H) 分区时间状态(分区清单)

- 语义: 分区属于当前周期/历史周期/未来预建，或存在告警标记。
- 代码来源: `app/static/js/modules/views/admin/partitions/partition-list.js`（`current/past/future/warning/unknown`）。
- 当前 UI 文案: `当前 / 历史 / 未来 / 告警 / 未知`
- Canonical(v1): **当前 / 历史 / 未来 / 告警 / 未知**

#### I) 风险等级(账户分类)

- 语义: 规则/分类的风险等级标签(用于辅助识别高风险账户分类)。
- 代码来源: `app/static/js/modules/views/accounts/account-classification/index.js`（`low/medium/high/critical` + 未标记）。
- 当前 UI 文案: `低风险 / 中风险 / 高风险 / 极高风险 / 未标记风险`
- Canonical(v1): **低风险 / 中风险 / 高风险 / 极高风险 / 未标记风险**

---

## 2. 不变约束(行为/契约/兼容)

- 行为不变: 仅调整 UI 文案, 不改变状态含义, 不改变接口字段, 不改变权限与业务逻辑.
- 一致性优先: 同一页面内不得混用同义词, 同一语义状态全站优先保持同一对词.
- 可回滚: 变更应按页面/模块拆分 PR, 避免一次性全站替换造成回归难定位.
- 展示对齐: 允许状态文案为 1/2/3 个字，但在表格 status 列等“垂直扫描”场景，需要通过样式保证视觉对齐(避免居中布局下因字数不同产生抖动).

---

## 3. 方案选项(2-3 个)与推荐

### Option A(中期, 推荐): 选择一组 canonical 状态词, 全站替换

做法:

- 明确 "active/inactive" 的 canonical 词对(例如 "启用/停用" 或 "正常/停用").
- 将现有 UI 中的漂移词统一替换为 canonical 词对.

优点:

- 见效快, 成本低.
- 对用户心智模型提升明显.

缺点:

- 若缺少标准与门禁, 未来仍可能回归.

### Option B(长期): 术语表 + 状态词表 + 统一 helper

做法:

- 在 `docs/standards/terminology.md` 增加 "状态用词" 小节, 固化 canonical 词表与适用范围.
- 在前端增加 `UI.Terms` 或 `UI.resolveStatusText(...)` helper, 页面不再手写状态词.

优点:

- 从源头减少重复与漂移.
- 便于后续扩展到多语言或 UI 统一改版.

缺点:

- 需要迁移调用点, 需要逐步落地.

### Option C(长期): 门禁与字典扫描

做法:

- 增加 `scripts/ci/ui-terminology-guard.sh`, 扫描特定目录中是否出现 "deprecated 词"(例如某一组不再允许的状态词).
- 采用 baseline + 逐步清零策略, 避免一次性阻断存量.

优点:

- 可防止回归, 治理可持续.

缺点:

- 需要精确限定扫描范围, 避免误伤实现层的 "禁用按钮" 等技术描述.

推荐结论:

- Phase 1 先落地 Option A(统一文案).
- Phase 2 结合 Option B/C: 标准化 + helper + 门禁, 让一致性可持续.

---

## 4. 分阶段计划(中期 + 长期)

### Phase 1(中期, 1-2 周): 统一常见状态词(v1)并清理漂移点

验收口径:

- 激活状态(`is_active`)在实例/标签/凭据/用户等页面使用同一组词: `启用/停用`.
- 同一页面内不再出现以下漂移:
  - 激活: `禁用/停用/正常/活跃` 混用
  - 运行态: `运行中/进行中/执行中` 混用；`排队中/等待中/等待` 混用
  - 调度器动作: `启用/禁用` 混入 pause/resume 语义
  - 锁定/删除: `锁定/已锁定` 与 `已删除` 的用法不一致

建议实施步骤:

1. 决策 canonical 词表(v1)(见 1.3).
2. 解决对齐问题(基础样式):
   - 对 Grid.js 的 `status` 列，为 `.status-pill` 增加统一最小宽度，避免 1/2/3 字状态在居中列中“左右抖动”.
3. 替换证据点(激活状态):
   - `app/static/js/modules/views/instances/list.js`: status 文案对齐.
   - `app/templates/tags/index.html`: 统计卡片/状态文案对齐.
4. 扩展清理(激活状态):
   - `app/templates/instances/statistics.html`, `app/templates/accounts/statistics.html` 等统计文案对齐.
   - `app/static/js/modules/views/credentials/list.js`, `app/static/js/modules/views/auth/list.js`, `app/static/js/modules/views/tags/index.js` 等已存在 "启用/停用" 的页面, 确认与 canonical 一致.
5. 补齐其他状态漂移点(锁定/删除/运行态/健康):
   - 锁定: `app/templates/instances/detail.html`, `app/static/js/modules/views/accounts/ledgers.js`, `app/static/js/modules/views/instances/detail.js`
   - 删除/回收站: `app/templates/instances/list.html`, `app/templates/instances/detail.html`, `app/static/js/modules/views/instances/list.js`, `app/static/js/modules/views/instances/detail.js`
   - 同步会话运行态: `app/static/js/modules/views/history/sessions/sync-sessions.js`, `app/static/js/modules/views/history/sessions/session-detail.js`
   - 调度器运行态: `app/templates/admin/scheduler/index.html`, `app/static/js/modules/views/admin/scheduler/index.js`
   - 健康状态: `app/templates/dashboard/overview.html`, `app/static/js/modules/views/admin/partitions/index.js`
6. 手工回归:
   - 关键页面: 实例管理, 标签管理, 凭据管理, 用户管理.
   - 关键页面: 同步会话列表/详情, 调度器管理, 分区管理, Dashboard.
   - 口径: status badge, action button, toast 文案一致.

### Phase 2(长期, 2-4 周): 标准化 + 防回归机制

验收口径:

- `docs/standards/terminology.md` 增加 "状态用词" 条目, 明确:
  - 激活/锁定/删除/运行态/健康状态/数据新鲜度的 canonical 词表
  - 例外场景与适用边界(例如 “数据新鲜度” 不使用 “运行中/已完成”)
- 新增统一 helper 或至少在关键组件内集中生成状态词, 减少手写.
- 新增门禁或 checklist 防止回归.

建议实施步骤:

1. 更新术语标准:
   - `docs/standards/terminology.md` 增加 "状态用词" 小节, 并给出正反例.
2. 引入统一 helper(建议最小化):
   - `app/static/js/modules/ui/terms.js`:
     - `resolveActiveStatusText(isActive)` -> returns canonical word
     - 可选: `resolveActiveActionText(isActive)` -> for buttons
     - 可选: `resolveRunStatusText(status)` -> for pending/running/paused/completed/failed/cancelled
     - 可选: `resolveLockStatusText(isLocked)` / `resolveDeletionStatusText(isDeleted)`
3. 门禁与协作入口:
   - 增加 `scripts/ci/ui-terminology-guard.sh`(只扫描 UI 文案目录, 且只对已约定 deprecated 词生效).
   - 更新 `.github/pull_request_template.md` 增加 "术语一致性" 自检项(引用 `docs/standards/terminology.md`).

---

## 5. 风险与回滚

风险:

- "禁用" 在代码中同时用于技术语义(按钮 disabled), 门禁需要避免误伤.
- 部分页面的状态语义不完全等价(例如 scheduler 的 "暂停/启用" 与 is_active 不同), 需要明确例外词表.

回滚:

- 文案替换可按页面回退, 但必须保持该页面内用词一致(禁止回到混用状态).

---

## 6. 验证与门禁

静态检查(建议命令):

- `rg -n \"禁用|停用\" app/templates app/static/js/modules/views`
- `rg -n \"运行中|进行中|执行中|排队中|等待中|等待\" app/templates app/static/js/modules/views/history app/static/js/modules/views/admin`
- `rg -n \"已锁定|锁定状态|锁定/\" app/templates app/static/js/modules/views`
- `rg -n \"已删除|回收站|显示已删除\" app/templates app/static/js/modules/views`

手工验证(最低覆盖):

- 实例管理列表: 状态列与操作文案一致.
- 标签管理页: 统计卡片与状态列一致.
- 同步会话: 列表与详情页 status pill/统计卡片一致.
- 调度器管理: 任务卡片状态与动作按钮/toast 一致.
- 表格对齐: 同一 `status` 列内 `失败/已完成/运行中/等待中/已取消/已暂停/已删除` 等状态 pill 左右对齐、不抖动.

---

## 7. 清理计划

- Phase 1 完成后: 证据点相关页面不再出现漂移词.
- Phase 2 完成后: 新增页面不应再手写状态词, 或手写时必须遵守术语表与门禁.

---

## 8. Open Questions(需要确认)

1. canonical 词对选择: 已确认使用 `启用/停用`.
2. running 状态统一口径: 已确认统一为 `运行中`.
3. pending 状态统一口径: 已确认统一为 `等待中`（`排队中` 仅在“明确存在队列/排队语义”的页面使用）.
4. 对 scheduler/job 的 pause/resume 动作口径: `暂停/恢复` vs `暂停/启用`，是否确认统一为 `暂停/恢复` 并禁止出现 `禁用任务`?
