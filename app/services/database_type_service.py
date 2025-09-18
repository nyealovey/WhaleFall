"""
泰摸鱼吧 - 数据库类型管理服务
提供数据库类型的CRUD操作和业务逻辑
"""

from typing import Any

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.database_type_config import DatabaseTypeConfig
from app.utils.structlog_config import get_api_logger, log_error, log_info

api_logger = get_api_logger()


class DatabaseTypeService:
    """数据库类型管理服务"""

    @staticmethod
    def get_all_types() -> list[DatabaseTypeConfig]:
        """获取所有数据库类型配置"""
        return DatabaseTypeConfig.query.order_by(DatabaseTypeConfig.sort_order, DatabaseTypeConfig.name).all()

    @staticmethod
    def get_active_types() -> list[DatabaseTypeConfig]:
        """获取启用的数据库类型"""
        return DatabaseTypeConfig.get_active_types()

    @staticmethod
    def get_type_by_name(name: str) -> DatabaseTypeConfig | None:
        """根据名称获取数据库类型"""
        return DatabaseTypeConfig.get_by_name(name)

    @staticmethod
    def get_type_by_id(type_id: int) -> DatabaseTypeConfig | None:
        """根据ID获取数据库类型"""
        return DatabaseTypeConfig.query.get(type_id)

    @staticmethod
    def create_type(data: dict[str, Any]) -> dict[str, Any]:
        """创建数据库类型配置"""
        try:
            # 验证必填字段
            required_fields = [
                "name",
                "display_name",
                "driver",
                "default_port",
                "default_schema",
            ]
            for field in required_fields:
                if not data.get(field):
                    return {"success": False, "message": f"缺少必填字段: {field}"}

            # 检查名称是否已存在
            if DatabaseTypeConfig.get_by_name(data["name"]):
                return {"success": False, "message": "数据库类型名称已存在"}

            # 创建配置
            config = DatabaseTypeConfig(
                name=data["name"],
                display_name=data["display_name"],
                driver=data["driver"],
                default_port=data["default_port"],
                default_schema=data["default_schema"],
                connection_timeout=data.get("connection_timeout", 30),
                description=data.get("description", ""),
                icon=data.get("icon", "fa-database"),
                color=data.get("color", "primary"),
                is_active=data.get("is_active", True),
                sort_order=data.get("sort_order", 0),
            )
            # 设置特性列表
            config.features_list = data.get("features", [])

            db.session.add(config)
            db.session.commit()

            log_info(
                "创建数据库类型",
                module="database_type",
                type_name=config.name,
                display_name=config.display_name,
                driver=config.driver,
            )

            return {
                "success": True,
                "message": "数据库类型创建成功",
                "data": config.to_dict(),
            }

        except IntegrityError as e:
            db.session.rollback()
            log_error(f"数据库类型创建失败 - 完整性错误: {e}")
            return {"success": False, "message": "数据库类型名称已存在"}
        except Exception as e:
            db.session.rollback()
            log_error(f"数据库类型创建失败: {e}")
            return {"success": False, "message": f"创建失败: {str(e)}"}

    @staticmethod
    def update_type(type_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """更新数据库类型配置"""
        try:
            config = DatabaseTypeConfig.query.get(type_id)
            if not config:
                return {"success": False, "message": "数据库类型不存在"}

            # 系统内置类型只能修改部分字段
            if config.is_system:
                allowed_fields = [
                    "display_name",
                    "description",
                    "icon",
                    "color",
                    "is_active",
                    "sort_order",
                ]
                for key, value in data.items():
                    if key in allowed_fields:
                        setattr(config, key, value)
            else:
                # 自定义类型可以修改所有字段
                for key, value in data.items():
                    if hasattr(config, key) and key != "id":
                        setattr(config, key, value)

            db.session.commit()

            log_info(
                "更新数据库类型",
                module="database_type",
                type_id=type_id,
                type_name=config.name,
                changes=data,
            )

            return {
                "success": True,
                "message": "数据库类型更新成功",
                "data": config.to_dict(),
            }

        except Exception as e:
            db.session.rollback()
            log_error(f"数据库类型更新失败: {e}")
            return {"success": False, "message": f"更新失败: {str(e)}"}

    @staticmethod
    def delete_type(type_id: int) -> dict[str, Any]:
        """删除数据库类型配置"""
        try:
            config = DatabaseTypeConfig.query.get(type_id)
            if not config:
                return {"success": False, "message": "数据库类型不存在"}

            # 系统内置类型不能删除
            if config.is_system:
                return {"success": False, "message": "系统内置类型不能删除"}

            # 检查是否有实例使用此类型
            from app.models.instance import Instance

            instance_count = Instance.query.filter_by(db_type=config.name).count()
            if instance_count > 0:
                return {
                    "success": False,
                    "message": f"有 {instance_count} 个实例正在使用此数据库类型，无法删除",
                }

            db.session.delete(config)
            db.session.commit()

            log_info(
                "删除数据库类型",
                module="database_type",
                type_id=type_id,
                type_name=config.name,
            )

            return {"success": True, "message": "数据库类型删除成功"}

        except Exception as e:
            db.session.rollback()
            log_error(f"数据库类型删除失败: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}

    @staticmethod
    def toggle_status(type_id: int) -> dict[str, Any]:
        """切换数据库类型启用状态"""
        try:
            config = DatabaseTypeConfig.query.get(type_id)
            if not config:
                return {"success": False, "message": "数据库类型不存在"}

            config.is_active = not config.is_active
            db.session.commit()

            log_info(
                "切换数据库类型状态",
                module="database_type",
                type_id=type_id,
                type_name=config.name,
                new_status=config.is_active,
            )

            return {
                "success": True,
                "message": f"数据库类型已{'启用' if config.is_active else '禁用'}",
                "data": config.to_dict(),
            }

        except Exception as e:
            db.session.rollback()
            log_error(f"数据库类型状态切换失败: {e}")
            return {"success": False, "message": f"状态切换失败: {str(e)}"}

    @staticmethod
    def init_default_types() -> None:
        """初始化默认数据库类型"""
        default_types = [
            {
                "name": "mysql",
                "display_name": "MySQL",
                "driver": "pymysql",
                "default_port": 3306,
                "default_schema": "information_schema",
                "description": "MySQL数据库",
                "icon": "fa-database",
                "color": "primary",
                "features": ["replication", "partitioning", "json"],
                "is_system": True,
                "sort_order": 1,
            },
            {
                "name": "postgresql",
                "display_name": "PostgreSQL",
                "driver": "psycopg",
                "default_port": 5432,
                "default_schema": "public",
                "description": "PostgreSQL数据库",
                "icon": "fa-elephant",
                "color": "info",
                "features": ["jsonb", "arrays", "full_text_search"],
                "is_system": True,
                "sort_order": 2,
            },
            {
                "name": "sqlserver",
                "display_name": "SQL Server",
                "driver": "pymssql",
                "default_port": 1433,
                "default_schema": "dbo",
                "description": "Microsoft SQL Server数据库",
                "icon": "fa-windows",
                "color": "success",
                "features": ["clustering", "mirroring", "always_on"],
                "is_system": True,
                "sort_order": 3,
            },
            {
                "name": "oracle",
                "display_name": "Oracle",
                "driver": "oracledb",
                "default_port": 1521,
                "default_schema": "SYS",
                "description": "Oracle数据库",
                "icon": "fa-database",
                "color": "warning",
                "features": ["rac", "asm", "flashback"],
                "is_system": True,
                "sort_order": 4,
            },
        ]

        for type_data in default_types:
            if not DatabaseTypeConfig.get_by_name(type_data["name"]):
                config = DatabaseTypeConfig(
                    name=type_data["name"],
                    display_name=type_data["display_name"],
                    driver=type_data["driver"],
                    default_port=type_data["default_port"],
                    default_schema=type_data["default_schema"],
                    connection_timeout=type_data.get("connection_timeout", 30),
                    description=type_data.get("description", ""),
                    icon=type_data.get("icon", "fa-database"),
                    color=type_data.get("color", "primary"),
                    is_active=type_data.get("is_active", True),
                    is_system=type_data.get("is_system", False),
                    sort_order=type_data.get("sort_order", 0),
                )
                # 设置特性列表
                config.features_list = type_data.get("features", [])
                db.session.add(config)

        try:
            db.session.commit()
            api_logger.info(
                "database_type_init",
                user_id=None,
                details={"count": len(default_types)},
            )
        except Exception as e:
            db.session.rollback()
            log_error(f"初始化默认数据库类型失败: {e}")

    @staticmethod
    def get_database_types_for_form() -> list[dict[str, Any]]:
        """获取用于表单的数据库类型列表"""
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
