"""鲸落 - WSGI 入口文件, 提供生产与本地统一启动方式。."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from gevent import monkey
except ImportError:  # pragma: no cover - gevent 为可选依赖
    monkey = None
else:  # pragma: no cover - gevent 在本地测试环境通常不存在
    monkey.patch_all()

from app import create_app  # noqa: E402

os.environ.setdefault("FLASK_APP", "app")
os.environ.setdefault("FLASK_ENV", "production")

application = app = create_app(init_scheduler_on_start=True)


def _resolve_host_and_port() -> tuple[str, int]:
    """解析 WSGI 运行时绑定信息, 默认使用 127.0.0.1。."""
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5001"))
    return host, port


if __name__ == "__main__":
    host, port = _resolve_host_and_port()
    application.run(host=host, port=port, debug=False)
