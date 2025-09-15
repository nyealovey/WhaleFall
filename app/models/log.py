"""
泰摸鱼吧 - 操作日志模型
"""

from datetime import datetime

from app import db
from app.utils.timezone import now


class Log(db.Model):
    """操作日志模型"""

    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_type = db.Column(db.String(50), nullable=False, index=True)  # operation, system, error, security
    module = db.Column(db.String(100), nullable=True, index=True)  # 模块名称
    message = db.Column(db.Text, nullable=False)  # 日志消息
    details = db.Column(db.Text, nullable=True)  # 详细信息
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # 操作用户
    ip_address = db.Column(db.String(45), nullable=True)  # IP地址
    user_agent = db.Column(db.Text, nullable=True)  # 用户代理
    source = db.Column(db.String(50), nullable=True, index=True, comment="日志来源")  # 日志来源
    created_at = db.Column(db.DateTime(timezone=True), default=now, index=True)

    # 关系
    user = db.relationship("User", backref="logs")

    def __init__(
        self,
        level: str,
        log_type: str,
        message: str,
        module: str | None = None,
        details: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str | None = None,
    ) -> None:
        """
        初始化日志

        Args:
            level: 日志级别
            log_type: 日志类型
            message: 日志消息
            module: 模块名称
            details: 详细信息
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            source: 日志来源
        """
        self.level = level
        self.log_type = log_type
        self.message = message
        self.module = module
        self.details = details
        self.user_id = user_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.source = source

    def to_dict(self) -> dict:
        """
        转换为字典格式

        Returns:
            Dict: 日志信息字典
        """
        return {
            "id": self.id,
            "level": self.level,
            "log_type": self.log_type,
            "module": self.module,
            "message": self.message,
            "details": self.details,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def log_operation(
        level: str,
        log_type: str,
        message: str,
        module: str | None = None,
        details: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str | None = None,
    ) -> None:
        """
        记录操作日志

        Args:
            level: 日志级别
            log_type: 日志类型
            message: 日志消息
            module: 模块名称
            details: 详细信息
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            source: 日志来源
        """
        try:
            log = Log(
                level=level,
                log_type=log_type,
                message=message,
                module=module,
                details=details,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                source=source,
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # 记录日志失败时，使用系统日志记录
            import logging

            logging.error(f"记录操作日志失败: {e}")

    @staticmethod
    def log_info(
        message: str,
        module: str | None = None,
        details: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str | None = None,
    ) -> None:
        """记录INFO级别日志"""
        Log.log_operation(
            "INFO",
            "operation",
            message,
            module,
            details,
            user_id,
            ip_address,
            user_agent,
            source,
        )

    @staticmethod
    def log_warning(
        message: str,
        module: str | None = None,
        details: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str | None = None,
    ) -> None:
        """记录WARNING级别日志"""
        Log.log_operation(
            "WARNING",
            "operation",
            message,
            module,
            details,
            user_id,
            ip_address,
            user_agent,
            source,
        )

    @staticmethod
    def log_error(
        message: str,
        module: str | None = None,
        details: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str | None = None,
    ) -> None:
        """记录ERROR级别日志"""
        Log.log_operation(
            "ERROR",
            "error",
            message,
            module,
            details,
            user_id,
            ip_address,
            user_agent,
            source,
        )

    @staticmethod
    def log_security(
        message: str,
        module: str | None = None,
        details: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str | None = None,
    ) -> None:
        """记录安全相关日志"""
        Log.log_operation(
            "WARNING",
            "security",
            message,
            module,
            details,
            user_id,
            ip_address,
            user_agent,
            source,
        )

    @staticmethod
    def get_by_level(level: str) -> list:
        """根据级别获取日志"""
        return Log.query.filter_by(level=level).order_by(Log.created_at.desc()).all()

    @staticmethod
    def get_by_type(log_type: str) -> list:
        """根据类型获取日志"""
        return Log.query.filter_by(log_type=log_type).order_by(Log.created_at.desc()).all()

    @staticmethod
    def get_by_user(user_id: int) -> list:
        """根据用户获取日志"""
        return Log.query.filter_by(user_id=user_id).order_by(Log.created_at.desc()).all()

    @staticmethod
    def get_recent_logs(limit: int = 100) -> list:
        """获取最近的日志"""
        return Log.query.order_by(Log.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_error_logs(limit: int = 50) -> list:
        """获取错误日志"""
        return Log.query.filter(Log.level.in_(["ERROR", "CRITICAL"])).order_by(Log.created_at.desc()).limit(limit).all()

    def __repr__(self) -> str:
        return f"<Log {self.level}:{self.message[:50]}>"
