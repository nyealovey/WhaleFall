"""容量同步使用的数据库级过滤工具."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import yaml
from pydantic import ValidationError as PydanticValidationError

from app.schemas.yaml_configs import DatabaseFiltersConfigFile
from app.utils.structlog_config import get_system_logger

if TYPE_CHECKING:
    from app.models.instance import Instance

logger = get_system_logger()

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "database_filters.yaml"


@dataclass(frozen=True)
class _CompiledRule:
    raw: str
    regex: re.Pattern[str]


class _FilterRule(TypedDict):
    exclude_databases: set[str]
    exclude_patterns: list[_CompiledRule]


class DatabaseSyncFilterManager:
    """负责加载数据库发现/容量同步所需的过滤配置."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        """初始化过滤配置管理器,支持自定义配置路径."""
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._normalized_rules: dict[str, _FilterRule] = {}
        self.reload()

    @property
    def config_path(self) -> Path:
        """返回当前生效的配置文件路径.

        Returns:
            Path: 数据库过滤配置所在路径.

        """
        return self._config_path

    def reload(self) -> None:
        """从磁盘重新加载过滤配置.

        Returns:
            None: 配置刷新完成后返回.

        """
        if not self._config_path.exists():
            msg = f"数据库过滤配置文件不存在: {self._config_path}"
            raise FileNotFoundError(msg)

        try:
            with self._config_path.open(encoding="utf-8") as buffer:
                raw_config = yaml.safe_load(buffer)
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            logger.exception("解析数据库过滤配置失败", error=str(exc))
            msg = f"解析数据库过滤配置失败: {exc}"
            raise ValueError(msg) from exc

        try:
            parsed = DatabaseFiltersConfigFile.model_validate(raw_config)
        except PydanticValidationError as exc:
            logger.exception("数据库过滤配置格式错误", error=str(exc), path=str(self._config_path))
            msg = f"数据库过滤配置格式错误: {exc}"
            raise ValueError(msg) from exc

        filters = parsed.database_filters
        normalized: dict[str, _FilterRule] = {}

        for db_type, rule in filters.items():
            exact = {name.lower() for name in rule.exclude_databases}

            compiled_patterns: list[_CompiledRule] = []
            for pattern in rule.exclude_patterns:
                regex = self._compile_pattern(pattern)
                compiled_patterns.append(_CompiledRule(pattern, regex))

            normalized[db_type] = {
                "exclude_databases": exact,
                "exclude_patterns": compiled_patterns,
            }

        self._normalized_rules = normalized
        logger.info(
            "database_filter_config_loaded",
            path=str(self._config_path),
            db_types=list(normalized.keys()),
        )

    def _compile_pattern(self, pattern: str) -> re.Pattern[str]:
        """将 LIKE 风格的模式转换为正则表达式.

        Args:
            pattern: 包含 %/_ 通配符的模式字符串.

        Returns:
            Pattern[str]: 忽略大小写的正则表达式.

        """
        parts: list[str] = []
        for char in pattern:
            if char == "%":
                parts.append(".*")
            elif char == "_":
                parts.append(".")
            else:
                parts.append(re.escape(char))
        regex = f"^{''.join(parts)}$"
        return re.compile(regex, re.IGNORECASE)

    def should_exclude_database(self, instance: Instance, database_name: str | None) -> tuple[bool, str | None]:
        """判断给定实例下的数据库是否需要被过滤.

        Args:
            instance: 数据库实例对象.
            database_name: 需要检测的数据库名称.

        Returns:
            tuple[bool, str | None]: (是否排除, 命中规则标识).

        """
        if not database_name:
            return False, None

        db_type_value = getattr(instance, "db_type", None)
        db_type = "" if db_type_value is None else str(db_type_value).lower()
        if not db_type:
            return False, None

        rules = self._normalized_rules.get(db_type)
        if not rules:
            return False, None

        name_lower = database_name.lower()
        if name_lower in rules["exclude_databases"]:
            return True, "exclude_database"

        for compiled in rules["exclude_patterns"]:
            if compiled.regex.match(database_name):
                return True, f"exclude_pattern:{compiled.raw}"

        return False, None

    def filter_database_names(self, instance: Instance, names: Iterable[str]) -> tuple[list[str], list[str]]:
        """过滤数据库名称,返回保留与排除列表.

        Args:
            instance: 数据库实例对象.
            names: 待过滤的数据库名称集合.

        Returns:
            tuple[list[str], list[str]]: (允许的名称, 被排除的名称).

        """
        allowed: list[str] = []
        excluded: list[str] = []
        for name in names:
            should_exclude, _ = self.should_exclude_database(instance, name)
            if should_exclude:
                excluded.append(name)
            else:
                allowed.append(name)
        return allowed, excluded

    def filter_capacity_payload(
        self,
        instance: Instance,
        payload: Sequence[dict[str, object]],
    ) -> tuple[list[dict[str, object]], list[str]]:
        """过滤容量采集结果,返回保留记录与被排除的库名.

        Args:
            instance: 数据库实例对象.
            payload: 容量数据行列表.

        Returns:
            tuple[list[dict[str, object]], list[str]]: (保留的记录, 被排除的数据库名称).

        """
        kept: list[dict[str, object]] = []
        excluded: list[str] = []
        for row in payload:
            raw_name = row.get("database_name")
            database_name = str(raw_name) if raw_name is not None else None
            should_exclude, _ = self.should_exclude_database(instance, database_name)
            if should_exclude:
                excluded.append(database_name if database_name is not None else "")
            else:
                kept.append(row)
        return kept, excluded


database_sync_filter_manager = DatabaseSyncFilterManager()

__all__ = ["DatabaseSyncFilterManager", "database_sync_filter_manager"]
