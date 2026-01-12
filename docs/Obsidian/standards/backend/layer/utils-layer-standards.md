---
title: Utils 工具层编写规范
aliases:
  - utils-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-09
updated: 2026-01-12
owner: WhaleFall Team
scope: "`app/utils/**` 下所有工具模块"
related:
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/shared-kernel-standards]]"
---

# Utils 工具层编写规范

> [!note] 说明
> Utils 目标是沉淀跨域复用的通用能力(纯函数, 装饰器, 中间件, 轻量工具类). 业务逻辑应留在 Service, 数据访问应留在 Repository.

## 目的

- 提供可复用的通用能力, 降低重复实现与口径漂移.
- 固化依赖边界, 避免工具模块反向依赖业务层导致循环引用与不可测试.
- 让工具模块具备清晰契约(输入/输出/异常), 便于单元测试与静态检查.

## 适用范围

- `app/utils/**` 下所有工具模块, 包括日志子模块, 装饰器, 响应工具, 时间/格式化/解析工具等.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Utils 以无状态纯函数或轻量工具类为主, 输入输出清晰, 无隐式副作用.
- MUST NOT: 包含业务规则(例如权限判定, 状态机, 跨实体编排).
- MUST NOT: 直接访问数据库或依赖 `db.session`.
- SHOULD: 当工具需要依赖外部状态(例如 app config)时, 通过显式参数注入或在上层组装.

> [!note]
> `app/utils/**` 同时包含两类代码：
> - **纯工具(shared-kernel-like)**：不依赖 Flask/DB/request context，可跨层复用（例如 `payload_converters/time_utils/version_parser`）。这类模块应尽量向 `app/core/**` 收敛，至少需要同时满足 [[standards/backend/shared-kernel-standards]] 的约束。
> - **边界工具**：与 HTTP/日志/安全/中间件强绑定（例如响应封套、请求上下文日志）。这类模块不属于 shared kernel，必须避免被 `app/core/**`、`app/core/constants/**`、`app/core/types/**` 反向依赖。

### 2) 模块组织(推荐)

```text
app/utils/
├── __init__.py
├── logging/
│   ├── __init__.py
│   ├── context_vars.py
│   ├── error_adapter.py
│   └── handlers.py
├── decorators.py
├── time_utils.py
├── response_utils.py
├── sensitive_data.py
└── {function}_utils.py
```

### 3) 异常处理

- MUST: 默认情况下不要吞异常. 当函数语义明确是 "best-effort" 时才允许返回兜底值, 且必须在 docstring 写清楚.
- MUST: 记录日志时遵循 [[standards/backend/sensitive-data-handling|敏感数据处理]] 约束.
- SHOULD: 只捕获可预期的异常类型(例如 `ValueError`, `TypeError`), 避免 `except Exception` 造成误吞.

### 4) 类型注解

- MUST: 对公共工具函数提供完整类型注解.
- SHOULD: 使用 `from __future__ import annotations` 简化类型引用并减少循环依赖风险.
- SHOULD: 装饰器使用 `ParamSpec`/`TypeVar` 保持签名.

### 5) 命名规范

函数/方法前缀建议:

| 前缀/模式 | 用途 | 示例 |
|---|---|---|
| `parse_` | 解析转换 | `parse_datetime()`, `parse_int_safe()` |
| `format_` | 格式化输出 | `format_china_time()`, `format_bytes()` |
| `validate_` | 校验检查 | `validate_email()`, `validate_csrf()` |
| `is_`/`has_` | 布尔判断 | `is_today()`, `has_permission()` |
| `to_` | 类型转换 | `to_china()`, `to_json_serializable()` |
| `build_` | 构建对象 | `build_query()`, `build_response()` |
| `sanitize_` | 清理净化 | `sanitize_input()`, `sanitize_filename()` |

文件命名建议:

| 命名模式 | 用途 | 示例 |
|---|---|---|
| `{function}_utils.py` | 功能工具集 | `time_utils.py`, `cache_utils.py` |
| `{noun}.py` | 单一职责模块 | `decorators.py` |
| `{adjective}_{noun}.py` | 特定类型 | `safe_query_builder.py`, `sensitive_data.py` |

### 6) 常量与单例

- SHOULD: 运行时不变的派生常量可以放在 utils 模块内, 但源常量应来自 `app/core/constants/**`.
- MAY: 提供模块级单例实例以便导入使用, 但必须保持无状态或只读.

### 7) 依赖规则

允许依赖:

- MAY: `app.core.constants.*`
- MAY: `app.core.exceptions`(仅用于抛出明确异常类型)
- MUST: 标准库
- MAY: 第三方库(例如 `structlog`, `werkzeug`)

禁止依赖:

- MUST NOT: `app.models.*`, `app.services.*`, `app.repositories.*`, `app.routes.*`, `app.api.*`
- MUST NOT: `app` 的 `db`

### 8) 代码规模限制

- SHOULD: 单文件 <= 400 行.
- SHOULD: 单类方法数 <= 20 个.
- SHOULD: 单函数 <= 30 行.

### 9) 测试要求

- SHOULD: 对有非平凡逻辑的工具函数补充 `tests/unit/**` 单测.
- SHOULD: 测试覆盖边界条件(空值, 非法输入, 时区等).

## 正反例

### 正例: 轻量工具类 + 模块级实例

```python
from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

CHINA_TZ = ZoneInfo("Asia/Shanghai")


class TimeUtils:
    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def now_china() -> datetime:
        return datetime.now(CHINA_TZ)


time_utils = TimeUtils()
```

### 正例: 装饰器签名保持

```python
from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def admin_required(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    def decorated(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)

    return decorated
```

### 正例: best-effort 解析函数(明确兜底语义)

```python
import structlog

LOGGER = structlog.get_logger("system")


def parse_int_safe(value: str | None) -> int | None:
    """Best-effort: 解析失败返回 None, 并记录 warning."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        LOGGER.warning("parse_int_safe failed", error=str(exc))
        return None
```

### 反例: 静默吞异常

```python
def bad():
    try:
        return do_something()
    except Exception:
        return None  # 反例: 无语义说明且吞掉所有异常
```

## 门禁/检查方式

- 评审检查:
  - utils 是否保持无业务/无数据库依赖?
  - 异常兜底是否有明确语义与 docstring, 且避免静默吞异常?
  - 是否遵循敏感数据与错误字段标准?
- 自查命令(示例):

```bash
rg -n "from app\\.(models|services|repositories|routes|api)\\.|db\\.session" app/utils
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
