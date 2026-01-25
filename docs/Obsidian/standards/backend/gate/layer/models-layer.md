---
title: Models 数据模型层编写规范
aliases:
  - models-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
enforcement: gate
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: "`app/models/**` 下所有 SQLAlchemy 模型"
related:
  - "[[standards/backend/database-migrations]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/layer/repository-layer-standards]]"
  - "[[standards/backend/layer/services-layer-standards]]"
---

# Models 数据模型层编写规范

> [!note] 说明
> Model 负责 ORM 映射与关系定义. 复杂查询与数据访问细节放在 Repository. 业务编排与事务边界放在 Service.

## 目的

- 固化 ORM 映射的最小职责集合, 降低 Model 巨型化与业务逻辑侵入的风险.
- 统一字段命名与基础字段约束, 提升迁移与排障效率.
- 统一 `to_dict` 等基础转换口径, 避免在上层随意序列化引入敏感字段泄露.

## 适用范围

- `app/models/**` 下所有 SQLAlchemy 模型类, 以及模型间关系定义.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Model 只负责表结构定义, ORM 映射, 关系定义, 最小的基础方法(例如 `__repr__`, `to_dict`).
- MUST NOT: 在 Model 中编写业务逻辑(状态机, 权限, 跨实体聚合等).
- SHOULD: 复杂查询逻辑放在 Repository, 避免在 Model 上堆叠大量 `@classmethod` 查询方法.

### 2) 文件命名

| 命名模式 | 示例 |
|---|---|
| `{entity}.py` | `instance.py`, `user.py`, `tag.py` |
| `{entity}_{type}.py` | `database_size_stat.py`, `account_permission.py` |

### 3) 字段命名与通用字段

字段命名建议:

| 字段类型 | 命名规则 | 示例 |
|---|---|---|
| 主键 | `id` | `id` |
| 外键 | `{entity}_id` | `credential_id`, `instance_id` |
| 布尔 | `is_*`/`has_*` | `is_active`, `has_permission` |
| 时间戳 | `*_at` | `created_at`, `deleted_at` |
| 计数 | `*_count` | `sync_count`, `login_count` |

通用字段建议:

- SHOULD: 每个模型包含 `created_at`/`updated_at`.
- MAY: 支持软删除的模型包含 `deleted_at`.

### 4) 关系定义

- SHOULD: 明确 `back_populates`/`backref` 并在需要时配置 `cascade`.
- MUST: 避免在 `to_dict` 里隐式触发大量 lazy load.

### 5) 类型注解

- SHOULD: 使用 `TYPE_CHECKING` 或 SQLAlchemy 兼容方式提供静态类型信息, 避免运行时循环依赖.

### 6) `to_dict` 规范

- MUST: `to_dict` 默认不得包含敏感信息, 敏感字段受 [[standards/backend/sensitive-data-handling|敏感数据处理]] 约束.
- SHOULD: `to_dict` 支持 `include_sensitive: bool = False` 之类的显式开关, 且默认关闭.
- SHOULD: `to_dict` 控制规模(<= 30 行), 超出则拆分辅助函数或使用 DTO 转换放在 Service.

### 7) 依赖规则

允许依赖:

- MUST: `app` 的 `db`
- MAY: `app.utils.time_utils` 等基础工具
- MAY: 其他 `app.models.*`(仅用于关系定义)

禁止依赖:

- MUST NOT: `app.services.*`
- MUST NOT: `app.repositories.*`
- MUST NOT: `app.routes.*`, `app.api.*`

### 8) 代码规模限制

- SHOULD: 单文件 <= 300 行.
- SHOULD: 单模型字段数 <= 20 个, 超出需要评估拆表或抽象.
- SHOULD: `to_dict` <= 30 行.

## 正反例

### 正例: 模型结构

- 判定点:
  - Model 只负责字段/关系/最小方法, 不依赖 `services/repositories/routes/api`.
  - 时间字段统一使用 `time_utils.now`, 避免散落 `datetime.now`.
  - `to_dict` 默认不输出敏感字段, 通过显式开关控制.
- 长示例见: [[reference/examples/backend-layer-examples#模型结构|Models Layer 模型结构(长示例)]]

### 反例: 在 Model 中堆业务逻辑

```python
class BadModel(db.Model):
    def can_sync(self, user) -> bool:
        # 反例: 权限/业务规则不应放在 Model
        return user.is_admin and self.status != "deleted"
```

## 门禁/检查方式

- 评审检查:
  - Model 是否只包含 ORM 映射与最小方法?
  - 是否把复杂查询放到了 Repository?
  - `to_dict` 是否默认不包含敏感信息, 且无隐式大规模 lazy load?
- 自查命令(示例):

```bash
rg -n "from app\\.services\\.|from app\\.repositories\\." app/models
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
