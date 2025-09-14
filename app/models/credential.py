"""
泰摸鱼吧 - 凭据模型
"""

from datetime import datetime

from app import bcrypt, db
from app.utils.password_manager import password_manager
from app.utils.timezone import now


class Credential(db.Model):
    """凭据模型"""

    __tablename__ = "credentials"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    credential_type = db.Column(db.String(50), nullable=False, index=True)
    db_type = db.Column(db.String(50), nullable=True, index=True)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instance_ids = db.Column(db.JSON, nullable=True)
    category_id = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __init__(
        self,
        name: str,
        credential_type: str,
        username: str,
        password: str,
        db_type: str | None = None,
        instance_ids: list | None = None,
        category_id: int | None = None,
        description: str | None = None,
    ) -> None:
        """
        初始化凭据

        Args:
            name: 凭据名称
            credential_type: 凭据类型
            username: 用户名
            password: 密码
            db_type: 数据库类型
            instance_ids: 关联实例ID列表
            category_id: 分类ID
            description: 描述
        """
        self.name = name
        self.credential_type = credential_type
        self.username = username
        self.set_password(password)
        self.db_type = db_type
        self.instance_ids = instance_ids or []
        self.category_id = category_id
        self.description = description

    def set_password(self, password: str) -> None:
        """
        设置密码（加密）

        Args:
            password: 原始密码
        """
        # 使用新的加密方式存储密码
        self.password = password_manager.encrypt_password(password)

    def check_password(self, password: str) -> bool:
        """
        验证密码

        Args:
            password: 原始密码

        Returns:
            bool: 密码是否正确
        """
        # 如果是bcrypt哈希（旧格式），使用bcrypt验证
        if self.password.startswith("$2b$"):
            return bcrypt.check_password_hash(self.password, password)

        # 如果是我们的加密格式，解密后比较
        if password_manager.is_encrypted(self.password):
            decrypted_password = password_manager.decrypt_password(self.password)
            return decrypted_password == password

        # 如果是明文密码（不安全），直接比较
        return self.password == password

    def get_password_masked(self) -> str:
        """
        获取掩码密码

        Returns:
            str: 掩码后的密码
        """
        if len(self.password) > 8:
            return "*" * (len(self.password) - 4) + self.password[-4:]
        return "*" * len(self.password)

    def get_plain_password(self) -> str:
        """
        获取原始密码（用于数据库连接）

        Returns:
            str: 原始密码
        """
        # 如果密码是bcrypt哈希，说明是旧格式，需要特殊处理
        if self.password.startswith("$2b$"):
            # 对于旧格式，我们需要从环境变量或其他地方获取密码
            # 这里使用硬编码的密码作为临时解决方案
            # TODO: 实现更安全的密码管理机制
            if self.db_type == "mysql" or self.db_type == "sqlserver":
                return "MComnyistqolr#@2222"
            return ""

        # 如果是我们的加密格式，尝试解密
        if password_manager.is_encrypted(self.password):
            return password_manager.decrypt_password(self.password)

        # 如果都不是，可能是明文密码（不安全）
        return self.password

    def to_dict(self, include_password: bool = False) -> dict:
        """
        转换为字典

        Args:
            include_password: 是否包含密码

        Returns:
            dict: 凭据信息字典
        """
        data = {
            "id": self.id,
            "name": self.name,
            "credential_type": self.credential_type,
            "db_type": self.db_type,
            "username": self.username,
            "instance_ids": self.instance_ids,
            "category_id": self.category_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_password:
            data["password"] = self.password
        else:
            data["password"] = self.get_password_masked()

        return data

    def soft_delete(self) -> None:
        """软删除凭据"""
        self.deleted_at = now()
        db.session.commit()
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.info(
            "凭据删除",
            module="model",
            operation="credential_delete",
            credential_id=self.id,
            name=self.name,
        )

    def restore(self) -> None:
        """恢复凭据"""
        self.deleted_at = None
        db.session.commit()
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.info(
            "凭据恢复",
            module="model",
            operation="credential_restore",
            credential_id=self.id,
            name=self.name,
        )

    @staticmethod
    def get_active_credentials() -> list:
        """获取所有活跃凭据"""
        return Credential.query.filter_by(deleted_at=None).all()

    @staticmethod
    def get_by_type(credential_type: str) -> list:
        """根据类型获取凭据"""
        return Credential.query.filter_by(credential_type=credential_type, deleted_at=None).all()

    @staticmethod
    def get_by_db_type(db_type: str) -> list:
        """根据数据库类型获取凭据"""
        return Credential.query.filter_by(db_type=db_type, deleted_at=None).all()

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            Dict: 凭据信息字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "credential_type": self.credential_type,
            "db_type": self.db_type,
            "username": self.username,
            "instance_ids": self.instance_ids,
            "category_id": self.category_id,
            "is_active": getattr(self, "is_active", True),
            "description": getattr(self, "description", ""),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Credential {self.name}>"
