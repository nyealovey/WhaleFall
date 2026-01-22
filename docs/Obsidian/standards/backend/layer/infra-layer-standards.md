---
title: Infra 基础设施层编写规范
aliases:
  - infra-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-12
updated: 2026-01-12
owner: WhaleFall Team
scope: "`app/infra/**`, `app/scheduler.py`"
related:
  - "[[standards/backend/layer/README|后端分层标准]]"
  - "[[standards/backend/write-operation-boundary]]"
  - "[[standards/backend/task-and-scheduler]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/error-message-schema-unification]]"
---

# Infra 基础设施层编写规范

> [!note] 说明
> Infra 层用于承载“与框架/外部依赖强绑定、带副作用、需要失败隔离或适配”的基础设施代码，例如事务边界包装、后台 worker、调度器与跨切面日志/安全包装器。业务规则必须下沉到 Service，数据访问必须通过 Repository 组织。

## 目的

- 收敛跨切面能力（事务边界、失败隔离、日志上下文、调度器单实例）到可审计的少量入口，避免散落在各层的 `try/except` 与兜底链。
- 提供清晰的“适配/封装/回退”口径（facade/adapter），让上层只消费稳定接口而不是直接耦合外部库细节。
- 明确 Infra 的副作用边界（允许点/禁止点），降低循环依赖与隐式写入的风险。

## 适用范围

- `app/infra/**` 下所有基础设施模块。
- 调度器：`app/scheduler.py`（虽然不在 `app/infra/` 目录下，但其语义属于 Infra）。

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Infra 提供“包装器/适配器/门面”，例如统一异常转换、统一日志字段、统一事务边界。
- MUST: Infra 的入口函数/类要明确其副作用：是否会 `commit/rollback`、是否会启动后台线程、是否会持锁。
- MUST NOT: 在 Infra 中写业务规则（权限判定、状态机、跨实体编排等），这些必须下沉到 `app/services/**`。
- SHOULD: 通过“参数/回调/Protocol”注入上层逻辑，避免 Infra 反向 import 业务层造成循环依赖。

### 2) 防御/回退/失败隔离

- MUST: 对“预期失败”使用显式异常列表（例如 `EXPECTED_EXCEPTIONS` 元组）并在日志中输出 `error_type`。
- MUST: 对“非预期失败”必须记录 error 日志并将异常转换为项目统一错误（或返回明确的失败结果），禁止静默吞异常后继续执行。
- SHOULD: 兜底值要显式、可审计：
  - 对可选入参字典/元组等可使用 `x or {}` / `x or ()` 做形状兜底（空即视为缺省）。
  - 对可能合法为 `0/""/[]` 的业务值禁止用 `or` 做兜底（会把合法值误判为缺省），应使用 `is None` 判断。

### 3) 事务边界与数据库访问

- MUST: 写路径的 `commit/rollback` 只允许发生在“事务边界入口”，详见 [[standards/backend/write-operation-boundary|写操作事务边界]]。
- MUST: Infra 中涉及事务边界的模块必须在 docstring/README 明确其策略（成功提交、异常回滚、回退异常类型）。
- SHOULD: 若需避免循环导入，使用 `importlib.import_module`/惰性加载（参考日志 worker 的做法），但必须保证导入路径稳定。

### 4) 调度器（`app/scheduler.py`）

- MUST: 单实例策略与启停策略遵循 [[standards/backend/task-and-scheduler|任务与调度(APScheduler)]]（`ENABLE_SCHEDULER`、reloader 子进程策略、生产 Web/Scheduler 分进程建议）。
- MUST: 调度器初始化失败不得阻塞应用启动（必须记录结构化日志并安全返回）。
- SHOULD: 任务函数导入路径保持稳定，新增任务同时更新 `TASK_FUNCTIONS` 与配置文件，避免“找不到 callable”。

### 5) 依赖规则

允许依赖:

- MUST: 标准库
- MAY: 第三方库（例如 Flask/SQLAlchemy/APScheduler/structlog/werkzeug）
- MAY: `app.core.constants.*`, `app.core.types.*`, `app.core.exceptions`, `app.utils.*`
- MAY: `app` 的扩展对象与 `app.models.*`（仅当模块语义本身是事务边界入口/worker，并且能证明不会引入循环依赖）

禁止依赖:

- MUST NOT: `app.routes.*`, `app.api.*`（Infra 不应依赖具体 HTTP 层实现）
- SHOULD NOT: `app.services.*`, `app.repositories.*`（优先用回调注入或惰性导入；如确需依赖必须在评审说明理由与循环依赖风险）

### 6) 测试要求

- SHOULD: 对 Infra 的关键兜底/失败隔离逻辑补单测（例如锁策略、异常转换、队列满丢弃策略），并覆盖“异常分支”。

## 门禁/检查方式

- 评审检查:
  - 是否把业务逻辑放进了 Infra？
  - 是否存在静默吞异常或隐式副作用（尤其是 `commit/rollback`）？
  - 是否出现 “用 `or` 兜底导致合法空值被覆盖”？
- 自查命令(示例):

```bash
rg -n "from app\\.(routes|api)\\.|from app\\.(services|repositories)\\.|db\\.session\\.query\\b" app/infra app/scheduler.py
```

## 变更历史

- 2026-01-12: 新增 Infra 层标准, 覆盖 `app/infra/**` 与 `app/scheduler.py`.
