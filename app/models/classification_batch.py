"""
自动分类批次模型
用于管理自动分类操作的批次信息，便于日志聚合和查询
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app import db
from app.utils.timezone import now


class ClassificationBatch(db.Model):
    """自动分类批次模型"""

    __tablename__ = "classification_batches"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 批次ID (UUID格式，用于关联日志)
    batch_id = Column(String(36), unique=True, nullable=False, index=True, comment="批次唯一标识")

    # 批次类型
    batch_type = Column(
        String(20),
        nullable=False,
        comment="批次类型: manual(手动), scheduled(定时), api(API)",
    )

    # 批次状态
    status = Column(
        String(20),
        nullable=False,
        default="running",
        comment="批次状态: running(运行中), completed(完成), failed(失败)",
    )

    # 开始时间
    started_at = Column(DateTime, nullable=False, default=func.now(), comment="批次开始时间")

    # 完成时间
    completed_at = Column(DateTime, nullable=True, comment="批次完成时间")

    # 处理统计
    total_accounts = Column(Integer, default=0, comment="总账户数")
    matched_accounts = Column(Integer, default=0, comment="匹配账户数")
    failed_accounts = Column(Integer, default=0, comment="失败账户数")

    # 规则统计
    total_rules = Column(Integer, default=0, comment="总规则数")
    active_rules = Column(Integer, default=0, comment="活跃规则数")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 批次详情 (JSON格式存储详细信息)
    batch_details = Column(Text, nullable=True, comment="批次详细信息(JSON)")

    # 创建者 (对于手动操作)
    created_by = Column(Integer, nullable=True, comment="创建者用户ID")

    # 创建时间
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")

    # 更新时间
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    def __repr__(self):
        return f"<ClassificationBatch {self.batch_id}>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "batch_type": self.batch_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "total_accounts": self.total_accounts,
            "matched_accounts": self.matched_accounts,
            "failed_accounts": self.failed_accounts,
            "total_rules": self.total_rules,
            "active_rules": self.active_rules,
            "error_message": self.error_message,
            "batch_details": self.batch_details,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def duration(self):
        """计算批次执行时长（秒）"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        if self.started_at:
            return (now() - self.started_at).total_seconds()
        return 0

    @property
    def success_rate(self):
        """计算成功率"""
        if self.total_accounts == 0:
            return 0
        return round((self.matched_accounts / self.total_accounts) * 100, 2)
