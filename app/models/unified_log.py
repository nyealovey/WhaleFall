"""
鲸落 - 统一日志系统数据模型
基于structlog的统一日志存储模型
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum

from app import db
from app.utils.timezone import now, utc_to_china


class LogLevel(Enum):
    """日志级别枚举"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UnifiedLog(db.Model):
    """统一日志表"""

    __tablename__ = "unified_logs"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 日志时间戳 (UTC)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # 日志级别
    level = Column(SQLEnum(LogLevel, name="log_level"), nullable=False, index=True)

    # 模块/组件名
    module = Column(String(100), nullable=False, index=True)

    # 日志消息
    message = Column(Text, nullable=False)

    # 错误堆栈追踪 (仅ERROR/CRITICAL)
    traceback = Column(Text, nullable=True)

    # 附加上下文 (JSON格式)
    context = Column(JSON, nullable=True)

    # 记录创建时间
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)

    # 复合索引优化查询性能
    __table_args__ = (
        Index("idx_timestamp_level_module", "timestamp", "level", "module"),
        Index("idx_timestamp_module", "timestamp", "module"),
        Index("idx_level_timestamp", "level", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<UnifiedLog(id={self.id}, level={self.level}, module={self.module}, timestamp={self.timestamp})>"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        # 将UTC时间转换为东八区时间显示
        china_timestamp = utc_to_china(self.timestamp)
        china_created_at = utc_to_china(self.created_at) if self.created_at else None

        return {
            "id": self.id,
            "timestamp": china_timestamp.isoformat() if china_timestamp else None,
            "level": self.level.value if self.level else None,
            "module": self.module,
            "message": self.message,
            "traceback": self.traceback,
            "context": self.context,
            "created_at": china_created_at.isoformat() if china_created_at else None,
        }

    @classmethod
    def create_log_entry(
        cls,
        level: LogLevel,
        module: str,
        message: str,
        traceback: str | None = None,
        context: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> "UnifiedLog":
        """创建日志条目"""
        # 确保时间戳带时区信息
        if timestamp is None:
            timestamp = now()
        elif timestamp.tzinfo is None:
            # 如果没有时区信息，假设为UTC时间
            from app.utils.timezone import UTC_TZ

            timestamp = timestamp.replace(tzinfo=UTC_TZ)

        return cls(
            timestamp=timestamp,
            level=level,
            module=module,
            message=message,
            traceback=traceback,
            context=context or {},
        )

    @classmethod
    def get_recent_logs(
        cls,
        hours: int = 24,
        level: LogLevel | None = None,
        module: str | None = None,
        limit: int = 100,
    ) -> list["UnifiedLog"]:
        """获取最近的日志"""
        query = cls.query.filter(cls.timestamp >= now() - timedelta(hours=hours))

        if level:
            query = query.filter(cls.level == level)

        if module:
            query = query.filter(cls.module.like(f"%{module}%"))

        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def get_error_logs(cls, hours: int = 24, limit: int = 50) -> list["UnifiedLog"]:
        """获取错误日志"""
        return (
            cls.query.filter(
                cls.timestamp >= now() - timedelta(hours=hours),
                cls.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]),
            )
            .order_by(cls.timestamp.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def get_logs_by_module(cls, module: str, hours: int = 24, limit: int = 100) -> list["UnifiedLog"]:
        """根据模块获取日志"""
        return (
            cls.query.filter(
                cls.module == module,
                cls.timestamp >= now() - timedelta(hours=hours),
            )
            .order_by(cls.timestamp.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def search_logs(
        cls,
        search_term: str,
        hours: int = 24,
        level: LogLevel | None = None,
        module: str | None = None,
        limit: int = 100,
    ) -> list["UnifiedLog"]:
        """搜索日志"""
        query = cls.query.filter(cls.timestamp >= now() - timedelta(hours=hours))

        # 全文搜索消息和上下文
        search_filter = db.or_(cls.message.like(f"%{search_term}%"), cls.context.like(f"%{search_term}%"))
        query = query.filter(search_filter)

        if level:
            query = query.filter(cls.level == level)

        if module:
            query = query.filter(cls.module.like(f"%{module}%"))

        return query.order_by(cls.timestamp.desc()).limit(limit).all()

    @classmethod
    def get_log_modules(cls, hours: int = 24) -> list["UnifiedLog"]:
        """获取日志模块列表"""
        from sqlalchemy import func

        start_time = now() - timedelta(hours=hours)

        # 获取不重复的模块列表，按日志数量排序
        modules = (
            db.session.query(cls.module, func.count(cls.id).label("count"))
            .filter(cls.timestamp >= start_time)
            .group_by(cls.module)
            .order_by(func.count(cls.id).desc())
            .all()
        )

        # 返回模块对象列表
        result = []
        for module_name, count in modules:
            # 创建一个临时的UnifiedLog对象来存储模块信息
            module_obj = cls()
            module_obj.module = module_name
            module_obj.id = count  # 使用count作为临时ID
            result.append(module_obj)

        return result

    @classmethod
    def get_log_statistics(cls, hours: int = 24) -> dict[str, Any]:
        """获取日志统计信息"""
        from datetime import timedelta

        from sqlalchemy import func

        start_time = now() - timedelta(hours=hours)

        # 总日志数
        total_logs = cls.query.filter(cls.timestamp >= start_time).count()

        # 按级别统计
        level_stats = (
            db.session.query(cls.level, func.count(cls.id).label("count"))
            .filter(cls.timestamp >= start_time)
            .group_by(cls.level)
            .all()
        )

        # 按模块统计
        module_stats = (
            db.session.query(cls.module, func.count(cls.id).label("count"))
            .filter(cls.timestamp >= start_time)
            .group_by(cls.module)
            .order_by(func.count(cls.id).desc())
            .limit(10)
            .all()
        )

        # 错误日志数
        error_count = cls.query.filter(
            cls.timestamp >= start_time,
            cls.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]),
        ).count()

        # 按级别统计
        level_counts = {level.value: count for level, count in level_stats}

        return {
            "total_logs": total_logs,
            "error_count": error_count,
            "warning_count": level_counts.get("WARNING", 0),
            "info_count": level_counts.get("INFO", 0),
            "debug_count": level_counts.get("DEBUG", 0),
            "critical_count": level_counts.get("CRITICAL", 0),
            "level_distribution": level_counts,
            "top_modules": [{"module": module, "count": count} for module, count in module_stats],
            "error_rate": (error_count / total_logs * 100) if total_logs > 0 else 0,
        }

    @classmethod
    def cleanup_old_logs(cls, days: int = 90) -> int:
        """清理旧日志"""
        cutoff_date = now() - timedelta(days=days)
        deleted_count = cls.query.filter(cls.timestamp < cutoff_date).delete()
        db.session.commit()
        return deleted_count
