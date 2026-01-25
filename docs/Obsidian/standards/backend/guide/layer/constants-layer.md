---
title: Constants 常量层编写规范
aliases:
  - constants-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
enforcement: guide
created: 2026-01-09
updated: 2026-01-12
owner: WhaleFall Team
scope: "`app/core/constants/**` 下所有常量与枚举定义"
related:
  - "[[standards/backend/configuration-and-secrets]]"
  - "[[standards/backend/shared-kernel-standards]]"
---

# Constants 常量层编写规范

> [!note] 说明
> Constants 放不可变的业务常量与枚举. 环境相关或可变配置放 Settings, 参考 [[standards/backend/configuration-and-secrets|配置与密钥]].

## 目的

- 统一不可变常量的定义位置, 避免 magic number/string 分散在各层.
- 固化依赖方向, 保持 constants "纯净", 让其可被全局安全复用.
- 通过 `Final`/`Enum` 等方式明确不变性, 降低误用风险.

## 适用范围

- `app/core/constants/**` 下所有常量, 枚举, 静态映射.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Constants 只包含不可变值, 枚举, 静态映射.
- MUST NOT: 包含环境相关配置(应放 Settings).
- MUST NOT: 包含需要运行时计算的动态值(应放 utils 或 Service).
- MUST NOT: 引入业务层依赖.

### 2) 常量定义

- SHOULD: 使用 `typing.Final` 标记不可变.
- SHOULD: 常量命名使用 `UPPER_SNAKE_CASE`.

### 3) 枚举定义

- SHOULD: 使用 `Enum`/`StrEnum`(视 Python 版本)表达离散值集合.
- SHOULD: 枚举类使用 `PascalCase`, 枚举值使用 `UPPER_SNAKE_CASE`.
- MAY: 提供 `choices()` 便于表单渲染.

### 4) 静态映射

- SHOULD: 对配置项结构使用 `TypedDict` 描述.
- SHOULD: 同时提供列表与 `*_MAP` 索引映射, 兼顾渲染与查找.

### 5) 导出规范

- SHOULD: 在 `app/core/constants/__init__.py` 里集中导出常用常量, 并维护 `__all__`.

### 6) 依赖规则

允许依赖:

- MUST: 标准库 `typing`, `enum`
- MAY: `app.core.constants.*`(同层内部模块互相 import)

禁止依赖:

- MUST NOT: `app.(api|routes|tasks|services|repositories|models|forms|views|utils|settings|infra|schemas).*`
- MUST NOT: `app.core.types.*`, `app.core.exceptions`
- SHOULD NOT: 第三方库

## 正反例

### 正例: 简单常量

```python
"""状态常量."""

from typing import Final

DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 200
MIN_PAGE_SIZE: Final[int] = 1

STATUS_ACTIVE: Final[str] = "active"
STATUS_INACTIVE: Final[str] = "inactive"
STATUS_DELETED: Final[str] = "deleted"
```

### 正例: 枚举与 choices()

```python
from enum import Enum


class SyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(item.value, item.name) for item in cls]
```

### 正例: 静态映射 + 索引

```python
from typing import Final, TypedDict


class DatabaseTypeConfig(TypedDict):
    name: str
    display_name: str
    default_port: int


DATABASE_TYPES: Final[list[DatabaseTypeConfig]] = [
    {"name": "mysql", "display_name": "MySQL", "default_port": 3306},
    {"name": "postgresql", "display_name": "PostgreSQL", "default_port": 5432},
]

DATABASE_TYPE_MAP: Final[dict[str, DatabaseTypeConfig]] = {
    item["name"]: item for item in DATABASE_TYPES
}
```

### 反例: 把动态配置放到 constants

```python
import os

DATABASE_URL = os.getenv("DATABASE_URL")  # 反例: 环境配置应放 Settings
```

## 门禁/检查方式

- 评审检查:
  - constants 是否保持纯净(无 `app.*` 依赖)?
  - 是否把环境配置/运行时动态值误放进 constants?
- 自查命令(示例):

```bash
rg -n "from app\\." app/core/constants
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
