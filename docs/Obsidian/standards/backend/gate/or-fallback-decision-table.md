---
title: `or`/truthy 兜底决策表（何时允许，何时必须替换）
aliases:
  - or-fallback-decision-table
tags:
  - standards
  - standards/backend
status: active
enforcement: gate
created: 2026-01-16
updated: 2026-01-16
owner: WhaleFall Team
scope: "Python `or`/truthy 兜底的使用边界；兼容/默认值/迁移/规范化的落点决策"
related:
  - "[[standards/backend/gate/layer/schemas-layer]]"
  - "[[standards/backend/gate/request-payload-and-schema-validation]]"
  - "[[standards/backend/gate/internal-data-contract-and-versioning]]"
  - "[[standards/backend/design/compatibility-and-deprecation]]"
  - "[[standards/backend/guide/resilience-and-fallback]]"
---

# `or`/truthy 兜底决策表（何时允许，何时必须替换）

## 1. 目的

- 解决“看到 `or` 兜底链就想改/不敢改”的评审分歧：把决策标准显式化、可执行化。
- 把 **默认值/兼容/迁移/规范化(canonicalization)** 从业务层散落的 `or` 链收敛到单入口（schema/adapter），降低语义漂移风险。

> [!note]
> 本表讨论的是 **“把 `or` 当默认值/兼容兜底”** 的用法；`if a or b:` 这类纯布尔逻辑不在本表约束范围内（但仍建议保持可读性）。

## 2. 核心判据：三类“空”必须区分

在写路径/读 internal contract 时，必须能区分：

- **缺失**：key 不存在（由 schema 默认值处理）。
- **显式提供但为空**：例如 `""`、`[]`、`{}`（可能代表“清空”或“合法空值”）。
- **None**：通常代表“未知/缺省”（是否等价于缺失取决于字段定义）。

## 3. 决策表

| 场景 | 典型写法 | 允许位置 | 是否允许 | 推荐替代 |
|---|---|---|---|---|
| 语义默认值（可能出现合法 falsy） | `value or default` | 任意 | ❌ | `default if value is None else value`；或交给 Pydantic 默认值/`default_factory` |
| 字段 alias/迁移（新旧字段名） | `data.get("new") or data.get("old")` | service/repo/api | ❌ | schema: `Field(validation_alias=AliasChoices("new","old"))` 或 `model_validator(mode="before")` |
| “空白视为缺省”的规范化 | `cleaned = raw.strip(); cleaned or None` | schema/adapter | ✅（需单测） | 保留，但必须注释说明语义；并补单测覆盖空白/缺失/合法空串策略 |
| list/dict 默认值（缺失 vs 显式空） | `payload.get("tags") or []` | 任意 | ❌ | schema: `Field(default_factory=list)`；update 场景用 `model_fields_set` 判断是否显式提供 |
| internal contract 未知版本 | `if version != 4: return {}` | 任意 | ❌ | adapter 返回 `InternalContractResult(ok=false, error_code=...)` 或 fail-fast 抛异常；禁止 `{}`/`[]` silent fallback |
| cache/外部依赖失败兜底 | `except: return default` | 任意 | ❌（silent） | 必须记录 `fallback=true` 与 `fallback_reason`；必要时返回显式错误结果结构（见 resilience 标准） |

## 4. 推荐替代写法（可直接复制）

### 4.1 “None 才兜底”（避免覆盖合法 falsy）

```python
value = payload.get("limit")
resolved = 100 if value is None else value
```

### 4.2 “缺失才兜底”（保留显式空）

```python
if "tags" not in payload:
    tags = []
else:
    tags = payload["tags"]
```

### 4.3 写路径：默认值/alias/迁移下沉到 schema（Pydantic v2）

```python
from pydantic import AliasChoices, Field

from app.schemas.base import PayloadSchema


class ExamplePayload(PayloadSchema):
    # 新字段优先，其次旧字段（兼容迁移）
    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "legacy_name"))

    # 缺失 -> 默认；显式传 0 会保留 0
    limit: int = 100

    # list 默认必须用 default_factory
    tags: list[str] = Field(default_factory=list)
```

### 4.4 update/patch：用 `model_fields_set` 区分“缺失”与“显式空”

```python
payload = validate_or_raise(ExamplePayload, sanitized)

if "tags" in payload.model_fields_set:
    # tags 被显式提供：允许 [] 表示“清空”
    apply_tags(payload.tags)
```

## 5. 执行建议（评审口径）

- 看到 `data.get("new") or data.get("old")`：一律视为“兼容逻辑落点错误”，迁移到 schema/adapter。
- 看到 `x or []/{}`：先问“显式空是否有语义（清空/合法空）”；如果有，必须改为缺失判定或 schema 默认 + `model_fields_set`。
- internal contract：未知版本必须显式失败（fail-fast 或 `InternalContractResult(ok=false, ...)`），禁止 silent fallback。

