# 未被 layer(10 篇)标准覆盖的后端 Python 文件：盘点与建议（2026-01-11）
> 状态: Draft  
> 创建: 2026-01-11  
> 更新: 2026-01-11  
> 口径: “layer 标准覆盖范围”= `docs/Obsidian/standards/backend/layer/` 下 10 篇标准的 scope（`app/api/v1, app/constants, app/forms+views, app/models, app/repositories, app/routes, app/services, app/tasks, app/types, app/utils`）

## 0. 未覆盖清单

### 0.1 `app/**` 内未覆盖（17 个）

- `app/__init__.py`
- `app/api/__init__.py`
- `app/errors.py`
- `app/infra/__init__.py`
- `app/infra/route_safety.py`
- `app/infra/logging/__init__.py`
- `app/infra/logging/queue_worker.py`
- `app/scheduler.py`
- `app/schemas/__init__.py`
- `app/schemas/auth.py`
- `app/schemas/base.py`
- `app/schemas/credentials.py`
- `app/schemas/instances.py`
- `app/schemas/tags.py`
- `app/schemas/users.py`
- `app/schemas/validation.py`
- `app/settings.py`

### 0.2 仓库根目录入口未覆盖（2 个）

- `app.py`
- `wsgi.py`

## 1. 归类与建议（补标准 vs 拆分/迁移）

> 原则：当模块属于“稳定存在的横切能力/架构层”时，应补齐标准文档；当模块属于“混合职责的大文件/可被现有层吸收”时，应拆分/迁移到已有层。

| 路径 | 角色归类 | 推荐动作 | 主要理由 |
|---|---|---|---|
| `app/schemas/**` | Schema 校验层 | **补齐标准文档**（新增 `schemas-layer-standards.md` 或将其纳入 layer/README） | 当前是稳定层（输入校验/字段约束），且存在大量业务阈值（适合与 constants/types 协同）；不建议塞进 types/utils。 |
| `app/infra/**` | Infra 基础设施层 | **补齐标准文档**（新增 `infra-layer-standards.md`） | 包含 route safety、异步日志 worker 等明确“非业务层”能力，且天然依赖 DB/app context；需要明确它与 services 的事务边界关系。 |
| `app/errors.py` | Errors 异常层 | **补齐标准文档**（新增 `errors-layer-standards.md` 或扩展 layer/README 并补齐 errors 标准） | 依赖方向与错误封套/日志强相关；目前 layer/README 已把它作为节点，但缺少对应标准会导致口径漂移。 |
| `app/settings.py` | Settings/Config 层 | **优先补齐/对齐现有配置标准**（可新增 `settings-layer-standards.md`，或在 `configuration-and-secrets` 中明确其“层规则”） | 这是“配置入口层”，与业务层/工具层的边界不同；若继续增长，可考虑包化拆分。 |
| `app/scheduler.py` | Scheduler(任务调度)层 | **建议归入 Infra 并补齐标准**（或新增 `scheduler-layer-standards.md`） | 该文件承担 jobstore/锁/配置加载/注册等基础设施职责，且与 tasks 的边界需要明确；文件已较大（~669 行），未来可考虑拆分为 package。 |
| `app/__init__.py` | App Bootstrap(应用装配)层 | **补齐标准文档**（新增 `bootstrap-layer-standards.md` 或纳入 Infra 标准） | 这是应用总装配点：注册扩展/蓝图/错误处理/日志/调度器；不属于业务分层，需要单独约束“允许 import 什么、禁止做什么”。 |
| `app/api/__init__.py` | API 注册入口 | **扩展现有 API 标准 scope**（将 API 标准从 `app/api/v1/**` 扩到 `app/api/**`） | 这是 v1 blueprint 的注册入口，语义属于 API 层；不建议为它单开一层。 |
| `app.py`/`wsgi.py` | 运行入口 | **补齐最小入口规范**（可放在 bootstrap/infra 标准里） | 入口文件通常允许少量“非分层代码”（如 app factory、WSGI patch）；但要明确哪些越界是“入口特例”。 |

## 2. “需要拆分/迁移”的具体建议（按收益排序）

### 2.1 `app/scheduler.py`（建议拆分为 package）

触发条件：文件体量已接近 700 行，且同时承担“锁、配置解析、job 注册、事件监听、APScheduler 细节”多职责。

建议拆分方向（示例）：

- `app/infra/scheduler/__init__.py`：对外 `init_scheduler(app)`/`TaskScheduler` 门面
- `app/infra/scheduler/lock.py`：文件锁与单实例运行
- `app/infra/scheduler/config_loader.py`：读取 `app/config/scheduler_tasks.yaml`
- `app/infra/scheduler/registry.py`：`TASK_FUNCTIONS` 与 callable 加载

### 2.2 `app/settings.py`（如继续增长，建议包化）

触发条件：文件体量 ~700 行，未来配置项只会继续增加。

建议拆分方向（示例）：

- `app/settings/__init__.py`：`Settings.load()` 与外部唯一入口
- `app/settings/schema.py`：字段定义与校验
- `app/settings/loaders.py`：环境变量/文件读取
- `app/settings/flask_mapping.py`：`to_flask_config()` 映射

> 注：若现有 `docs/Obsidian/standards/backend/configuration-and-secrets.md` 已足够细，则只需在 layer/README 明确 Settings 的“层规则”，不必马上拆文件。

### 2.3 `app/utils/database_batch_manager.py`（建议迁移到允许 DB 的层）

虽然它属于 layer(10 篇)范围内的 Utils，但其职责本质是 DB 批量写入/事务控制，更接近 Repository/Infra。

建议：迁移到 `app/repositories/common/**` 或 `app/infra/db/**`，并在对应标准中明确“允许/禁止”项。

## 3. 最小化补文档清单（建议先做这几篇）

若目标是“降低边界漂移的争议成本”，建议优先补齐以下标准（按优先级）：

1) `Infra 层编写规范`：覆盖 `app/infra/**` +（可选）`app/scheduler.py`
2) `Schemas 层编写规范`：覆盖 `app/schemas/**`
3) `Errors 层编写规范`：覆盖 `app/errors.py`（并与错误封套/日志口径对齐）
4) `Bootstrap/Entrypoint 规范`：覆盖 `app/__init__.py`, `app.py`, `wsgi.py`

