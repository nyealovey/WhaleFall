# Constants 常量层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/constants/` 目录下所有常量的编写规范

---

## 核心原则

**Constants = 不可变值 + 枚举 + 配置映射**

```python
# ✅ Constants 职责
- 定义全局常量
- 定义枚举类型
- 定义静态配置映射
- 被各层共享使用

# ❌ Constants 禁止
- 动态值（应放 Settings）
- 依赖任何业务层
- 包含函数逻辑
```

---

## 目录结构

```
constants/
├── __init__.py           # 导出常用常量
├── database_types.py     # 数据库类型常量
├── status.py             # 状态常量
├── sync_constants.py     # 同步相关常量
├── scheduler_jobs.py     # 调度任务常量
└── permissions.py        # 权限相关常量
```

---

## 常量定义规范

### 简单常量

```python
"""状态常量."""

from typing import Final

# 使用 Final 标记不可变
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 200
MIN_PAGE_SIZE: Final[int] = 1

# 字符串常量
STATUS_ACTIVE: Final[str] = "active"
STATUS_INACTIVE: Final[str] = "inactive"
STATUS_DELETED: Final[str] = "deleted"
```

### 枚举类型

```python
"""同步状态枚举."""

from enum import Enum, auto


class SyncStatus(str, Enum):
    """同步状态."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """返回选项列表（用于表单）."""
        return [(item.value, item.name) for item in cls]


class SyncSessionStatus(str, Enum):
    """同步会话状态."""

    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
```

### 静态映射

```python
"""数据库类型配置."""

from typing import Final, TypedDict


class DatabaseTypeConfig(TypedDict):
    """数据库类型配置."""
    name: str
    display_name: str
    default_port: int
    icon: str
    color: str


DATABASE_TYPES: Final[list[DatabaseTypeConfig]] = [
    {
        "name": "mysql",
        "display_name": "MySQL",
        "default_port": 3306,
        "icon": "fa-dolphin",
        "color": "primary",
    },
    {
        "name": "postgresql",
        "display_name": "PostgreSQL",
        "default_port": 5432,
        "icon": "fa-database",
        "color": "info",
    },
]


# 快速查找映射
DATABASE_TYPE_MAP: Final[dict[str, DatabaseTypeConfig]] = {
    item["name"]: item for item in DATABASE_TYPES
}
```

---

## 导出规范

```python
# constants/__init__.py
"""常量定义."""

from app.constants.database_types import DATABASE_TYPES, DATABASE_TYPE_MAP
from app.constants.status import STATUS_ACTIVE, STATUS_INACTIVE
from app.constants.sync_constants import SyncStatus, SyncSessionStatus

__all__ = [
    "DATABASE_TYPES",
    "DATABASE_TYPE_MAP",
    "STATUS_ACTIVE",
    "STATUS_INACTIVE",
    "SyncStatus",
    "SyncSessionStatus",
]
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| 标准库 `typing` | 类型注解 |
| 标准库 `enum` | 枚举 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.*` | 任何应用模块 |
| 第三方库 | 保持纯净 |

---

## 命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 常量 | `UPPER_SNAKE_CASE` | `DEFAULT_PAGE_SIZE` |
| 枚举类 | `PascalCase` | `SyncStatus` |
| 枚举值 | `UPPER_SNAKE_CASE` | `COMPLETED` |
| 映射 | `*_MAP` | `DATABASE_TYPE_MAP` |

---

## Constants vs Settings

| 类型 | 来源 | 示例 |
|------|------|------|
| **Constants** | 代码中硬编码 | 数据库类型列表、状态枚举 |
| **Settings** | 环境变量/.env | 数据库连接字符串、API 密钥 |

```python
# ✅ Constants - 不变的业务配置
DATABASE_TYPES = [...]

# ✅ Settings - 环境相关配置
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
