"""鲸落 - 数据库类型配置模型.

管理数据库类型的配置信息。
"""

import json
from typing import Any

from app import db
from app.utils.time_utils import time_utils


class DatabaseTypeConfig(db.Model):
    """数据库类型配置模型.

    管理数据库类型的配置信息,包括连接参数、显示样式、特性列表等.
    支持系统内置类型和自定义类型.

    Attributes:
        id: 主键 ID.
        name: 数据库类型名称(唯一).
        display_name: 显示名称.
        driver: 驱动名称.
        default_port: 默认端口.
        default_schema: 默认 Schema.
        connection_timeout: 连接超时时间(秒).
        description: 描述信息.
        icon: 图标类名(Font Awesome).
        color: 主题颜色.
        features: 特性列表(JSON 字符串).
        is_active: 是否启用.
        is_system: 是否系统内置.
        sort_order: 排序顺序.
        created_at: 创建时间.
        updated_at: 更新时间.

    """

    __tablename__ = "database_type_configs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, comment="数据库类型名称")
    display_name = db.Column(db.String(100), nullable=False, comment="显示名称")
    driver = db.Column(db.String(50), nullable=False, comment="驱动名称")
    default_port = db.Column(db.Integer, nullable=False, comment="默认端口")
    default_schema = db.Column(db.String(50), nullable=False, comment="默认Schema")
    connection_timeout = db.Column(db.Integer, default=30, comment="连接超时时间")
    description = db.Column(db.Text, comment="描述信息")
    icon = db.Column(db.String(50), default="fa-database", comment="图标类名")
    color = db.Column(db.String(20), default="primary", comment="主题颜色")
    features = db.Column(db.Text, comment="特性列表(JSON)")
    is_active = db.Column(db.Boolean, default=True, comment="是否启用")
    is_system = db.Column(db.Boolean, default=False, comment="是否系统内置")
    sort_order = db.Column(db.Integer, default=0, comment="排序顺序")
    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, comment="创建时间")
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=time_utils.now,
        onupdate=time_utils.now,
        comment="更新时间",
    )

    def __repr__(self) -> str:
        """返回数据库类型配置的调试表示.

        Returns:
            str: 含名称的可读文本,便于日志排查.

        """
        return f"<DatabaseTypeConfig {self.name}>"

    @property
    def features_list(self) -> list[str]:
        """获取 JSON 存储的特性列表.

        Returns:
            list[str]: 解码后的特性集合,解析失败时返回空列表.

        """
        if self.features:
            try:
                return json.loads(self.features)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @features_list.setter
    def features_list(self, value: list[str]) -> None:
        """设置 JSON 存储的特性列表.

        Args:
            value: 需要持久化的特性名称列表.

        Returns:
            None: 属性赋值完成即结束.

        """
        self.features = json.dumps(value, ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        """转换为易于序列化的字典.

        Returns:
            dict[str, Any]: 包含显示信息、连接参数及元数据的字典.

        """
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "driver": self.driver,
            "default_port": self.default_port,
            "default_schema": self.default_schema,
            "connection_timeout": self.connection_timeout,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "features": self.features_list,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_active_types(cls) -> list["DatabaseTypeConfig"]:
        """查询启用状态的数据库类型.

        Returns:
            list[DatabaseTypeConfig]: 已激活且按排序规则排列的配置列表.

        """
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order, cls.name).all()

    @classmethod
    def get_by_name(cls, name: str) -> "DatabaseTypeConfig":
        """根据名称获取单个配置.

        Args:
            name: 数据库类型唯一标识.

        Returns:
            DatabaseTypeConfig: 匹配到的配置实例,若不存在则返回 None.

        """
        return cls.query.filter_by(name=name).first()
