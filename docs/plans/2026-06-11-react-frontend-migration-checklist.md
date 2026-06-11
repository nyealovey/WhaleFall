# React Frontend Migration Checklist

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-06-11
> 更新: 2026-06-11
> 范围: `/console` React 新前端迁移进度
> 关联: `frontend/`, `app/api/v1/`, `docs/Obsidian/standards/doc/guide/documentation.md`

## 目标

在不影响旧站点的前提下，逐步把后台页面迁移到 `/console` React 新前端。迁移期间旧页面继续保留完整功能入口，新页面优先迁移只读浏览路径，写操作、批量操作和高风险动作后续单独迁移与验收。

## 更新规则

- 每完成一批页面迁移，必须更新本文档。
- 已迁移页面必须记录新路径、旧路径、接入 API、迁移范围和验证命令。
- 只迁移只读首屏时，状态写为 `Done - read-only`，不要标记成完整替换。
- 涉及新增、删除、同步、导入、导出、批量操作时，需要单独补充风险与回滚说明。

## 当前摘要

- React 入口: `/console`
- 已接入页面: 12
- 仍为占位页: 10
- 当前策略: 只读页面优先，写操作延后
- 旧站点状态: 保持不动
- UI 基线: shadcn 风格组件优先，当前已接入 Button、Card、Badge、Input、Separator、Table、Skeleton、Alert、Progress、Chart

## 已完成

| 新前端路径 | 旧页面路径 | 状态 | 接入 API | 备注 |
| --- | --- | --- | --- | --- |
| `/console/dashboard` | `/dashboard/` | Done - read-only | `/api/v1/dashboard/overview`, `/api/v1/dashboard/status`, `/api/v1/dashboard/charts?type=all`, `/api/v1/dashboard/activities` | 仪表盘指标、运行状态、图表信号、活动空态 |
| `/console/risk-center` | `/risk-center/` | Done - read-only | `/api/v1/risk-center/summary`, `/api/v1/risk-center/cards?limit=12` | 风险汇总、风险卡片、top risks |
| `/console/instances` | `/instances/` | Done - read-only | `/api/v1/instances?page=1&limit=20` | 实例首屏列表；新增、编辑、删除、同步仍走旧版 |
| `/console/database-ledgers` | `/databases/ledgers` | Done - read-only | `/api/v1/databases/ledgers?page=1&limit=20` | 数据库台账首屏列表；导出、同步仍走旧版 |
| `/console/account-ledgers` | `/accounts/ledgers` | Done - read-only | `/api/v1/accounts/ledgers?page=1&limit=20` | 账户台账首屏列表；权限详情、导出仍走旧版 |
| `/console/capacity/instances` | `/capacity/instances` | Done - read-only | `/api/v1/capacity/instances?period_type=daily&page=1&limit=20&start_date=...&end_date=...`, `/api/v1/capacity/instances/summary?period_type=daily&start_date=...&end_date=...` | 最近 30 天日粒度实例容量；聚合刷新仍走旧版 |
| `/console/capacity/databases` | `/capacity/databases` | Done - read-only | `/api/v1/capacity/databases?period_type=daily&page=1&limit=20&start_date=...&end_date=...`, `/api/v1/capacity/databases/summary?period_type=daily&start_date=...&end_date=...` | 最近 30 天日粒度数据库容量；聚合刷新仍走旧版 |
| `/console/instance-statistics` | `/instances/statistics` | Done - read-only | `/api/v1/instances/statistics` | 实例统计指标与分布 |
| `/console/account-statistics` | `/accounts/statistics` | Done - read-only | `/api/v1/accounts/statistics/summary`, `/api/v1/accounts/statistics/db-types`, `/api/v1/accounts/statistics/classifications`, `/api/v1/accounts/statistics/rules` | 账户统计汇总、分类、规则命中 |
| `/console/database-statistics` | `/databases/statistics` | Done - read-only | `/api/v1/databases/statistics` | 数据库统计、同步状态、容量排行 |
| `/console/logs` | `/history/logs/` | Done - read-only | `/api/v1/logs?page=1&limit=20`, `/api/v1/logs/statistics?hours=24` | 最近 24 小时系统日志统计与首屏日志列表；检索、详情仍走旧版 |
| `/console/account-change-logs` | `/history/account-change-logs/` | Done - read-only | `/api/v1/account-change-logs?page=1&limit=20`, `/api/v1/account-change-logs/statistics?hours=24` | 最近 24 小时账户变更统计与首屏变更列表；详情仍走旧版 |

## 待迁移

| 新前端路径 | 旧页面路径 | 优先级 | 迁移建议 |
| --- | --- | --- | --- |
| `/console/clusters` | `/cluster/` | P1 | 先迁移 SQL Server/MySQL 群集只读列表，再迁移同步动作 |
| `/console/account-classifications` | `/accounts/classifications/` | P1 | 规则与分类写操作较多，先迁移只读分类/规则列表 |
| `/console/classification-statistics` | `/accounts/statistics/classifications` | P1 | 已有统计 API，可接在账户统计之后 |
| `/console/scheduler` | `/scheduler/` | P2 | 含手动执行动作，需补 CSRF 与确认交互 |
| `/console/sync-sessions` | `/history/sessions/` | P2 | 先迁移会话列表，再迁移取消动作 |
| `/console/users` | `/users/` | P3 | 用户新增/删除/角色修改需单独验收 |
| `/console/settings` | `/admin/system-settings` | P3 | 配置写操作集中，需最后迁移 |
| `/console/credentials` | `/credentials/` | P3 | 涉及密钥与连接测试，需更严格确认 |
| `/console/tags` | `/tags/` | P3 | 批量绑定和删除需单独迁移 |
| `/console/partitions` | `/partition/` | P3 | 清理动作风险高，最后迁移 |

## 最近验证

2026-06-11 当前批次验证通过:

```bash
npm --prefix frontend run test          # 17 files, 33 tests passed
npm --prefix frontend run typecheck     # passed
npm --prefix frontend run lint          # passed
npm --prefix frontend run build         # passed
uv run pytest tests/unit/routes/test_api_v1_dashboard_contract.py tests/unit/routes/test_api_v1_risk_center_contract.py tests/unit/routes/test_api_v1_instances_contract.py tests/unit/routes/test_api_v1_databases_ledgers_contract.py tests/unit/routes/test_api_v1_accounts_ledgers_contract.py tests/unit/routes/test_api_v1_capacity_instances_contract.py tests/unit/routes/test_api_v1_capacity_databases_contract.py tests/unit/routes/test_api_v1_history_logs_contract.py tests/unit/routes/test_api_v1_account_change_logs_contract.py tests/unit/routes/test_api_v1_instances_statistics_contract.py tests/unit/routes/test_api_v1_accounts_statistics_contract.py tests/unit/routes/test_api_v1_databases_statistics_contract.py tests/unit/routes/test_console_frontend_contract.py -q  # 76 passed
git diff --check                        # passed
```

## 变更记录

- 2026-06-11: 建立 React 迁移清单；记录 dashboard、risk-center、instances、database-ledgers、account-ledgers、instance-statistics、account-statistics、database-statistics 的只读迁移状态。
- 2026-06-11: 迁移实例容量、数据库容量只读首屏；使用最近 30 天日粒度列表与汇总 API。
- 2026-06-11: 迁移日志中心、账户变更历史只读首屏；补充 shadcn Table、Skeleton、Alert、Progress、Chart 基础组件，运行信号改为 LineChart/AreaChart。
