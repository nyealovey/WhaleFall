# Types 类型定义层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/types/` 目录下所有类型定义的编写规范

---

## 核心原则

**Types = 类型别名 + TypedDict + Protocol + dataclass**

```python
# ✅ Types 职责
- 定义类型别名
- 定义 TypedDict（结构化字典）
- 定义 Protocol（接口契约）
- 定义通用 dataclass
- 被各层共享使用

# ❌ Types 禁止
- 业务逻辑
- 数据库操作
- 依赖 Service/Repository/Routes
```

---

## 目录结构

```
types/
├── __init__.py
├── accounts.py          # 账户相关类型
├── instances.py         # 实例相关类型
├── classification.py    # 分类相关类型
├── sync.py              # 同步相关类型
├── listing.py           # 列表/分页类型
├── routes.py            # 路由相关类型
├── request_payload.py   # 请求负载类型
├── converters.py        # 类型转换工具
├── extensions.py        # 扩展点类型
└── query_protocols.py   # 查询协议
```

---

## TypedDict 规范

用于定义结构化字典（如筛选条件、API 响应）：

```python
"""实例相关类型."""

from __future__ import annotations

from typing import TypedDict


class InstanceListFilters(TypedDict, total=False):
    """实例列表筛选条件."""

    page: int
    limit: int
    search: str
    db_type: str
    status: str
    include_deleted: bool
    tags: list[str]
    sort_by: str
    sort_order: str


class InstanceListMetrics(TypedDict):
    """实例列表指标."""

    database_count: int
    account_count: int
    last_sync_at: str | None
```

---

## dataclass 规范

用于定义值对象（不可变数据结构）：

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PaginatedResult(Generic[T]):
    """分页结果."""

    items: list[T]
    total: int
    page: int = 1
    limit: int = 20

    @property
    def pages(self) -> int:
        """总页数."""
        return (self.total + self.limit - 1) // self.limit

    @property
    def has_next(self) -> bool:
        """是否有下一页."""
        return self.page < self.pages
```

---

## Protocol 规范

用于定义接口契约（依赖倒置）：

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class DatabaseAdapter(Protocol):
    """数据库适配器协议."""

    def connect(self) -> None:
        """建立连接."""
        ...

    def execute(self, query: str) -> list[dict]:
        """执行查询."""
        ...

    def close(self) -> None:
        """关闭连接."""
        ...


# 使用
def run_query(adapter: DatabaseAdapter, query: str) -> list[dict]:
    adapter.connect()
    try:
        return adapter.execute(query)
    finally:
        adapter.close()
```

---

## 类型别名规范

```python
from typing import TypeAlias

# 简单别名
InstanceId: TypeAlias = int
DatabaseType: TypeAlias = str

# 复杂别名
TagsMap: TypeAlias = dict[int, list[dict[str, str]]]
FilterOptions: TypeAlias = list[dict[str, str | int]]
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| 标准库 `typing` | 类型工具 |
| `dataclasses` | dataclass |
| `app.constants.*` | 常量（可选） |

| 禁止依赖 | 说明 |
|---------|------|
| `app.models.*` | 数据模型 |
| `app.services.*` | 服务层 |
| `app.repositories.*` | 仓储层 |
| `app.routes.*` | 路由层 |
| `app` (db) | 数据库 |

---

## 命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| TypedDict | `{Entity}{Purpose}` | `InstanceListFilters`, `AccountSummary` |
| dataclass | `{Entity}{Type}` | `PaginatedResult`, `SyncStats` |
| Protocol | `{Capability}Protocol` 或 `{Role}` | `DatabaseAdapter`, `Validator` |
| 类型别名 | `{Entity}Id` 或描述性名称 | `InstanceId`, `TagsMap` |

---

## 导出规范

```python
# types/__init__.py
"""类型定义."""

from app.types.accounts import AccountFilters, AccountSummary
from app.types.instances import InstanceListFilters, InstanceListMetrics
from app.types.listing import PaginatedResult

__all__ = [
    "AccountFilters",
    "AccountSummary",
    "InstanceListFilters",
    "InstanceListMetrics",
    "PaginatedResult",
]
```

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 200 行 | 按业务域拆分 |
| 单 TypedDict 字段数 | 15 个 | 拆分为多个 TypedDict |

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
