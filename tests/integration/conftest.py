# tests/integration/conftest.py
"""集成测试专用 fixtures.

提供真实数据库连接和事务回滚机制。
"""

import os

import pytest

# 集成测试需要真实数据库，检查环境变量
if "DATABASE_URL" not in os.environ or "sqlite" in os.environ.get("DATABASE_URL", ""):
    pytest.skip(
        "集成测试需要真实数据库，请设置 DATABASE_URL 环境变量",
        allow_module_level=True,
    )

from app import create_app, db


@pytest.fixture(scope="session")
def app():
    """创建测试应用实例（整个测试会话复用）."""
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="function")
def db_session(app):
    """数据库会话，测试后自动回滚.

    使用事务回滚确保测试隔离。
    """
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
