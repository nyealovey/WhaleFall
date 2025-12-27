# tests/unit/routes/conftest.py
"""API 契约测试专用 fixtures.

提供 test_client 和认证会话相关的 fixtures。
"""

import pytest

from app import create_app, db
from app.models.user import User
from app.settings import Settings


@pytest.fixture(scope="function")
def app(monkeypatch):
    """创建测试应用实例."""
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="function")
def client(app):
    """创建测试客户端."""
    return app.test_client()


@pytest.fixture(scope="function")
def auth_client(app):
    """创建已认证的测试客户端.

    自动创建测试用户并设置会话。
    """
    with app.app_context():
        # 创建必要的表
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )

        # 创建测试用户
        user = User(username="test_admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)

        yield client

        # 清理
        db.session.rollback()
