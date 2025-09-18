from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

# 泰摸鱼吧 - API测试


class TestAuthAPI:
    """认证API测试"""

    def test_login_success(self, client):
        """测试登录成功"""
        # 先创建测试用户
        from app.models import User, db

        test_password = "testpass"  # 测试环境专用密码
        with client.application.app_context():
            user = User(username="testuser", password=test_password, role="admin")
            user.set_password(test_password)
            db.session.add(user)
            db.session.commit()

        response = client.post("/api/auth/login", json={"username": "testuser", "password": test_password})

        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"

    def test_login_failure(self, client):
        """测试登录失败"""
        response = client.post("/api/auth/login", json={"username": "wronguser", "password": "wrongpass"})

        assert response.status_code == 401

    def test_protected_route_without_token(self, client):
        """测试无token访问受保护路由"""
        response = client.get("/api/instances")
        assert response.status_code == 401

    def test_protected_route_with_token(self, client, auth_headers):
        """测试有token访问受保护路由"""
        response = client.get("/api/instances", headers=auth_headers)
        assert response.status_code == 200


class TestInstanceAPI:
    """实例API测试"""

    def test_get_instances(self, client, auth_headers):
        """测试获取实例列表"""
        response = client.get("/api/instances", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "pagination" in data

    def test_create_instance(self, client, auth_headers):
        """测试创建实例"""
        response = client.post(
            "/api/instances",
            headers=auth_headers,
            json={
                "name": "测试数据库",
                "db_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "description": "测试用数据库",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "测试数据库"
        assert data["db_type"] == "postgresql"

    def test_create_instance_invalid_data(self, client, auth_headers):
        """测试创建实例无效数据"""
        response = client.post(
            "/api/instances",
            headers=auth_headers,
            json={
                "name": "",  # 空名称
                "db_type": "invalid_type",  # 无效类型
            },
        )
        assert response.status_code == 400

    def test_get_instance_by_id(self, client, auth_headers):
        """测试根据ID获取实例"""
        # 先创建实例
        create_response = client.post(
            "/api/instances",
            headers=auth_headers,
            json={"name": "测试数据库", "db_type": "postgresql", "host": "localhost", "port": 5432},
        )
        instance_id = create_response.get_json()["id"]

        # 获取实例
        response = client.get(f"/api/instances/{instance_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == instance_id
        assert data["name"] == "测试数据库"

    def test_update_instance(self, client, auth_headers):
        """测试更新实例"""
        # 先创建实例
        create_response = client.post(
            "/api/instances",
            headers=auth_headers,
            json={"name": "测试数据库", "db_type": "postgresql", "host": "localhost", "port": 5432},
        )
        instance_id = create_response.get_json()["id"]

        # 更新实例
        response = client.put(
            f"/api/instances/{instance_id}",
            headers=auth_headers,
            json={"name": "更新的数据库", "description": "更新后的描述"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "更新的数据库"
        assert data["description"] == "更新后的描述"

    def test_delete_instance(self, client, auth_headers):
        """测试删除实例"""
        # 先创建实例
        create_response = client.post(
            "/api/instances",
            headers=auth_headers,
            json={"name": "测试数据库", "db_type": "postgresql", "host": "localhost", "port": 5432},
        )
        instance_id = create_response.get_json()["id"]

        # 删除实例
        response = client.delete(f"/api/instances/{instance_id}", headers=auth_headers)
        assert response.status_code == 204

        # 验证实例已删除
        get_response = client.get(f"/api/instances/{instance_id}", headers=auth_headers)
        assert get_response.status_code == 404


class TestCredentialAPI:
    """凭据API测试"""

    def test_get_credentials(self, client, auth_headers):
        """测试获取凭据列表"""
        response = client.get("/api/credentials", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "pagination" in data

    def test_create_credential(self, client, auth_headers):
        """测试创建凭据"""
        response = client.post(
            "/api/credentials",
            headers=auth_headers,
            json={
                "name": "测试凭据",
                "credential_type": "database",
                "db_type": "postgresql",
                "username": "testuser",
                "password": "testpass",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "测试凭据"
        assert data["credential_type"] == "database"
        assert data["db_type"] == "postgresql"
        assert data["username"] == "testuser"
        # 密码应该被掩码
        assert "testpass" not in data["password"]


class TestAccountAPI:
    """账户API测试"""

    def test_get_accounts(self, client, auth_headers):
        """测试获取账户列表"""
        response = client.get("/api/accounts", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "pagination" in data

    def test_get_account_stats(self, client, auth_headers):
        """测试获取账户统计"""
        response = client.get("/api/accounts/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "total_accounts" in data
        assert "active_accounts" in data
        assert "by_db_type" in data


class TestTaskAPI:
    """任务API测试"""

    def test_get_tasks(self, client, auth_headers):
        """测试获取任务列表"""
        response = client.get("/api/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "pagination" in data

    def test_create_task(self, client, auth_headers):
        """测试创建任务"""
        # 先创建实例
        instance_response = client.post(
            "/api/instances",
            headers=auth_headers,
            json={"name": "测试数据库", "db_type": "postgresql", "host": "localhost", "port": 5432},
        )
        instance_id = instance_response.get_json()["id"]

        # 创建任务
        response = client.post(
            "/api/tasks",
            headers=auth_headers,
            json={
                "name": "测试任务",
                "instance_id": instance_id,
                "task_type": "sync",
                "schedule": "0 2 * * *",
                "enabled": True,
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "测试任务"
        assert data["instance_id"] == instance_id
        assert data["task_type"] == "sync"
        assert data["schedule"] == "0 2 * * *"
        assert data["enabled"] is True


class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
