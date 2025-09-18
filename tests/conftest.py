from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

# 鲸落 - 测试配置


import pytest

from app import create_app, db
from app.models import Account, Credential, Instance, User


@pytest.fixture
def app():
    """创建测试应用实例"""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret-key",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建测试运行器"""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(client):
    """创建认证头"""
    # 创建测试用户
    test_password = "testpass"  # 测试环境专用密码
    user = User(username="testuser", password=test_password, role="admin")
    user.set_password(test_password)
    db.session.add(user)
    db.session.commit()

    # 登录获取token
    response = client.post("/api/auth/login", json={"username": "testuser", "password": test_password})

    token = response.json.get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_instance():
    """创建示例实例"""
    return Instance(
        name="测试数据库", db_type="postgresql", host="localhost", port=5432, description="测试用PostgreSQL数据库"
    )


@pytest.fixture
def sample_credential():
    """创建示例凭据"""
    test_password = "testpass"  # 测试环境专用密码
    return Credential(
        name="测试凭据", credential_type="database", db_type="postgresql", username="testuser", password=test_password
    )


@pytest.fixture
def sample_account():
    """创建示例账户"""
    return Account(
        instance_id=1, username="testuser", account_type="user", is_active=True, last_login="2024-01-01 00:00:00"
    )
