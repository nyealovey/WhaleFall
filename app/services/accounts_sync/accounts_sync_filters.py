"""鲸落 - 数据库过滤规则管理器.

专门用于数据库账户同步时的过滤规则管理,提供参数化过滤条件的统一加载与复用。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias, cast

import yaml

from app.utils.safe_query_builder import build_safe_filter_conditions
from app.utils.structlog_config import get_system_logger

if TYPE_CHECKING:
    from app.core.types import JsonDict
else:
    JsonDict = dict[str, Any]

logger = get_system_logger()

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "account_filters.yaml"

FilterRule = JsonDict
DatabaseFilterRules: TypeAlias = dict[str, Mapping[str, Sequence[str]]]


class DatabaseFilterManager:
    """数据库过滤规则管理器."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """加载过滤配置并准备规则字典."""
        path_obj = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self.config_file = path_obj
        self.config_path_str = str(path_obj)
        self.filter_rules: DatabaseFilterRules = self._load_filter_rules()

    def _load_filter_rules(self) -> DatabaseFilterRules:
        """从配置文件加载过滤规则配置.

        Returns:
            DatabaseFilterRules: 以数据库类型为键的过滤规则集合.

        Raises:
            FileNotFoundError: 当配置文件不存在时抛出.
            ValueError: YAML 解析失败或缺少必需节点时抛出.

        """
        if not self.config_file.exists():
            logger.error("账户过滤规则配置文件不存在", config_path=self.config_path_str)
            msg = f"账户过滤规则配置文件不存在: {self.config_path_str}"
            raise FileNotFoundError(msg)

        try:
            with self.config_file.open(encoding="utf-8") as config_buffer:
                config = yaml.safe_load(config_buffer) or {}

            if "account_filters" not in config:
                logger.error("配置文件格式错误,缺少 account_filters 节点")
                msg = "配置文件格式错误,缺少 account_filters 节点"
                raise ValueError(msg)

            raw_rules = config["account_filters"] or {}
            filter_rules = cast("DatabaseFilterRules", raw_rules)
            logger.info("成功加载账户过滤规则配置文件", config_path=self.config_path_str)
            logger.info(
                "加载的数据库类型",
                config_path=self.config_path_str,
                db_types=list(filter_rules.keys()),
            )
        except yaml.YAMLError as exc:
            logger.exception("解析配置文件失败")
            msg = f"解析配置文件失败: {exc}"
            raise ValueError(msg) from exc
        except OSError as exc:
            logger.exception("加载过滤规则配置文件失败", error=str(exc))
            raise
        else:
            return filter_rules

    def get_safe_sql_filter_conditions(
        self,
        db_type: str,
        username_field: str = "username",
    ) -> tuple[str, list[str]] | tuple[str, dict[str, str]]:
        """获取安全的 SQL 过滤条件(参数化查询).

        Args:
            db_type: 数据库类型 (mysql, postgresql, sqlserver, oracle)。
            username_field: 用户名字段名,默认为 'username'。

        Returns:
            tuple[str, list[str]] | tuple[str, dict[str, str]]: WHERE 子句和参数列表/字典.

        """
        where_clause, params = build_safe_filter_conditions(db_type, username_field, self.filter_rules)
        if isinstance(params, Mapping):
            return where_clause, cast("dict[str, str]", dict(params))
        return where_clause, cast("list[str]", list(params))

    def _match_pattern(self, text: str, pattern: str) -> bool:
        """模式匹配(支持 SQL LIKE 语法).

        Args:
            text: 要匹配的文本.
            pattern: SQL LIKE 模式.

        Returns:
            bool: 是否匹配.

        """
        try:
            regex_pattern = pattern.replace("%", ".*").replace("_", ".")
            regex_pattern = f"^{regex_pattern}$"
            return bool(re.match(regex_pattern, text, re.IGNORECASE))
        except re.error:
            logger.exception("模式匹配失败", pattern=pattern, text=text)
            return False

    def get_filter_rules(self, db_type: str | None = None) -> Mapping[str, Sequence[str]] | DatabaseFilterRules:
        """获取过滤规则.

        Args:
            db_type: 数据库类型,None 表示获取所有规则.

        Returns:
            过滤规则映射或某一数据库的规则字典.

        """
        if db_type:
            return self.filter_rules.get(db_type, {})
        return self.filter_rules


# 全局实例
database_filter_manager = DatabaseFilterManager()
