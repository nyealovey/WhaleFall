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
        path_obj = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self.config_file = path_obj
        self.config_path_str = str(path_obj)
        self.filter_rules = self._load_filter_rules()

    def _load_filter_rules(self) -> dict[str, dict[str, Any]]:
        """从配置文件加载过滤规则配置。

        Returns:
            dict[str, dict[str, Any]]: 以数据库类型为键的过滤规则集合。

        Raises:
            FileNotFoundError: 当配置文件不存在时抛出。
            ValueError: YAML 解析失败或缺少必需节点时抛出。

        """
        if not self.config_file.exists():
            logger.error(f"账户过滤规则配置文件不存在: {self.config_path_str}")
            raise FileNotFoundError(f"账户过滤规则配置文件不存在: {self.config_path_str}")

        try:
            with self.config_file.open(encoding="utf-8") as config_buffer:
                config = yaml.safe_load(config_buffer) or {}

            if "account_filters" not in config:
                logger.error("配置文件格式错误，缺少 account_filters 节点")
                raise ValueError("配置文件格式错误，缺少 account_filters 节点")

            filter_rules = config["account_filters"] or {}
            logger.info(f"成功加载账户过滤规则配置文件: {self.config_path_str}")
            logger.info(f"加载的数据库类型: {list(filter_rules.keys())}")

            return filter_rules

        except yaml.YAMLError as exc:
            logger.exception(f"解析配置文件失败: {exc}")
            raise ValueError(f"解析配置文件失败: {exc}") from exc
        except Exception as exc:
            logger.exception(f"加载过滤规则配置文件失败: {exc}")
            raise

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
        except Exception as exc:
            logger.exception(f"模式匹配失败: {pattern} -> {text}, 错误: {exc}")
            return False

    def get_filter_rules(self, db_type: str | None = None) -> dict[str, Any]:
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


# 全局实例
database_filter_manager = DatabaseFilterManager()
