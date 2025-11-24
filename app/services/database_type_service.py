"""
鲸落 - 数据库类型管理服务
提供数据库类型的CRUD操作和业务逻辑
"""

from typing import Any

from app.models.database_type_config import DatabaseTypeConfig


class DatabaseTypeService:
    """数据库类型管理服务。

    提供数据库类型的查询和表单数据生成功能。
    """

    @staticmethod
    def get_all_types() -> list[DatabaseTypeConfig]:
        """获取所有数据库类型配置。

        Returns:
            按排序顺序和名称排序的数据库类型配置列表。
        """
        return DatabaseTypeConfig.query.order_by(DatabaseTypeConfig.sort_order, DatabaseTypeConfig.name).all()

    @staticmethod
    def get_active_types() -> list[DatabaseTypeConfig]:
        """获取启用的数据库类型。

        Returns:
            启用状态的数据库类型配置列表。
        """
        return DatabaseTypeConfig.get_active_types()

    @staticmethod
    def get_type_by_name(name: str) -> DatabaseTypeConfig | None:
        """根据名称获取数据库类型。

        Args:
            name: 数据库类型名称，如 'mysql'、'postgresql'。

        Returns:
            匹配的数据库类型配置，如果不存在返回 None。
        """
        return DatabaseTypeConfig.get_by_name(name)

    @staticmethod
    def get_database_types_for_form() -> list[dict[str, Any]]:
        """获取用于表单的数据库类型列表。

        Returns:
            包含表单所需字段的字典列表，格式如下：
            [
                {
                    'value': 'mysql',
                    'text': 'MySQL',
                    'icon': 'fa-database',
                    'color': 'success'
                },
                ...
            ]
        """
        types = DatabaseTypeService.get_active_types()
        return [
            {
                "value": config.name,
                "text": config.display_name,
                "icon": config.icon,
                "color": config.color,
            }
            for config in types
        ]
