"""
鲸落 - 数据库过滤规则管理器
专门用于数据库账户同步时的过滤规则管理
"""

import re
from pathlib import Path
from typing import Any

import yaml

from app.utils.safe_query_builder import build_safe_filter_conditions
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "account_filters.yaml"


class DatabaseFilterManager:
    """数据库过滤规则管理器"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config_file = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self.filter_rules = self._load_filter_rules()

    def _load_filter_rules(self) -> dict[str, dict[str, Any]]:
        """从配置文件加载过滤规则配置"""
        if not self.config_file.exists():
            logger.error("账户过滤规则配置文件不存在: %s", self.config_file)
            raise FileNotFoundError(f"账户过滤规则配置文件不存在: {self.config_file}")

        try:
            with self.config_file.open(encoding="utf-8") as config_buffer:
                config = yaml.safe_load(config_buffer) or {}

            if "account_filters" not in config:
                logger.error("配置文件格式错误，缺少 account_filters 节点")
                raise ValueError("配置文件格式错误，缺少 account_filters 节点")

            filter_rules = config["account_filters"] or {}
            logger.info("成功加载账户过滤规则配置文件: %s", self.config_file)
            logger.info("加载的数据库类型: %s", list(filter_rules.keys()))

            return filter_rules

        except yaml.YAMLError as exc:
            logger.error("解析配置文件失败: %s", exc)
            raise ValueError(f"解析配置文件失败: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            logger.error("加载过滤规则配置文件失败: %s", exc)
            raise

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
            logger.debug("账户 %s 是PostgreSQL的默认超级用户，强制包含", username)
            return True

        # 检查排除用户列表
        if username in rules.get("exclude_users", []):
            logger.debug("账户 %s 在排除用户列表中", username)
            return False

        # 检查排除模式
        for pattern in rules.get("exclude_patterns", []):
            if self._match_pattern(username, pattern):
                logger.debug("账户 %s 匹配排除模式 %s", username, pattern)
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
        except Exception as exc:  # noqa: BLE001
            logger.error("模式匹配失败: %s -> %s, 错误: %s", pattern, text, exc)
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
                logger.info("已更新 %s 数据库过滤规则", db_type)
                return True
            logger.error("不支持的数据库类型: %s", db_type)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("更新过滤规则失败: %s", exc)
            return False

    def save_filter_rules_to_file(self, file_path: str | Path | None = None) -> bool:
        """
        保存过滤规则到配置文件

        Args:
            file_path: 配置文件路径

        Returns:
            bool: 是否保存成功
        """
        try:
            target_path = Path(file_path) if file_path else self.config_file

            # 确保目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # 准备保存的数据
            save_data = {
                "account_filters": self.filter_rules,
                "version": "1.0",
                "description": "鲸落账户过滤规则配置",
            }

            with target_path.open("w", encoding="utf-8") as output_buffer:
                yaml.safe_dump(save_data, output_buffer, default_flow_style=False, allow_unicode=True, indent=2)

            logger.info("过滤规则已保存到 %s", target_path)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("保存过滤规则失败: %s", exc)
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
