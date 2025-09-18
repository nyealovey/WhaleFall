"""
泰摸鱼吧 - 用户模型
"""

from flask_login import UserMixin

from app import bcrypt, db
from app.utils.timezone import now


class User(UserMixin, db.Model):
    """用户模型"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # 关系
    # logs关系在UnifiedLog模型中定义

    def __init__(self, username: str, password: str, role: str = "user") -> None:
        """
        初始化用户

        Args:
            username: 用户名
            password: 密码
            role: 角色
        """
        self.username = username
        self.set_password(password)
        self.role = role

    def set_password(self, password: str) -> None:
        """
        设置密码（加密）

        Args:
            password: 原始密码
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
        """
        验证密码

        Args:
            password: 原始密码

        Returns:
            bool: 密码是否正确
        """
        return bcrypt.check_password_hash(self.password, password)

    def is_admin(self) -> bool:
        """
        检查是否为管理员

        Returns:
            bool: 是否为管理员
        """
        return self.role == "admin"

    def has_permission(self, permission: str) -> bool:
        """
        检查用户是否有指定权限

        Args:
            permission: 权限名称 (view, create, update, delete)

        Returns:
            bool: 是否有权限
        """
        # 管理员拥有所有权限
        if self.is_admin():
            return True

        # 根据角色判断权限
        if self.role == "admin":
            return True
        if self.role == "user":
            # 普通用户只有查看权限
            return permission == "view"
        # 其他角色默认无权限
        return False

    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login = now()
        db.session.commit()

    def to_dict(self) -> dict:
        """
        转换为字典

        Returns:
            dict: 用户信息字典
        """
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
        }

    @staticmethod
    def create_admin() -> "User | None":
        """创建默认管理员用户"""
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            # 使用环境变量或生成随机密码，避免硬编码
            import os
            import secrets
            import string
            
            default_password = os.getenv('DEFAULT_ADMIN_PASSWORD')
            if not default_password:
                # 生成随机密码：12位，包含大小写字母、数字和特殊字符
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                default_password = ''.join(secrets.choice(alphabet) for _ in range(12))
            
            admin = User(username="admin", password=default_password, role="admin")
            db.session.add(admin)
            db.session.commit()
            from app.utils.structlog_config import get_system_logger

            system_logger = get_system_logger()
            system_logger.info(
                "默认管理员用户已创建", 
                module="user_model", 
                username="admin",
                password_length=len(default_password)
            )
            
            # 在控制台显示生成的密码（仅开发环境）
            import os
            if os.getenv('FLASK_ENV') == 'development':
                print(f"\n{'='*60}")
                print(f"🔐 默认管理员账户已创建")
                print(f"用户名: admin")
                print(f"密码: {default_password}")
                print(f"{'='*60}")
                print(f"⚠️  请妥善保存此密码，生产环境请立即修改！")
                print(f"{'='*60}\n")
        return admin

    def __repr__(self) -> str:
        return f"<User {self.username}>"
