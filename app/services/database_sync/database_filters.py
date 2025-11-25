"""容量同步使用的数据库级过滤工具。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "database_filters.yaml"


@dataclass(frozen=True)
class _CompiledRule:
    raw: str
    regex: re.Pattern[str]


class DatabaseSyncFilterManager:
    """负责加载数据库发现/容量同步所需的过滤配置。"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._normalized_rules: dict[str, dict[str, Any]] = {}
        self.reload()

    @property
    def config_path(self) -> Path:
        """返回当前生效的配置文件路径。"""

        return self._config_path

    def reload(self) -> None:
        """从磁盘重新加载过滤配置。"""
        if not self._config_path.exists():
            raise FileNotFoundError(f"数据库过滤配置文件不存在: {self._config_path}")

        try:
            with self._config_path.open(encoding="utf-8") as buffer:
                raw_config = yaml.safe_load(buffer) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            logger.error("解析数据库过滤配置失败", error=str(exc))
            raise ValueError(f"解析数据库过滤配置失败: {exc}") from exc

        filters = raw_config.get("database_filters") or {}
        normalized: dict[str, dict[str, Any]] = {}

        for db_type, rule in filters.items():
            if not isinstance(rule, Mapping):
                logger.warning("忽略格式异常的数据库过滤规则", db_type=db_type)
                continue

            exact = {
                str(name).lower()
                for name in rule.get("exclude_databases") or []
                if isinstance(name, str) and name.strip()
            }

            compiled_patterns: list[_CompiledRule] = []
            for pattern in rule.get("exclude_patterns") or []:
                if not isinstance(pattern, str) or not pattern.strip():
                    continue
                regex = self._compile_pattern(pattern)
                compiled_patterns.append(_CompiledRule(pattern, regex))

            normalized[db_type.lower()] = {
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
        escaped = re.escape(pattern)
        escaped = escaped.replace(r"\%", ".*").replace(r"\_", ".")
        regex = f"^{escaped}$"
        return re.compile(regex, re.IGNORECASE)

    def should_exclude_database(self, instance: Any, database_name: str | None) -> tuple[bool, str | None]:
        """判断给定实例下的数据库是否需要被过滤。"""
        if not database_name:
            return False, None

        db_type = (getattr(instance, "db_type", None) or "").lower()
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

    def filter_database_names(self, instance: Any, names: Iterable[str]) -> tuple[list[str], list[str]]:
        """过滤数据库名称，返回保留与排除列表。"""
        allowed: list[str] = []
        excluded: list[str] = []
        for name in names:
            should_exclude, _ = self.should_exclude_database(instance, name)
            if should_exclude:
                excluded.append(name)
            else:
                allowed.append(name)
        return allowed, excluded

    def filter_capacity_payload(self, instance: Any, payload: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        """过滤容量采集结果，返回保留记录与被排除的库名。"""
        kept: list[dict[str, Any]] = []
        excluded: list[str] = []
        for row in payload:
            name = row.get("database_name")
            should_exclude, _ = self.should_exclude_database(instance, name)
            if should_exclude:
                excluded.append(str(name))
            else:
                kept.append(row)
        return kept, excluded


database_sync_filter_manager = DatabaseSyncFilterManager()

__all__ = ["DatabaseSyncFilterManager", "database_sync_filter_manager"]
