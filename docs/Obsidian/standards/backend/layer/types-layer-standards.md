---
title: Types 类型定义层编写规范
aliases:
  - types-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-09
updated: 2026-01-11
owner: WhaleFall Team
scope: "`app/types/**` 下所有类型定义与协议"
related:
  - "[[standards/backend/request-payload-and-schema-validation]]"
---

# Types 类型定义层编写规范

> [!note] 说明
> Types 层承载类型别名, TypedDict, Protocol, dataclass 等. 其目标是让跨层数据结构与契约更明确, 而不是承载业务逻辑.

## 目的

- 提供稳定的类型契约, 降低跨层传参时的结构漂移与歧义.
- 让常用结构(分页结果, 筛选条件, DTO)可复用且易于静态检查.
- 通过 `Protocol` 支持依赖倒置与适配器抽象, 提升可测试性.

## 适用范围

- `app/types/**` 下所有 `.py` 类型定义文件.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: 只定义类型, 不写业务逻辑.
- MUST NOT: 访问数据库或依赖 `db.session`.
- MUST NOT: 依赖 `app.services.*`, `app.repositories.*`, `app.routes.*`, `app.api.*`.

### 2) TypedDict

- SHOULD: 用 `TypedDict` 描述结构化 dict(例如筛选条件, 统计指标, 轻量 DTO).
- SHOULD: 对可选字段使用 `total=False` 并在文档或字段名上体现默认值语义.

### 3) dataclass

- SHOULD: 用 dataclass 表达值对象与稳定返回结构(例如 `PaginatedResult`, `Outcome`).
- SHOULD: 对不可变值对象使用 `frozen=True`, 并优先启用 `slots=True`.

### 4) Protocol

- SHOULD: 用 `Protocol` 描述可替换依赖(适配器/客户端/扩展点).
- SHOULD: 对需要 runtime 检查的协议加 `@runtime_checkable`.

### 5) 类型别名

- SHOULD: 用 `TypeAlias` 表达可读性更强的类型别名(例如 `InstanceId`).

### 6) 导出规范

- SHOULD: `app/types/__init__.py` 只导出高频公共类型, 并维护 `__all__`.

### 7) 依赖规则

允许依赖:

- MUST: 标准库 `typing`, `dataclasses`, `collections.abc`
- MAY: `app.constants.*`(当类型需要引用常量值集合时)

禁止依赖:

- MUST NOT: `app.models.*`(包括 `TYPE_CHECKING` 分支), `app` 的 `db`
- MUST NOT: `app.services.*`, `app.repositories.*`, `app.routes.*`, `app.api.*`

补充说明:

- 如果需要表达 "某个 ORM 实体在上层会用到哪些字段/方法", MUST: 通过 `Protocol` 定义最小接口, 而不是在 types 中引用具体 model 类.

### 8) 代码规模限制

- SHOULD: 单文件 <= 200 行, 超出按业务域拆分.
- SHOULD: 单个 TypedDict 字段数 <= 15, 超出考虑拆分或嵌套结构.

## 正反例

### 正例: TypedDict

```python
from typing import TypedDict


class InstanceListFilters(TypedDict, total=False):
    page: int
    limit: int
    search: str
    db_type: str
    include_deleted: bool
```

### 正例: dataclass

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PaginatedResult(Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    limit: int = 20

    @property
    def pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit
```

### 正例: Protocol

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class DatabaseAdapter(Protocol):
    def connect(self) -> None: ...
    def execute(self, query: str) -> list[dict]: ...
    def close(self) -> None: ...
```

### 正例: 用 Protocol 替代对 model 的类型引用

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class SupportsCredentialListRow(Protocol):
    id: int
    name: str
    created_at: datetime | None

    def get_password_masked(self) -> str: ...


@dataclass(slots=True)
class CredentialListRowProjection:
    credential: SupportsCredentialListRow
    instance_count: int
```

### 反例: 在 types 里写业务逻辑或查库

```python
from app.models.instance import Instance


def list_instances():  # 反例: types 不应包含业务函数
    return Instance.query.all()
```

### 反例: 即使在 TYPE_CHECKING 中也不应引用 models

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.credential import Credential  # 反例: types 不允许依赖 models
```

## 门禁/检查方式

- 评审检查:
  - types 文件是否只包含类型定义?
  - 是否出现对 Model/db/Service/Repository 的依赖?
- 自查命令(示例):

```bash
rg -n "from app\\.(models|services|repositories|routes|api)\\.|db\\.session" app/types
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
- 2026-01-11: 明确禁止在 `TYPE_CHECKING` 中引用 models, 统一改用 `Protocol`/弱类型, 并补充示例.
