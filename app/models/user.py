"""鲸落 - 用户模型."""

from flask_login import UserMixin

from app import bcrypt, db
from app.constants import UserRole
from app.utils.time_utils import time_utils


class User(UserMixin, db.Model):
    """用户模型.

    管理系统用户的认证和授权信息,包括用户名、密码、角色等.
    继承 Flask-Login 的 UserMixin 提供会话管理功能.

    Attributes:
        id: 用户 ID,主键.
        username: 用户名,唯一索引.
        password: 加密后的密码(bcrypt).
        role: 用户角色,可选值:admin、user.
        created_at: 创建时间.
        last_login: 最后登录时间.
        is_active: 是否启用.

    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # 关系
    # logs关系在UnifiedLog模型中定义

    def __init__(self, username: str | None = None, password: str | None = None, role: str = "user") -> None:
        """初始化用户.

        Args:
            username: 用户名
            password: 密码
            role: 角色

        """
        if username is not None:
            self.username = username
        if password is not None:
            self.set_password(password)
        self.role = role or UserRole.USER

    def set_password(self, password: str) -> None:
        """设置密码(加密).

        Args:
            password: 原始密码.

        Returns:
            None: 密码校验与加密完成后即返回.

        Raises:
            ValueError: 当密码不满足长度或复杂度要求时抛出.

        """
        # 增加密码强度验证
        if len(password) < 8:
            error_msg = "密码长度至少8位"
            raise ValueError(error_msg)
        if not any(c.isupper() for c in password):
            error_msg = "密码必须包含大写字母"
            raise ValueError(error_msg)
        if not any(c.islower() for c in password):
            error_msg = "密码必须包含小写字母"
            raise ValueError(error_msg)
        if not any(c.isdigit() for c in password):
            error_msg = "密码必须包含数字"
            raise ValueError(error_msg)

        self.password = bcrypt.generate_password_hash(password, rounds=12).decode("utf-8")

    def check_password(self, password: str) -> bool:
        """验证密码.

        Args:
            password: 原始密码

        Returns:
            bool: 密码是否正确

        """
        return bcrypt.check_password_hash(self.password, password)

    def is_admin(self) -> bool:
        """检查是否为管理员.

        Returns:
            bool: 是否为管理员

        """
        return self.role == UserRole.ADMIN

    def to_dict(self) -> dict:
        """转换为字典.

        Returns:
            dict: 用户信息字典

        """
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.strftime("%Y-%m-%d") if self.created_at else None,
            "created_at_display": self.created_at.strftime("%Y-%m-%d") if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
        }

    @classmethod
    def active_admin_count(cls, *, exclude_user_id: int | None = None) -> int:
        """统计当前活跃管理员数量,可选排除指定用户.

        Args:
            exclude_user_id: 需要排除的用户 ID,用于编辑场景.

        Returns:
            int: 满足 `role=admin` 且 `is_active=True` 的用户数量.

        """
        query = cls.query.filter(cls.role == UserRole.ADMIN, cls.is_active.is_(True))
        if exclude_user_id is not None:
            query = query.filter(cls.id != exclude_user_id)
        return query.count()

    def __repr__(self) -> str:
        """返回用户模型的调试字符串.

        Returns:
            str: 展示用户名的文本.

        """
        return f"<User {self.username}>"
