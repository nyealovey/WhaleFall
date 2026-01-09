# Models 数据模型层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/models/` 目录下所有数据模型的编写规范

---

## 核心原则

**Models = 数据结构 + ORM 映射 + 基础方法**

```python
# ✅ Models 职责
- 定义数据库表结构
- ORM 字段映射
- 基础数据转换（to_dict）
- 简单的查询快捷方法

# ❌ Models 禁止
- 业务逻辑
- 复杂查询（应放 Repository）
- 依赖 Service/Repository/Routes
- HTTP 响应处理
```

---

## 文件命名规范

| 命名模式 | 示例 |
|---------|------|
| `{entity}.py` | `instance.py`, `user.py`, `tag.py` |
| `{entity}_{type}.py` | `database_size_stat.py`, `account_permission.py` |

---

## 模型编写模板

```python
"""实例模型."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from datetime import datetime


class Instance(db.Model):
    """数据库实例模型.

    Attributes:
        id: 主键.
        name: 实例名称，唯一.
        db_type: 数据库类型.
        host: 主机地址.
        port: 端口号.
        is_active: 是否激活.
        created_at: 创建时间.
        updated_at: 更新时间.
        deleted_at: 删除时间（软删除）.

    """

    __tablename__ = "instances"

    # 主键
    id = db.Column(db.Integer, primary_key=True)

    # 基础字段
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    db_type = db.Column(db.String(50), nullable=False, index=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)

    # 状态字段
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # 时间戳
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=time_utils.now,
        onupdate=time_utils.now,
    )
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # 外键
    credential_id = db.Column(
        db.Integer,
        db.ForeignKey("credentials.id"),
        nullable=True,
    )

    # 关系
    credential = db.relationship("Credential", backref="instances")
    tags = db.relationship(
        "Tag",
        secondary="instance_tags",
        back_populates="instances",
        lazy="dynamic",
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "id": self.id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """调试字符串."""
        return f"<Instance {self.name}>"

    # 类型注解（TYPE_CHECKING）
    if TYPE_CHECKING:
        id: int
        name: str
        db_type: str
        host: str
        port: int
        is_active: bool
        created_at: datetime
        updated_at: datetime
        deleted_at: datetime | None
```

---

## 字段规范

### 命名规范

| 字段类型 | 命名规则 | 示例 |
|---------|---------|------|
| 主键 | `id` | `id` |
| 外键 | `{entity}_id` | `credential_id`, `instance_id` |
| 布尔 | `is_*` / `has_*` | `is_active`, `has_permission` |
| 时间戳 | `*_at` | `created_at`, `deleted_at` |
| 计数 | `*_count` | `sync_count`, `login_count` |

### 必备字段

```python
# 每个模型都应有的字段
created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
updated_at = db.Column(
    db.DateTime(timezone=True),
    default=time_utils.now,
    onupdate=time_utils.now,
)

# 支持软删除的模型
deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
```

---

## 关系定义规范

```python
# 一对多（Instance 有多个 Account）
class Instance(db.Model):
    accounts = db.relationship(
        "InstanceAccount",
        back_populates="instance",
        cascade="all, delete-orphan",  # 级联删除
    )

class InstanceAccount(db.Model):
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"))
    instance = db.relationship("Instance", back_populates="accounts")


# 多对多（Instance ↔ Tag）
instance_tags = db.Table(
    "instance_tags",
    db.Column("instance_id", db.Integer, db.ForeignKey("instances.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id")),
)

class Instance(db.Model):
    tags = db.relationship(
        "Tag",
        secondary=instance_tags,
        back_populates="instances",
        lazy="dynamic",
    )
```

---

## to_dict 规范

```python
def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
    """转换为字典.

    Args:
        include_sensitive: 是否包含敏感信息.

    Returns:
        字典格式数据.

    """
    data = {
        "id": self.id,
        "name": self.name,
        "created_at": self.created_at.isoformat() if self.created_at else None,
    }

    # 可选：包含关系数据
    if hasattr(self, "tags") and self.tags is not None:
        data["tags"] = [tag.to_dict() for tag in self.tags]

    # 可选：敏感信息
    if include_sensitive and self.credential:
        data["credential"] = self.credential.to_dict()

    return data
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| `app` (db) | 数据库实例 |
| `app.utils.time_utils` | 时间工具 |
| 其他 `app.models.*` | 关系定义 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.services.*` | 服务层 |
| `app.repositories.*` | 仓储层 |
| `app.routes.*` | 路由层 |
| `app.api.*` | API 层 |

---

## `__init__.py` 导出

```python
"""数据模型."""

from app.models.credential import Credential
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.tag import Tag
from app.models.user import User

__all__ = [
    "Credential",
    "Instance",
    "InstanceAccount",
    "Tag",
    "User",
]
```

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 300 行 | 拆分关系/方法到 mixin |
| 单模型字段数 | 20 个 | 考虑拆分表 |
| to_dict 行数 | 30 行 | 提取辅助方法 |

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
