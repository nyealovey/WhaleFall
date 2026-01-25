---
title: Repository 仓储层编写规范
aliases:
  - repository-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
enforcement: gate
created: 2026-01-09
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/repositories/**` 下所有仓储类"
related:
  - "[[standards/backend/standard/write-operation-boundary]]"
  - "[[standards/backend/gate/layer/services-layer]]"
  - "[[standards/backend/gate/layer/models-layer]]"
---

# Repository 仓储层编写规范

> [!note] 说明
> Repository 封装数据访问与 Query 组装. Service 负责编排与事务边界, Repository 负责把 "怎么查/怎么写" 变成可复用的接口.

## 目的

- 统一数据访问入口, 降低 Model.query 在代码中四处扩散导致的耦合与复用困难.
- 让查询逻辑可复用可测试, 并把排序/筛选/分页从业务逻辑中剥离.
- 固化 "Repository 不做业务逻辑/不 commit" 的边界, 避免不可控副作用.

## 适用范围

- `app/repositories/**` 下所有仓储类与查询辅助模块.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Repository 负责 ORM Query 组装, 筛选/排序/分页, 数据访问细节封装.
- MUST: 返回 Model 对象或稳定的原始数据结构(dict/list), 由 Service 决定如何转换为 DTO.
- MUST NOT: 包含业务规则判断(例如权限, 冲突判定, 状态机).
- MUST NOT: 调用 `app.services.*` 或依赖 Routes/API.
- MUST NOT: 返回 `flask.Response` 或 JSON 封套.

### 2) 事务处理

- MUST: Repository 可以 `flush` 以获取主键或触发约束, 但 MUST NOT `commit`.
- MUST: 写操作的事务语义由上层(通常为 Service/Coordinator) 决策；提交点由入口(`safe_route_call`/tasks/scripts) 统一承担，参考 [[standards/backend/standard/write-operation-boundary]].

### 3) 命名规范

文件命名:

| 命名模式 | 用途 | 示例 |
|---|---|---|
| `{entity}_repository.py` | 单实体仓储 | `instances_repository.py` |
| `{domain}_repository.py` | 领域仓储 | `capacity_databases_repository.py` |
| `{function}_repository.py` | 功能仓储 | `filter_options_repository.py` |

方法命名前缀建议:

| 前缀 | 用途 | 示例 |
|---|---|---|
| `get_` | 获取单个对象 | `get_instance()`, `get_by_id()` |
| `get_*_or_404` | 获取或抛 404 | `get_instance_or_404()` |
| `list_` | 获取列表 | `list_instances()`, `list_active()` |
| `fetch_` | 获取原始数据/聚合 | `fetch_statistics()` |
| `count_` | 计数查询 | `count_active()` |
| `exists_` | 存在性检查 | `exists_by_name()` |
| `add` | 新增对象 | `add(instance)` |
| `delete` | 删除对象 | `delete(instance_id)` |

### 4) 目录结构(推荐)

```text
app/repositories/
├── __init__.py
├── instances_repository.py
├── credentials_repository.py
├── tags_repository.py
├── users_repository.py
├── capacity_databases_repository.py
├── capacity_instances_repository.py
├── ledgers/
│   ├── __init__.py
│   ├── accounts_ledger_repository.py
│   └── database_ledger_repository.py
└── common/
    └── query_builder.py
```

### 5) 分页返回

- SHOULD: 列表查询返回 `PaginatedResult[T]` 等稳定结构, 避免上层重复拼分页字段.

### 6) 依赖规则

允许依赖:

- MUST: `app.models.*`
- MAY: `app.core.types.*`
- MAY: `app.core.exceptions`
- MAY: `app` 的 `db` 会话(仅用于 `add/flush` 等低级操作)
- MAY: `sqlalchemy`/`sqlalchemy.orm`

禁止依赖:

- MUST NOT: `app.services.*`
- MUST NOT: `app.routes.*`, `app.api.*`

### 7) 代码规模限制

- SHOULD: 单文件 <= 400 行.
- SHOULD: 单类方法数 <= 15 个.
- SHOULD: 单方法 <= 50 行.

## 正反例

### 正例: 仓储基本结构

- 判定点:
  - Repository 只承载数据访问与查询细节, 不承载业务编排与事务边界.
  - 写入默认只 `add/flush`, 提交/回滚由上层事务边界负责.
  - 对外暴露的方法形态稳定, 便于 service 组合与测试替身注入.
- 长示例见: [[reference/examples/backend-layer-examples#仓储基本结构|Repository Layer 仓储基本结构(长示例)]]

### 反例: 在 Repository 中 commit

```python
class BadRepository:
    def add(self, obj):
        db.session.add(obj)
        db.session.commit()  # 反例: Repository 不允许 commit
```

## 门禁/检查方式

- 静态门禁（commit 位置 allowlist）：`./scripts/ci/db-session-commit-allowlist-guard.sh`（事务边界见 [[standards/backend/standard/write-operation-boundary]]）
- 评审检查:
  - 是否存在在 Repository 内 `commit`?
  - 是否引入业务判断或调用 Service?
  - 查询与分页是否在 Repository 内完成, 而不是散落在 Service?
- 自查命令(示例):

```bash
rg -n "db\\.session\\.commit\\(" app/repositories
rg -n "from app\\.services\\." app/repositories
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/guide/documentation|文档结构与编写规范]] 补齐标准章节.
- 2026-01-13: 明确 Repository 不承载事务提交点, 并将“事务边界”表述对齐为“提交点 vs 决策点”.
