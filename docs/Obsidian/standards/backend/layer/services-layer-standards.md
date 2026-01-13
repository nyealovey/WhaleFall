---
title: Services 服务层编写规范
aliases:
  - services-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-09
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/services/**` 下所有业务服务"
related:
  - "[[standards/doc/service-layer-documentation-standards]]"
  - "[[standards/backend/request-payload-and-schema-validation]]"
  - "[[standards/backend/write-operation-boundary]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/layer/repository-layer-standards]]"
  - "[[standards/backend/layer/models-layer-standards]]"
---

# Services 服务层编写规范

> [!note] 说明
> Service 是后端业务编排的主要承载点. Routes/API 负责 HTTP 接入, Repository 负责数据访问, Model 负责 ORM 映射.

## 目的

- 集中承载业务规则与编排逻辑, 保持 Routes/API "薄" 且一致.
- 固化事务边界与写操作口径, 避免 commit/rollback 分散在各层导致不可控副作用.
- 让业务逻辑更容易测试(通过依赖注入替换仓储/外部依赖).

## 适用范围

- `app/services/**` 下所有服务类与业务编排函数.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Service 负责业务编排, 输入校验, 数据规范化, 事务边界控制, 业务日志记录.
- MUST: 通过 `app.repositories.*` 执行数据访问与 Query 组装.
- MUST NOT: 直接解析 `flask.request`(应由 Routes/API 完成).
- MUST NOT: 返回 `flask.Response` 或 JSON 封套(应由 Routes/API 完成).
- MUST NOT: 直接拼装复杂 SQL/ORM Query(应由 Repository 完成).

### 2) 服务分类

- SHOULD: 按职责拆分为 Read/Write/List/Action 等服务, 避免巨型 Service.
- SHOULD: 读服务(查询/聚合)不做 commit.
- SHOULD: 写服务(创建/更新/删除/恢复)集中处理校验与事务边界.

### 3) 目录结构与组织(推荐)

```text
app/services/
├── __init__.py
├── common/
│   └── filter_options_service.py
├── instances/
│   ├── __init__.py
│   ├── instance_list_service.py
│   ├── instance_detail_read_service.py
│   └── instance_write_service.py
└── aggregation/
    ├── __init__.py
    └── aggregation_service.py
```

组织原则:

- SHOULD: 单一实体多种操作 -> 放在同一业务域目录(例如 `instances/`).
- SHOULD: 跨实体编排 -> 建立独立业务域目录(例如 `aggregation/`).
- MAY: 简单独立功能 -> 根目录单文件.

### 4) 输入校验与数据规范化

- MUST: 对外部输入(HTTP payload, task payload)做 schema 校验与显式转换, 参考 [[standards/backend/request-payload-and-schema-validation]].
- SHOULD: 在进入核心业务逻辑前完成数据规整(例如 trim, 类型转换, 默认值补齐), 避免核心逻辑到处判空.
- MUST NOT: 在 Routes/API 与 Service 两处重复实现相同校验规则.

### 5) 事务边界

- MUST: 默认情况下(Web 请求写路径), Service 是事务语义的主要决策点：通过“正常返回 vs 抛异常”驱动上层 `safe_route_call` 的 `commit/rollback`（提交点见 [[standards/backend/write-operation-boundary|写操作事务边界]]）。
- MUST: Repository 可以 `flush`, 但 MUST NOT `commit`.
- SHOULD: 批量写入支持部分回滚时使用 `db.session.begin_nested()`.

> [!note] 事务边界优先级（Web vs Tasks）
> - Web 请求写路径：提交点在 `safe_route_call`（Infra）；Service 为事务语义决策点（通过抛异常触发 rollback，正常返回触发 commit）。Routes/API 不得自行 `commit/rollback`。
> - 长任务/批处理：允许 Tasks/Infra 作为提交点做分阶段 `commit/rollback`；此时 Service/Runner 必须保持“无 `commit/rollback`”，仅做业务编排与必要的 `flush`，事务语义与提交节奏由 Tasks/Infra 统一掌控。

### 6) 返回值与 DTO

- SHOULD: Service 返回领域对象(Model)或稳定 DTO(`app/core/types/**`), 由上层决定如何渲染/序列化.
- SHOULD: 多返回值或需要携带状态标记时, 定义 `Outcome` dataclass.
- MUST NOT: Service 返回模板上下文 dict 且由 Routes 直接 `render_template(..., **dict)` (建议返回结构化对象或 DTO).

### 7) 依赖注入与可测试性

- SHOULD: Service 构造器支持注入 Repository 依赖, 默认值用 `repository or InstancesRepository()`.
- SHOULD: 需要替换外部依赖(适配器/客户端)时, 用 `Protocol` 或明确的接口类描述依赖.

### 8) 依赖规则

允许依赖:

- MUST: `app.repositories.*`
- MAY: `app.models.*`(用于类型标注或实例化)
- MAY: `app.core.types.*`, `app.schemas.*`, `app.core.exceptions`, `app.utils.*`, `app.core.constants.*`
- MAY: 其他 `app.services.*`(跨域编排需在评审中说明)

禁止依赖:

- MUST NOT: `app.routes.*`, `app.api.*`
- MUST NOT: `flask.request`, `flask.Response`

### 9) 命名规范

方法命名前缀建议:

| 前缀 | 用途 | 示例 |
|---|---|---|
| `get_` | 获取单个对象/详情 | `get_instance_detail()` |
| `list_` | 获取列表 | `list_instances()` |
| `create` | 创建 | `create()` |
| `update` | 更新 | `update()` |
| `delete`/`soft_delete` | 删除 | `soft_delete()` |
| `restore` | 恢复 | `restore()` |
| `sync_` | 同步 | `sync_accounts()` |
| `export_` | 导出 | `export_to_excel()` |
| `validate_` | 校验 | `validate_expression()` |

文件命名建议:

| 命名模式 | 用途 | 示例 |
|---|---|---|
| `{entity}_read_service.py` | 读取服务 | `instance_detail_read_service.py` |
| `{entity}_write_service.py` | 写入服务 | `instance_write_service.py` |
| `{entity}_list_service.py` | 列表服务 | `instance_list_service.py` |
| `{entity}_{action}_service.py` | 特定操作 | `accounts_sync_service.py` |
| `{domain}_service.py` | 领域服务 | `aggregation_service.py` |

类命名建议:

| 类型 | 命名规则 | 示例 |
|---|---|---|
| 读服务 | `{Entity}{Action}ReadService` | `InstanceDetailReadService` |
| 写服务 | `{Entity}WriteService` | `InstanceWriteService` |
| 列表服务 | `{Entity}ListService` | `InstanceListService` |
| 操作服务 | `{Entity}{Action}Service` | `AccountsSyncService` |
| 结果类 | `{Entity}{Action}Outcome` | `InstanceSoftDeleteOutcome` |

### 10) 代码规模限制

- SHOULD: 单文件 <= 300 行.
- SHOULD: 单类方法数 <= 10 个.
- SHOULD: 单方法 <= 50 行.

### 11) 日志规范

- MUST: 业务关键路径记录结构化日志(使用 `app.utils.structlog_config`).
- MUST: 日志字段遵循敏感数据约束, 参考 [[standards/backend/sensitive-data-handling|敏感数据处理]].

## 正反例

### 正例: Read Service

- 判定点:
  - Service 只做业务编排, 数据访问下沉到 Repository.
  - 支持注入 repository, 便于测试与替身.
- 长示例见: [[reference/examples/backend-layer-examples#Read Service|Services Read Service 示例(长示例)]]

### 正例: Write Service + Outcome

- 判定点:
  - 写操作通过 schema 校验后再落 Model, 冲突/业务失败用明确异常类型表达.
  - 以 outcome 承载写入结果, 避免返回裸 dict.
- 长示例见: [[reference/examples/backend-layer-examples#Write Service + Outcome|Services Write Service 示例(长示例)]]

### 反例: Service 直接依赖 request/Response

```python
from flask import request

class BadService:
    def do(self):
        # 反例: Service 不应解析 request, 更不应返回 Response
        return request.args.get("q")
```

## 门禁/检查方式

- 评审检查:
  - 是否存在在 Service 内返回 `Response` 或依赖 `flask.request`?
  - 是否存在在 Repository 内 `commit`?
  - 写操作事务边界是否遵循 [[standards/backend/write-operation-boundary]]?
- 自查命令(示例):

```bash
rg -n "from flask import request|flask\\.request" app/services
rg -n "db\\.session\\.commit\\(" app/repositories
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
- 2026-01-13: 将事务边界表述拆分为“提交点 vs 决策点”, 统一口径对齐 [[standards/backend/write-operation-boundary|写操作事务边界]].
