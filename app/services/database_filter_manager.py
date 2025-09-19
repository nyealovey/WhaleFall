"""
鲸落 - 数据库过滤规则管理器
专门用于数据库账户同步时的过滤规则管理
"""

import os
import re
from typing import Any

import yaml

from app.utils.safe_query_builder import build_safe_filter_conditions
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


class DatabaseFilterManager:
    """数据库过滤规则管理器"""

    def __init__(self) -> None:
        self.filter_rules = self._load_filter_rules()

    def _load_filter_rules(self) -> dict[str, dict[str, Any]]:
        """加载过滤规则配置"""
        # 默认规则配置
        default_rules = {
            "mysql": {
                "exclude_users": [],
                "exclude_patterns": [],
                "exclude_roles": [],
                "include_only": False,
                "description": "MySQL数据库过滤规则",
            },
            "postgresql": {
                "exclude_users": ["postgres", "rdsadmin", "rds_superuser"],
                "exclude_patterns": ["pg_%"],
                "exclude_roles": [],
                "include_only": False,
                "description": "PostgreSQL数据库过滤规则",
            },
            "sqlserver": {
                "exclude_users": ["public", "guest", "dbo"],
                "exclude_patterns": [
                    "##%",
                    "NT SERVICE\\%",
                    "NT AUTHORITY\\%",
                    "BUILTIN\\%",
                    "NT %",
                ],
                "exclude_roles": [],
                "include_only": False,
                "description": "SQL Server数据库过滤规则",
            },
            "oracle": {
                "exclude_users": [
                    "SCOTT",
                    "CTXSYS",
                    "EXFSYS",
                    "MDDATA",
                    "APPQOSSYS",
                    "OUTLN",
                    "DIP",
                    "TSMSYS",
                    "WMSYS",
                    "XDB",
                    "ANONYMOUS",
                    "ORDPLUGINS",
                    "ORDSYS",
                    "SI_INFORMTN_SCHEMA",
                    "MDSYS",
                    "OLAPSYS",
                    "SPATIAL_CSW_ADMIN_USR",
                    "SPATIAL_WFS_ADMIN_USR",
                    "APEX_PUBLIC_USER",
                    "APEX_030200",
                    "FLOWS_FILES",
                    "HR",
                    "OE",
                    "PM",
                    "IX",
                    "SH",
                    "BI",
                    "DEMO",
                    "ADMIN",
                    "AUDSYS",
                    "GSMADMIN_INTERNAL",
                    "GSMCATUSER",
                    "GSMUSER",
                    "LBACSYS",
                    "OJVMSYS",
                    "ORACLE_OCM",
                    "ORDDATA",
                    "ORDPLUGINS",
                    "ORDS_METADATA",
                    "ORDS_PUBLIC_USER",
                    "PDBADMIN",
                    "RDSADMIN",
                    "REMOTE_SCHEDULER_AGENT",
                    "SYSBACKUP",
                    "SYSDG",
                    "SYSKM",
                    "SYSRAC",
                    "SYS$UMF",
                    "XS$NULL",
                    "OWBSYS",
                    "OWBSYS_AUDIT",
                ],
                "exclude_patterns": [
                    "SYS$%",
                    "GSM%",
                    "XDB%",
                    "APEX%",
                    "ORD%",
                    "SPATIAL_%",
                ],
                "exclude_roles": [],
                "include_only": False,
                "description": "Oracle数据库过滤规则",
            },
        }

        # 尝试从配置文件加载
        config_file = "app/config/database_filters.yaml"
        if os.path.exists(config_file):
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if "database_filters" in config:
                        # 合并默认规则和配置文件规则
                        for db_type, rules in config["database_filters"].items():
                            if db_type in default_rules:
                                default_rules[db_type].update(rules)
                        logger.info("已加载数据库过滤规则配置文件")
                    else:
                        logger.warning("配置文件格式错误，使用默认规则")
            except Exception:
                logger.error("加载过滤规则配置文件失败: {e}，使用默认规则")
        else:
            logger.info("未找到过滤规则配置文件，使用默认规则")

        return default_rules

    def get_sql_filter_conditions(self, db_type: str, username_field: str = "username") -> str:
        """
        获取SQL过滤条件

        Args:
            db_type: 数据库类型 (mysql, postgresql, sqlserver, oracle)
            username_field: 用户名字段名，默认为'username'

        Returns:
            str: SQL WHERE条件字符串
        """
        rules = self.filter_rules.get(db_type, {})
        conditions = []

        # 排除特定用户
        exclude_users = rules.get("exclude_users", [])
        if exclude_users:
            # 转义单引号
            escaped_users = [user.replace("'", "''") for user in exclude_users]
            user_list = "', '".join(escaped_users)
            conditions.append(f"{username_field} NOT IN ('{user_list}')")

        # 排除模式匹配
        exclude_patterns = rules.get("exclude_patterns", [])
        for pattern in exclude_patterns:
            # 转义单引号
            escaped_pattern = pattern.replace("'", "''")
            conditions.append(f"{username_field} NOT LIKE '{escaped_pattern}'")

        # 如果没有任何条件，返回1=1（表示不过滤）
        return " AND ".join(conditions) if conditions else "1=1"

    def get_safe_sql_filter_conditions(self, db_type: str, username_field: str = "username") -> tuple[str, list[Any]]:
        """
        获取安全的SQL过滤条件（参数化查询）

        Args:
            db_type: 数据库类型 (mysql, postgresql, sqlserver, oracle)
            username_field: 用户名字段名，默认为'username'

        Returns:
            Tuple[str, List[Any]]: WHERE子句和参数列表
        """
        return build_safe_filter_conditions(db_type, username_field, self.filter_rules)

    def should_include_account(self, username: str, db_type: str) -> bool:
        """
        判断账户是否应该包含

        Args:
            username: 用户名
            db_type: 数据库类型

        Returns:
            bool: True表示应该包含，False表示应该排除
        """
        rules = self.filter_rules.get(db_type, {})

        # 特殊处理：PostgreSQL的postgres用户应该被包含
        if db_type == "postgresql" and username == "postgres":
            logger.debug("账户 {username} 是PostgreSQL的默认超级用户，强制包含")
            return True

        # 检查排除用户列表
        if username in rules.get("exclude_users", []):
            logger.debug("账户 {username} 在排除用户列表中")
            return False

        # 检查排除模式
        for pattern in rules.get("exclude_patterns", []):
            if self._match_pattern(username, pattern):
                logger.debug("账户 {username} 匹配排除模式 {pattern}")
                return False

        return True

    def _match_pattern(self, text: str, pattern: str) -> bool:
        """
        模式匹配（支持SQL LIKE语法）

        Args:
            text: 要匹配的文本
            pattern: SQL LIKE模式

        Returns:
            bool: 是否匹配
        """
        try:
            # 将SQL LIKE模式转换为正则表达式
            # % 匹配任意字符，_ 匹配单个字符
            regex_pattern = pattern.replace("%", ".*").replace("_", ".")
            # 添加行首和行尾锚点
            regex_pattern = f"^{regex_pattern}$"
            return bool(re.match(regex_pattern, text, re.IGNORECASE))
        except Exception:
            logger.error("模式匹配失败: {pattern} -> {text}, 错误: {e}")
            return False

    def get_filter_rules(self, db_type: str = None) -> dict[str, Any]:
        """
        获取过滤规则

        Args:
            db_type: 数据库类型，None表示获取所有规则

        Returns:
            Dict: 过滤规则
        """
        if db_type:
            return self.filter_rules.get(db_type, {})
        return self.filter_rules

    def update_filter_rules(self, db_type: str, rules: dict[str, Any]) -> bool:
        """
        更新过滤规则

        Args:
            db_type: 数据库类型
            rules: 新的规则配置

        Returns:
            bool: 是否更新成功
        """
        try:
            if db_type in self.filter_rules:
                self.filter_rules[db_type].update(rules)
                logger.info("已更新 {db_type} 数据库过滤规则")
                return True
            logger.error("不支持的数据库类型: {db_type}")
            return False
        except Exception:
            logger.error("更新过滤规则失败: {e}")
            return False

    def save_filter_rules_to_file(self, file_path: str = "app/config/database_filters.yaml") -> bool:
        """
        保存过滤规则到配置文件

        Args:
            file_path: 配置文件路径

        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 准备保存的数据
            save_data = {
                "database_filters": self.filter_rules,
                "version": "1.0",
                "description": "鲸落数据库过滤规则配置",
            }

            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(save_data, f, default_flow_style=False, allow_unicode=True, indent=2)

            logger.info("过滤规则已保存到 {file_path}")
            return True
        except Exception:
            logger.error("保存过滤规则失败: {e}")
            return False

    def get_filter_statistics(self, db_type: str = None) -> dict[str, Any]:
        """
        获取过滤规则统计信息

        Args:
            db_type: 数据库类型，None表示获取所有统计

        Returns:
            Dict: 统计信息
        """
        if db_type:
            rules = self.filter_rules.get(db_type, {})
            return {
                "exclude_users_count": len(rules.get("exclude_users", [])),
                "exclude_patterns_count": len(rules.get("exclude_patterns", [])),
                "exclude_roles_count": len(rules.get("exclude_roles", [])),
                "include_only": rules.get("include_only", False),
            }
        stats = {}
        for db_type, rules in self.filter_rules.items():
            stats[db_type] = {
                "exclude_users_count": len(rules.get("exclude_users", [])),
                "exclude_patterns_count": len(rules.get("exclude_patterns", [])),
                "exclude_roles_count": len(rules.get("exclude_roles", [])),
                "include_only": rules.get("include_only", False),
            }
        return stats


# 全局实例
database_filter_manager = DatabaseFilterManager()
