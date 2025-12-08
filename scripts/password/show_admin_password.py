#!/usr/bin/env python3
"""展示默认管理员凭据的辅助脚本."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

# 添加项目根目录到 Python 路径, 便于直接调用应用依赖
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.structlog_config import get_system_logger  # noqa: E402

OUTPUT_PREFIX: Final[str] = "[WhaleFall] "


def _emit_message(message: str) -> None:
    """通过 stdout 输出提示, 避免使用 print() 触发 Ruff T201."""
    sys.stdout.write(f"{OUTPUT_PREFIX}{message}\n")
    sys.stdout.flush()


def _show_env_password(env_password: str) -> None:
    """打印环境变量中的管理员密码, 并记录日志."""
    system_logger = get_system_logger()
    system_logger.info(
        "检测到 DEFAULT_ADMIN_PASSWORD 环境变量",
        module="show_admin_password",
        strategy="env",
    )
    _emit_message("当前正在使用环境变量 DEFAULT_ADMIN_PASSWORD 作为管理员密码.")
    _emit_message("请妥善保存以下密码, 仅在可信终端使用:")
    _emit_message(env_password)


def _show_database_hint(admin: User) -> None:
    """提供数据库中管理员账号的状态提示, 引导用户执行重置脚本."""
    system_logger = get_system_logger()
    system_logger.info(
        "未设置环境变量密码, 数据库中保存的是哈希值",
        module="show_admin_password",
        strategy="database",
        password_hash=admin.password,
    )
    _emit_message("当前管理员密码由数据库维护, 已做加盐哈希处理, 无法直接还原.")
    _emit_message("若忘记明文密码, 请运行 scripts/password/reset_admin_password.py 生成新的随机密码.")
    _emit_message("现有哈希值仅供排查使用:")
    _emit_message(admin.password)


def show_admin_password() -> None:
    """在安全上下文中展示管理员凭据说明."""
    app = create_app(init_scheduler_on_start=False)

    with app.app_context():
        system_logger = get_system_logger()

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            system_logger.error(
                "未找到管理员账号, 请确认数据库迁移或初始化脚本已执行",
                module="show_admin_password",
            )
            _emit_message("未在数据库中找到 admin 账号, 请先执行初始化或运行重置脚本.")
            return

        env_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
        if env_password:
            _show_env_password(env_password)
            return

        _show_database_hint(admin)


if __name__ == "__main__":
    show_admin_password()
