# Repository 仓储层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/repositories/` 目录下所有仓储类的编写规范

---

## 核心原则

**Repository = 数据访问 + Query 组装 + 无业务逻辑**

```python
# ✅ Repository 职责
- 封装数据库查询（Query 组装）
- 提供分页、筛选、排序
- 返回 Model 对象或原始数据
- 不包含业务逻辑

# ❌ Repository 禁止
- 业务规则判断
- 调用其他 Service
- 返回 HTTP Response
- 处理事务提交（由 Service 控制）
```

---

## 文件命名规范

| 命名模式 | 用途 | 示例 |
|---------|------|------|
| `{entity}_repository.py` | 单实体仓储 | `instances_repository.py` |
| `{domain}_repository.py` | 领域仓储 | `capacity_databases_repository.py` |
| `{function}_repository.py` | 功能仓储 | `filter_options_repository.py` |

---

## 类设计规范

### 基本结构

```python
"""实例仓储."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Query

from app import db
from app.models.instance import Instance
from app.types.listing import PaginatedResult

if TYPE_CHECKING:
    from app.types.instances import InstanceListFilters


class InstancesRepository:
    """实例查询仓储.

    职责:
    - 实例列表查询与筛选
    - 实例详情获取
    - 不包含业务逻辑

    """

    @staticmethod
    def get_instance(instance_id: int) -> Instance | None:
        """按 ID 获取实例."""
        return Instance.query.get(instance_id)

    @staticmethod
    def get_active_instance(instance_id: int) -> Instance | None:
        """获取未删除的实例."""
        return Instance.query.filter_by(
            id=instance_id,
            deleted_at=None,
        ).first()

    def list_instances(
        self,
        filters: InstanceListFilters,
    ) -> PaginatedResult[Instance]:
        """按筛选条件返回实例分页列表."""
        query = Instance.query.filter(Instance.deleted_at.is_(None))
        query = self._apply_filters(query, filters)
        query = self._apply_sorting(query, filters)

        total = query.count()
        items = query.offset(filters.offset).limit(filters.limit).all()

        return PaginatedResult(items=items, total=total)

    def _apply_filters(
        self,
        query: Query,
        filters: InstanceListFilters,
    ) -> Query:
        """应用筛选条件."""
        if filters.search:
            query = query.filter(Instance.name.ilike(f"%{filters.search}%"))
        if filters.db_type:
            query = query.filter(Instance.db_type == filters.db_type)
        return query

    def _apply_sorting(
        self,
        query: Query,
        filters: InstanceListFilters,
    ) -> Query:
        """应用排序."""
        if filters.sort_by == "name":
            return query.order_by(Instance.name.asc())
        return query.order_by(Instance.created_at.desc())
```

---

## 方法命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `get_` | 获取单个对象 | `get_instance()`, `get_by_id()` |
| `get_*_or_404` | 获取或抛 404 | `get_instance_or_404()` |
| `list_` | 获取列表 | `list_instances()`, `list_active()` |
| `fetch_` | 获取原始数据/聚合 | `fetch_statistics()`, `fetch_tags_map()` |
| `count_` | 计数查询 | `count_active()`, `count_by_type()` |
| `exists_` | 存在性检查 | `exists_by_name()` |
| `add` | 新增对象 | `add(instance)` |
| `delete` | 删除对象 | `delete(instance_id)` |

---

## 分页返回规范

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """分页结果."""
    items: list[T]
    total: int
    page: int = 1
    limit: int = 20

    @property
    def pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| `app.models.*` | 数据模型 |
| `app.types.*` | 类型定义 |
| `app` (db) | 数据库会话 |
| `sqlalchemy` | ORM 工具 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.services.*` | 服务层（反向依赖） |
| `app.routes.*` | 路由层 |
| `app.api.*` | API 层 |

---

## 事务处理

```python
# ✅ 正确：Repository 只 flush，不 commit
class InstancesRepository:
    def add(self, instance: Instance) -> None:
        """新增实例并 flush."""
        db.session.add(instance)
        db.session.flush()  # 获取 ID，但不提交

# ✅ 正确：Service 控制事务边界
class InstanceWriteService:
    def create(self, data: dict) -> Instance:
        with db.session.begin_nested():
            instance = Instance(**data)
            self._repository.add(instance)
        db.session.commit()  # Service 决定提交时机
        return instance
```

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 400 行 | 按功能拆分多个 Repository |
| 单类方法数 | 15 个 | 拆分为多个 Repository |
| 单方法行数 | 50 行 | 提取私有方法 |

---

## 目录结构

```
repositories/
├── __init__.py
├── instances_repository.py
├── credentials_repository.py
├── tags_repository.py
├── users_repository.py
├── capacity_databases_repository.py
├── capacity_instances_repository.py
├── ledgers/                    # 子目录（复杂业务）
│   ├── __init__.py
│   ├── accounts_ledger_repository.py
│   └── database_ledger_repository.py
└── common/                     # 通用查询工具（可选）
    └── query_builder.py
```

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
