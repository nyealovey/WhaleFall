---
title: 名词表与边界(一页纸)
aliases:
  - glossary-and-boundaries
  - terminology
tags:
  - architecture
  - architecture/glossary
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 术语表 + Web UI vs API v1 边界 + task/service/repository 边界
related:
  - "[[architecture/project-structure]]"
  - "[[architecture/spec]]"
  - "[[architecture/developer-entrypoint]]"
  - "[[architecture/identity-access]]"
  - "[[standards/backend/guide/layer/README|后端分层标准]]"
  - "[[operations/observability-ops]]"
---

# 名词表与边界(一页纸)

> [!note] 目标
> 统一团队对核心概念的叫法, 并明确不同入口(Web/API/Task)的边界与推荐用法.

## 1. 名词表(Terminology)

| 名词 | 含义(一句话) | 代码落点(建议从这里开始读) |
| --- | --- | --- |
| Instance(实例) | 一个外部数据库实例的连接目标(类型 + host/port + 默认库等) | `app/models/instance.py` |
| Credential(凭据) | 连接外部数据库使用的账号口令(加密存储) | `app/models/credential.py` |
| InstanceDatabase(实例数据库) | 某个实例下发现/维护的数据库清单(库存) | `app/models/instance_database.py` |
| InstanceAccount(实例账户) | 某个实例下发现/维护的账号清单(库存) | `app/models/instance_account.py` |
| AccountPermission(权限快照) | 某个账户的权限快照(按 db_type 存 JSON 字段) | `app/models/account_permission.py` |
| AccountChangeLog(变更记录) | 权限快照的变化记录(用于审计/对比) | `app/models/account_change_log.py` |
| AccountClassification(分类) | 对账户做分组的分类对象 | `app/models/account_classification.py` |
| ClassificationRule(分类规则) | 分类内的规则(表达式为 DSL v4) | `app/models/account_classification.py` |
| Tag(标签) | 实例的标签(用于筛选/组织) | `app/models/tag.py` |
| Ledger(台账) | 面向人阅读的汇总视图(账户台账/数据库台账) | `app/services/ledgers/**` |
| SyncSession(同步会话) | 一次批量/任务执行的会话载体(总览状态 + 统计) | `app/models/sync_session.py` |
| SyncInstanceRecord(实例记录) | session 内每个 instance 的执行记录(状态 + 错误 + 统计) | `app/models/sync_instance_record.py` |
| DatabaseSizeStat(库容量日统计) | 按天记录某实例下某库的容量 | `app/models/database_size_stat.py` |
| InstanceSizeStat(实例容量日统计) | 按天记录某实例的总容量与库数量 | `app/models/instance_size_stat.py` |
| Aggregations(聚合) | 周/月/季等周期聚合结果 | `app/models/*_size_aggregation.py` |
| UnifiedLog(统一日志) | structlog 落库后的结构化日志 | `app/models/unified_log.py` |

## 2. Web UI vs API v1 边界

### 2.1 Web UI

- 入口: `app/routes/**` + `app/templates/**` + `app/static/**`
- 目标: 面向人交互, 页面渲染, 表单提交.
- 认证/会话: Flask-Login session cookie + CSRF.

### 2.2 API v1(`/api/v1/**`)

- 入口: `app/api/v1/namespaces/**`
- 目标: 面向程序的 JSON API, 响应统一 envelope, 提供 OpenAPI.
- 认证/权限/CSRF: 见 [[architecture/identity-access]] 与 `docs/Obsidian/API/*-api-contract.md`.

推荐用法:

- 业务集成/脚本调用: 优先走 API v1.
- 页面交互: Web UI 调用 API v1 或直接走 routes, 以现有实现为准.
- 禁止把 Web routes 当成 API 使用(返回 HTML, 错误语义与 CSRF 约束不同).

## 3. Task/Scheduler/Service/Repository 边界

### 3.1 Task(任务)

- 落点: `app/tasks/**`
- 职责: 作为后台执行入口, 负责 app context, 可观测字段, 会话状态的粗粒度推进.
- 业务逻辑: 下沉到 `app/services/**`(任务不要变成巨型脚本).

### 3.2 Scheduler(调度器)

- 落点: `app/scheduler.py`
- jobstore: `userdata/scheduler.db`(SQLite)
- 开关: `ENABLE_SCHEDULER`(见 `docs/Obsidian/reference/config/environment-variables.md`)

### 3.3 Service(服务层)

- 落点: `app/services/**`
- 职责: 业务编排 + 事务边界 + 失败语义.
- 上游: routes/api/tasks.
- 下游: repositories/models/utils.

### 3.4 Repository(仓储层)

- 落点: `app/repositories/**`
- 职责: 只读 query 组合, 数据访问细节, 避免在上层散落复杂查询.

分层依赖方向见 [[standards/backend/guide/layer/README|后端分层标准]] 与 [[architecture/module-dependency-graph]].

