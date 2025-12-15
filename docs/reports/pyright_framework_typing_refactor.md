# 框架扩展类型声明重构指引 (针对 reportAttributeAccessIssue / reportMissingImports)

## 背景与目标
- 当前 Pyright 报告中 `reportAttributeAccessIssue` 达 321 条，核心由 Flask 实例/扩展的动态属性引起，如 `app.enhanced_error_handler`、`login_manager.remember_cookie_duration` 等。
- `reportMissingImports` 主要来自路径未收录或第三方 stub 缺失，导致 IDE/CI 无法解析模块。
- 目标：通过显式类型包装与配置补全，消除上述规则的告警，为后续重构和自动补全打下基线。

## 实施步骤（推荐顺序）
1) **建立统一的扩展类型协议**
   - 新增文件 `app/types/extensions.py`（集中管理 Protocol/TypeAlias，符合仓库类型治理要求）。
   - 定义错误处理器签名：
     - `EnhancedErrorHandler = Callable[[Exception], tuple[dict[str, object], int]]`（返回统一错误响应与状态码）。
   - 定义自定义 Flask 协议：
     ```python
     class WhaleFallFlask(Flask, Protocol):
         enhanced_error_handler: EnhancedErrorHandler
         cache: Cache  # 如后续需要直接在 app 上挂载缓存实例
     ```
     - 如有其他在运行期挂载到 `app` 的属性（例如 `scheduler`、`rate_limiter`），在同一协议中显式列出，避免散落 cast。
   - 定义登录管理器协议：
     ```python
     class WhaleFallLoginManager(LoginManager, Protocol):
         login_view: str | None
         login_message: str
         login_message_category: str
         session_protection: str | None
         remember_cookie_duration: int | float | timedelta
         remember_cookie_secure: bool
         remember_cookie_httponly: bool
     ```
     - 按实际使用的属性补齐类型，避免下一轮新增属性再触发告警。

2) **在初始化处应用显式 cast**
   - `app/__init__.py` 中的创建与扩展初始化位置：
     - 将 `app = Flask(__name__)` 改为 `app: WhaleFallFlask = cast(WhaleFallFlask, Flask(__name__))`。
     - 将全局 `login_manager = LoginManager()` 改为显式类型：`login_manager: WhaleFallLoginManager = cast(WhaleFallLoginManager, LoginManager())`。
   - 在使用 `current_app` 的模块：
     ```python
     from flask import current_app
     from app.types.extensions import WhaleFallFlask
     app_ctx = typing.cast(WhaleFallFlask, current_app)
     ```
     - 保持局部变量名一致，避免重复 cast；下游直接使用 `app_ctx.enhanced_error_handler` 等属性。

3) **路径与依赖补全（reportMissingImports）**
   - 更新 `pyrightconfig.json`：
     - 在 `executionEnvironments[0].extraPaths` 中补充 `"scripts"`、`"tests"`（当前仅有 `app`）。
     - 如后续新增类型存放目录（如 `app/types/stubs`），同步加入。
   - 安装缺失的第三方类型 stub（若报告提示），常见组合：
     - `pip install types-requests types-python-dateutil types-PyYAML` 等；
     - 对于未提供官方 stub 的库，可在 `typings/` 或 `app/types/stubs/` 下添加轻量 `*.pyi` 占位并在 `pyrightconfig.json` 的 `typeshedPath` 指向。

4) **集中管理运行期挂载属性**
   - 对所有通过 `setattr(app, "xxx", obj)` 或直接点号赋值的动态属性，统一记录在 `WhaleFallFlask` 协议中。
   - 推荐在 `configure_app` 末尾调用一个 `_register_runtime_attrs(app: WhaleFallFlask)`，内部仅做类型标注与说明，不做逻辑，以保证 Pyright 能解析。

5) **示例代码片段（可直接套用）**
```python
from __future__ import annotations

from typing import Protocol, Callable
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager
from flask_caching import Cache

EnhancedErrorHandler = Callable[[Exception], tuple[dict[str, object], int]]


class WhaleFallFlask(Flask, Protocol):
    enhanced_error_handler: EnhancedErrorHandler
    cache: Cache


class WhaleFallLoginManager(LoginManager, Protocol):
    login_view: str | None
    login_message: str
    login_message_category: str
    session_protection: str | None
    remember_cookie_duration: int | float | timedelta
    remember_cookie_secure: bool
    remember_cookie_httponly: bool
```

6) **验证步骤**
- 本地执行 `npx pyright --warnings --verifytypes app.types.extensions`，确认协议无循环导入与缺失依赖。
- 运行 `npx pyright app/__init__.py` 观察 `reportAttributeAccessIssue` 数量显著下降。
- 补丁后执行 `./scripts/ruff_report.sh style` 确认无新增 Ruff 告警（尤其是类型注解相关规则 ANN*）。

## 预期效果
- `reportAttributeAccessIssue` 由 321 条收敛至零或个位数（只剩真实缺失属性）。
- `reportMissingImports` 解决路径与依赖后应清零；若仍存在则为真实缺文件问题，可据报错定位补齐模块。
- 后续对 Flask/登录扩展的改动可直接在协议中新增属性，避免重复 cast 与告警回归。
