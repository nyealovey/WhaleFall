# tests/integration/conftest.py
"""集成测试专用 fixtures.

提供真实数据库连接和事务回滚机制。
"""

from __future__ import annotations

import os

import pytest


def _require_integration_database_url() -> str:
    """集成测试必须显式配置真实数据库（禁止默认 sqlite fallback）。"""
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url or "sqlite" in database_url:
        raise RuntimeError("集成测试需要真实数据库，请设置 DATABASE_URL 环境变量（禁止 sqlite）。")
    return database_url


@pytest.fixture(scope="session")
def app():
    """创建测试应用实例（整个测试会话复用）."""
    _require_integration_database_url()
    from app import create_app

    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="function")
def db_session(app):
    """数据库会话，测试后自动回滚.

    使用事务回滚确保测试隔离。
    """
    _require_integration_database_url()
    from app import db

    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()

        # 绑定会话到这个连接
        db.session.configure(bind=connection)

        yield db.session

        # 回滚事务，撤销所有更改
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(app, db_session):
    """测试客户端，每个测试函数独立."""
    return app.test_client()
