# Utils 工具层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/utils/` 目录下所有工具模块的编写规范

---

## 核心原则

**Utils = 纯函数 + 无状态 + 可复用**

```python
# ✅ Utils 职责
- 提供无状态的纯函数或工具类
- 封装通用算法和数据处理
- 提供装饰器和中间件
- 不依赖业务模型和数据库

# ❌ Utils 禁止
- 包含业务逻辑
- 直接查询数据库
- 依赖 Service/Repository
- 维护全局可变状态
```

---

## 目录结构

```
utils/
├── __init__.py
├── logging/                      # 日志子模块
│   ├── __init__.py
│   ├── context_vars.py           # 上下文变量
│   ├── error_adapter.py          # 错误适配
│   ├── handlers.py               # 日志处理器
│   └── queue_worker.py           # 队列工作器
├── decorators.py                 # 装饰器集合
├── time_utils.py                 # 时间处理
├── cache_utils.py                # 缓存工具
├── pagination_utils.py           # 分页工具
├── password_crypto_utils.py      # 密码加密
├── query_filter_utils.py         # 查询过滤
├── response_utils.py             # 响应工具
├── safe_query_builder.py         # 安全查询构建
├── sensitive_data.py             # 敏感数据处理
├── structlog_config.py           # 日志配置
└── {function}_utils.py           # 其他功能工具
```

---

## 工具分类规范

### 纯函数工具

```python
"""时间处理工具模块.

基于 Python 3.9+ 的 zoneinfo 模块,提供一致的时间处理功能.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

CHINA_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = ZoneInfo("UTC")


class TimeUtils:
    """统一时间处理工具类."""

    @staticmethod
    def now() -> datetime:
        """获取当前 UTC 时间."""
        return datetime.now(UTC)

    @staticmethod
    def now_china() -> datetime:
        """获取当前中国时间."""
        return datetime.now(CHINA_TZ)

    @staticmethod
    def to_china(dt: str | date | datetime | None) -> datetime | None:
        """将时间转换为中国时区."""
        if not dt:
            return None
        # 转换逻辑...


# 提供单例实例便于导入使用
time_utils = TimeUtils()
```

### 装饰器工具

```python
"""装饰器工具模块."""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from flask import request

P = ParamSpec("P")
T = TypeVar("T")


def admin_required(func: Callable[P, T]) -> Callable[P, T]:
    """确保被装饰函数仅允许管理员访问.

    Args:
        func: 被装饰的视图函数.

    Returns:
        装饰后的函数.

    Raises:
        AuthenticationError: 用户未认证.
        AuthorizationError: 权限不足.

    """

    @wraps(func)
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> T:
        # 权限检查逻辑...
        return func(*args, **kwargs)

    return decorated_function


def require_csrf(func: Callable[P, T]) -> Callable[P, T]:
    """统一的 CSRF 校验装饰器."""

    @wraps(func)
    def decorated_function(*args: P.args, **kwargs: P.kwargs) -> T:
        # CSRF 校验逻辑...
        return func(*args, **kwargs)

    return decorated_function
```

### 中间件工具

```python
"""代理修复中间件."""

from werkzeug.middleware.proxy_fix import ProxyFix


def create_proxy_fix_middleware(app, x_for=1, x_proto=1):
    """创建代理修复中间件.

    Args:
        app: Flask 应用实例.
        x_for: X-Forwarded-For 头信任层数.
        x_proto: X-Forwarded-Proto 头信任层数.

    Returns:
        包装后的 WSGI 应用.

    """
    return ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto)
```

---

## 方法命名规范

| 前缀/模式 | 用途 | 示例 |
|----------|------|------|
| `parse_` | 解析转换 | `parse_datetime()`, `parse_int_safe()` |
| `format_` | 格式化输出 | `format_china_time()`, `format_bytes()` |
| `validate_` | 校验检查 | `validate_email()`, `validate_csrf()` |
| `is_` / `has_` | 布尔判断 | `is_today()`, `has_permission()` |
| `to_` | 类型转换 | `to_china()`, `to_json_serializable()` |
| `get_` | 获取计算值 | `get_relative_time()`, `get_time_range()` |
| `build_` | 构建对象 | `build_query()`, `build_response()` |
| `sanitize_` | 清理净化 | `sanitize_input()`, `sanitize_filename()` |
| `encrypt_` / `decrypt_` | 加解密 | `encrypt_password()`, `decrypt_data()` |
| `hash_` | 哈希计算 | `hash_password()`, `hash_file()` |

---

## 文件命名规范

| 命名模式 | 用途 | 示例 |
|---------|------|------|
| `{function}_utils.py` | 功能工具集 | `time_utils.py`, `cache_utils.py` |
| `{domain}_utils.py` | 领域工具 | `query_filter_utils.py` |
| `{noun}.py` | 单一职责模块 | `decorators.py`, `rate_limiter.py` |
| `{adjective}_{noun}.py` | 特定类型 | `safe_query_builder.py`, `sensitive_data.py` |

---

## 常量定义规范

```python
"""时间工具模块."""

from app.constants import TimeConstants

# 派生常量（基于 constants 模块）
MINUTES_PER_HOUR = TimeConstants.ONE_HOUR // TimeConstants.ONE_MINUTE
HOURS_PER_DAY = TimeConstants.ONE_DAY // TimeConstants.ONE_HOUR


# 模块内部常量类
class TimeFormats:
    """时间格式常量."""

    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
```

---

## 单例模式规范

```python
"""提供模块级单例实例."""


class TimeUtils:
    """时间处理工具类."""

    @staticmethod
    def now() -> datetime:
        """获取当前 UTC 时间."""
        return datetime.now(UTC)


# 模块级单例，便于导入使用
time_utils = TimeUtils()


# 使用方式
from app.utils.time_utils import time_utils

now = time_utils.now()
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| `app.constants.*` | 常量定义 |
| `app.errors` | 异常类（仅用于抛出） |
| 标准库 | `datetime`, `functools`, `typing` 等 |
| 第三方库 | `structlog`, `werkzeug` 等 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.models.*` | 数据模型 |
| `app.services.*` | 服务层 |
| `app.repositories.*` | 仓储层 |
| `app.routes.*` | 路由层 |
| `app.api.*` | API 层 |
| `app` (db) | 数据库会话 |

---

## 异常处理规范

```python
"""工具函数异常处理."""

import structlog

LOGGER = structlog.get_logger("system")


class TimeUtils:
    @staticmethod
    def to_china(dt: str | date | datetime | None) -> datetime | None:
        """将时间转换为中国时区.

        Args:
            dt: 待转换的时间.

        Returns:
            转换后的时间,转换失败时返回 None.

        """
        if not dt:
            return None

        try:
            # 转换逻辑...
            return result
        except (ValueError, TypeError) as e:
            # 记录警告但不抛出，返回安全默认值
            LOGGER.warning("时间转换错误", error=str(e))
            return None
```

---

## 类型注解规范

```python
"""完整的类型注解示例."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, Protocol, TypeVar, overload

P = ParamSpec("P")
T = TypeVar("T")


class PermissionUser(Protocol):
    """用于描述具备角色信息的用户协议."""

    is_authenticated: bool
    role: str


def has_permission(user: PermissionUser | None, permission: str) -> bool:
    """检查用户是否具备指定权限."""
    if not user or not user.is_authenticated:
        return False
    # 检查逻辑...


@overload
def view_required(
    func: Callable[P, T],
    *,
    permission: str = "view",
) -> Callable[P, T]: ...


@overload
def view_required(
    func: None = None,
    *,
    permission: str = "view",
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...


def view_required(
    func: Callable[P, T] | None = None,
    *,
    permission: str = "view",
) -> Callable[[Callable[P, T]], Callable[P, T]] | Callable[P, T]:
    """支持多种调用方式的装饰器."""
    ...
```

---

## 文档字符串规范

```python
def format_china_time(
    dt: str | date | datetime | None,
    format_str: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """格式化中国时间显示.

    将输入时间转换为中国时区并按指定格式输出.

    Args:
        dt: 待格式化的时间,支持字符串、date 或 datetime.
        format_str: 时间格式字符串,默认为 '%Y-%m-%d %H:%M:%S'.

    Returns:
        格式化后的时间字符串,失败时返回 '-'.

    Examples:
        >>> format_china_time(datetime.now(UTC))
        '2026-01-09 15:30:00'
        >>> format_china_time(None)
        '-'

    """
    ...
```

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 400 行 | 按功能拆分多个模块 |
| 单类方法数 | 20 个 | 拆分为多个工具类 |
| 单函数行数 | 30 行 | 提取辅助函数 |

---

## 测试要求

```python
# tests/unit/utils/test_time_utils.py

import pytest
from datetime import datetime, UTC
from app.utils.time_utils import time_utils


class TestTimeUtils:
    """时间工具测试."""

    def test_now_returns_utc(self):
        """now() 应返回 UTC 时间."""
        result = time_utils.now()
        assert result.tzinfo is not None

    def test_to_china_with_none(self):
        """to_china(None) 应返回 None."""
        assert time_utils.to_china(None) is None

    def test_format_china_time_default_format(self):
        """format_china_time() 应使用默认格式."""
        dt = datetime(2026, 1, 9, 7, 30, 0, tzinfo=UTC)
        result = time_utils.format_china_time(dt)
        assert result == "2026-01-09 15:30:00"
```

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
