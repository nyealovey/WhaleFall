from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

# 泰摸鱼吧 - 模型测试

from app.models import Account, Credential, GlobalParam, Instance, Task, User


class TestUser:
    """用户模型测试"""

    def test_user_creation(self, app):
        """测试用户创建"""
        test_password = "testpass"  # 测试环境专用密码
        with app.app_context():
            user = User(username="testuser", password=test_password, role="admin")
            user.set_password(test_password)
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.username == "testuser"
            assert user.role == "admin"
            assert user.check_password(test_password)
            assert not user.check_password("wrongpass")

    def test_user_password_hashing(self, app):
        """测试密码哈希"""
        test_password = "testpass"  # 测试环境专用密码
        with app.app_context():
            user = User(username="testuser", password=test_password)
            user.set_password(test_password)

            assert user.password != test_password
            assert user.check_password(test_password)
            assert not user.check_password("wrongpass")

    def test_user_last_login_update(self, app):
        """测试最后登录时间更新"""
        with app.app_context():
            user = User(username="testuser", password="testpass")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()

            assert user.last_login is None

            user.update_last_login()
            assert user.last_login is not None


class TestInstance:
    """实例模型测试"""

    def test_instance_creation(self, app):
        """测试实例创建"""
        with app.app_context():
            instance = Instance(
                name="测试数据库", db_type="postgresql", host="localhost", port=5432, description="测试用数据库"
            )
            db.session.add(instance)
            db.session.commit()

            assert instance.id is not None
            assert instance.name == "测试数据库"
            assert instance.db_type == "postgresql"
            assert instance.host == "localhost"
            assert instance.port == 5432

    def test_instance_soft_delete(self, app):
        """测试实例软删除"""
        with app.app_context():
            instance = Instance(name="测试数据库", db_type="postgresql", host="localhost", port=5432)
            db.session.add(instance)
            db.session.commit()

            assert instance.deleted_at is None
            assert instance.status == "active"

            instance.soft_delete()
            assert instance.deleted_at is not None
            assert instance.status == "deleted"


class TestCredential:
    """凭据模型测试"""

    def test_credential_creation(self, app):
        """测试凭据创建"""
        with app.app_context():
            credential = Credential(
                name="测试凭据",
                credential_type="database",
                db_type="postgresql",
                username="testuser",
                password="testpass",
            )
            credential.set_password("testpass")
            db.session.add(credential)
            db.session.commit()

            assert credential.id is not None
            assert credential.name == "测试凭据"
            assert credential.credential_type == "database"
            assert credential.db_type == "postgresql"
            assert credential.username == "testuser"
            assert credential.check_password("testpass")

    def test_credential_password_masking(self, app):
        """测试密码掩码"""
        with app.app_context():
            credential = Credential(
                name="测试凭据",
                credential_type="database",
                db_type="postgresql",
                username="testuser",
                password="testpass",
            )
            credential.set_password("testpass")

            masked = credential.get_password_masked()
            assert "*" in masked
            assert "testpass" not in masked


class TestAccount:
    """账户模型测试"""

    def test_account_creation(self, app):
        """测试账户创建"""
        with app.app_context():
            # 先创建实例
            instance = Instance(name="测试数据库", db_type="postgresql", host="localhost", port=5432)
            db.session.add(instance)
            db.session.commit()

            account = Account(instance_id=instance.id, username="testuser", account_type="user", is_active=True)
            db.session.add(account)
            db.session.commit()

            assert account.id is not None
            assert account.instance_id == instance.id
            assert account.username == "testuser"
            assert account.account_type == "user"
            assert account.is_active is True


class TestTask:
    """任务模型测试"""

    def test_task_creation(self, app):
        """测试任务创建"""
        with app.app_context():
            # 先创建实例
            instance = Instance(name="测试数据库", db_type="postgresql", host="localhost", port=5432)
            db.session.add(instance)
            db.session.commit()

            task = Task(name="测试任务", instance_id=instance.id, task_type="sync", schedule="0 2 * * *", enabled=True)
            db.session.add(task)
            db.session.commit()

            assert task.id is not None
            assert task.name == "测试任务"
            assert task.instance_id == instance.id
            assert task.task_type == "sync"
            assert task.schedule == "0 2 * * *"
            assert task.enabled is True


class TestGlobalParam:
    """全局参数模型测试"""

    def test_global_param_creation(self, app):
        """测试全局参数创建"""
        with app.app_context():
            param = GlobalParam(key="test_key", value="test_value", description="测试参数", param_type="string")
            db.session.add(param)
            db.session.commit()

            assert param.id is not None
            assert param.key == "test_key"
            assert param.value == "test_value"
            assert param.description == "测试参数"
            assert param.param_type == "string"
