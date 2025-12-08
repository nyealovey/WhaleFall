"""鲸落 - 本地开发环境启动文件."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

# 添加项目根目录到 Python 路径
PROJECT_ROOT: Final[Path] = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.structlog_config import get_system_logger  # noqa: E402

if TYPE_CHECKING:
    from flask import Flask

os.environ.setdefault("FLASK_APP", "app")
os.environ.setdefault("FLASK_ENV", "development")

DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[str] = "5001"
DEFAULT_DEBUG: Final[str] = "true"


def _ensure_admin_account(flask_app: Flask) -> None:
    """确保 admin 账号存在, 避免初次启动无法登录.

    Args:
        flask_app: 当前的 Flask 应用实例, 用于推入 application context.

    """
    with flask_app.app_context():
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            User.create_admin()


def _load_runtime_config() -> tuple[str, int, bool]:
    """读取开发服务器运行参数."""
    host = os.environ.get("FLASK_HOST") or DEFAULT_HOST
    port = int(os.environ.get("FLASK_PORT", DEFAULT_PORT))
    debug = os.environ.get("FLASK_DEBUG", DEFAULT_DEBUG).lower() == "true"
    return host, port, debug


def _log_startup_instructions(host: str, port: int, *, debug: bool) -> None:
    """输出常见的本地访问说明, 便于开发者查阅."""
    logger = get_system_logger()
    logger.info("鲸落开发环境已启动", host=host, port=port, debug=debug)
    logger.info("访问入口", url=f"http://{host}:{port}")
    logger.info("管理后台", url=f"http://{host}:{port}/admin")
    logger.info("默认管理员凭据", username="admin", hint="随机密码见脚本输出")
    logger.info("辅助脚本", show_command="python scripts/show_admin_password.py")
    logger.info("辅助脚本", reset_command="python scripts/reset_admin_password.py")


def main() -> None:
    """启动 Flask 开发服务器并打印辅助信息."""
    app = create_app(init_scheduler_on_start=True)
    host, port, debug = _load_runtime_config()
    _ensure_admin_account(app)
    _log_startup_instructions(host, port, debug=debug)

    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
