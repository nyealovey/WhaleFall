# 账户变更历史（全量页面 + 弹窗重设计）实现说明

> 目的：让“账户变更历史”更易读、更可追溯；并新增一个类似日志中心的全量变更历史页面（最新在前）。

## 目标

- 现有实例详情页内的“变更历史”弹窗：降低信息噪音，优先展示可扫读的摘要；需要时再展开细节。
- 新增“账户变更历史”页面：集中展示所有账户变更记录，提供筛选与详情查看。

## 架构与数据流

### 1) 新增 API：`/api/v1/account-change-logs`

- List：`GET /api/v1/account-change-logs`
  - 支持 `search/db_type/change_type/status/hours/page/limit/sort/order`
  - 默认 `change_time desc`（最新优先）
- Statistics：`GET /api/v1/account-change-logs/statistics?hours=24`
  - 返回：`total_changes/success_count/failed_count/affected_accounts`
- Detail：`GET /api/v1/account-change-logs/<log_id>`
  - 返回单条变更详情（含 diff 列表）

### 2) 新增页面：`/history/account-change-logs/`

- 顶部统计卡片（4 个）
- 筛选卡片：搜索、数据库类型、变更类型、状态、时间范围
- Grid 列表：时间/实例/账号/类型/状态/摘要/详情
- 详情弹窗：复用 change-history 渲染器展示单条变更详情

### 3) 复用渲染器：`ChangeHistoryRenderer`

- 统一：变更类型/状态文案映射、diff 渲染、加载态渲染
- 弹窗（实例详情页）与新页面详情弹窗均复用

## UI 改动点（实例详情页：变更历史弹窗）

- 单条变更改为可折叠卡片（默认仅展开最新一条）
- 摘要区展示：类型 + diff 数量 + 时间 + 状态
- 新增按钮：在新页面打开（带默认筛选：`search=username&db_type=db_type`）

## 验证

- `uv run pytest -m unit`
- `make typecheck`
- `./scripts/ci/ruff-report.sh style`
- `./scripts/ci/eslint-report.sh quick`

