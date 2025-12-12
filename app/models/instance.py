"""鲸落 - 实例模型."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypedDict, Unpack

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Sequence

    class InstanceOrmFields(TypedDict, total=False):
        id: int
        name: str
        db_type: str
        host: str
        port: int
        database_name: str | None
        database_version: str | None
        main_version: str | None
        detailed_version: str | None
        sync_count: int
        credential_id: int | None
        description: str | None
        is_active: bool
        last_connected: Any
        created_at: Any
        updated_at: Any
        deleted_at: Any


@dataclass(slots=True)
class InstanceCreateParams:
    """实例初始化参数."""

    name: str
    db_type: str
    host: str
    port: int
    database_name: str | None = None
    credential_id: int | None = None
    description: str | None = None
    tags: Sequence[object] | None = None
    is_active: bool = True


class Instance(db.Model):
    """数据库实例模型.

    存储数据库实例的基本信息,包括连接配置、版本信息、
    关联的凭据和标签等.

    Attributes:
        id: 实例主键.
        name: 实例名称,唯一.
        db_type: 数据库类型(mysql、postgresql、sqlserver、oracle等).
        host: 主机地址.
        port: 端口号.
        database_name: 数据库名称,可选.
        database_version: 原始版本字符串.
        main_version: 主版本号(如 8.0、13.4).
        detailed_version: 详细版本号(如 8.0.32、13.4).
        sync_count: 同步次数.
        credential_id: 关联的凭据ID.
        description: 描述信息.
        is_active: 是否激活.
        last_connected: 最后连接时间.
        created_at: 创建时间.
        updated_at: 更新时间.
        deleted_at: 删除时间.

    """

    __tablename__ = "instances"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    db_type = db.Column(db.String(50), nullable=False, index=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    database_name = db.Column(db.String(255), nullable=True)
    database_version = db.Column(db.String(1000), nullable=True)  # 原始版本字符串
    main_version = db.Column(db.String(20), nullable=True)  # 主版本号 (如 8.0, 13.4, 14.0)
    detailed_version = db.Column(db.String(50), nullable=True)  # 详细版本号 (如 8.0.32, 13.4, 14.0.3465.1)
    sync_count = db.Column(db.Integer, default=0, nullable=False)
    credential_id = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_connected = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # 关系
    credential = db.relationship("Credential", backref="instances")
    # 标签关系
    tags = db.relationship("Tag", secondary="instance_tags", back_populates="instances", lazy="dynamic")
    # 数据库大小统计关系
    database_size_stats = db.relationship(
        "DatabaseSizeStat",
        back_populates="instance",
        cascade="all, delete-orphan",
    )
    database_size_aggregations = db.relationship(
        "DatabaseSizeAggregation",
        back_populates="instance",
        cascade="all, delete-orphan",
    )
    # 实例大小统计关系
    instance_size_stats = db.relationship(
        "InstanceSizeStat",
        back_populates="instance",
        cascade="all, delete-orphan",
    )

    # 实例数据库关系
    instance_databases = db.relationship(
        "InstanceDatabase",
        back_populates="instance",
        cascade="all, delete-orphan",
    )
    instance_accounts = db.relationship(
        "InstanceAccount",
        back_populates="instance",
        cascade="all, delete-orphan",
    )
    instance_size_aggregations = db.relationship(
        "InstanceSizeAggregation",
        back_populates="instance",
        cascade="all, delete-orphan",
    )
    # accounts关系已移除,因为Account模型已废弃,使用AccountPermission
    # sync_data关系已移除,因为SyncData表已删除

    def __init__(
        self,
        params: InstanceCreateParams | None = None,
        **orm_fields: Unpack["InstanceOrmFields"],
    ) -> None:
        """初始化实例数据.

        Args:
            params: 结构化的实例参数对象,用于 batch/create 流程.
            **orm_fields: ORM 加载或测试场景注入的原始字段.

        """
        super().__init__(**orm_fields)
        if params is None:
            self._pending_tags = None
            return
        self.name = params.name
        self.db_type = params.db_type
        self.host = params.host
        self.port = params.port
        self.database_name = params.database_name
        self.credential_id = params.credential_id
        self.description = params.description
        self.is_active = params.is_active
        self._pending_tags = list(params.tags) if params.tags else None

    def to_dict(self, *, include_password: bool = False) -> dict:
        """转换为字典格式.

        Args:
            include_password: 是否包含凭据密码,默认为 False(安全考虑).

        Returns:
            包含实例完整信息的字典,包括关联的凭据和标签.

        """
        status_value = "deleted" if self.deleted_at else ("active" if self.is_active else "inactive")

        data = {
            "id": self.id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database_name": self.database_name,
            "database_version": self.database_version,
            "main_version": self.main_version,
            "detailed_version": self.detailed_version,
            "credential_id": self.credential_id,
            "description": self.description,
            "tags": [tag.to_dict() for tag in self.tags],
            "is_active": self.is_active,
            "last_connected": (self.last_connected.isoformat() if self.last_connected else None),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": status_value,
        }

        if self.credential:
            if include_password:
                data["credential"] = {
                    "id": self.credential.id,
                    "name": self.credential.name,
                    "username": self.credential.username,
                    "password": self.credential.password,
                    "credential_type": self.credential.credential_type,
                }
            else:
                data["credential"] = {
                    "id": self.credential.id,
                    "name": self.credential.name,
                    "username": self.credential.username,
                    "password": self.credential.get_password_masked(),
                    "credential_type": self.credential.credential_type,
                }

        return data

    def __repr__(self) -> str:
        """返回实例的调试字符串.

        Returns:
            str: 展示实例名称的文本表示.

        """
        return f"<Instance {self.name}>"
