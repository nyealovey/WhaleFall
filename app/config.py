"""鲸落 - 配置兼容层(已弃用).

历史原因:
- 旧实现使用 `Config` 在 import 阶段读取环境变量并做强校验,容易导致:
  - 启动顺序敏感(导入即失败)
  - 回退逻辑不可达(看似有 sqlite/简单缓存回退,实际被 import 阶段拦截)

当前推荐:
- 使用 `app/settings.py` 的 `Settings` 作为唯一配置来源.
- `create_app(settings=...)` 只消费 Settings,不再散落 `os.getenv`.

本模块仅保留兼容入口,避免旧代码/文档引用 `app.config` 时直接报错.
"""

from __future__ import annotations

from app.settings import Settings


def load_settings() -> Settings:
    """加载 Settings 配置对象.

    Returns:
        Settings: 已解析并校验后的配置对象.

    """
    return Settings.load()

