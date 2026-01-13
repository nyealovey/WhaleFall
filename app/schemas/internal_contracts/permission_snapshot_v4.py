"""Permission snapshot v4 internal contract adapter/normalizer.

目的：
- 收敛 `permission_snapshot(v4)` 的形状兼容与类型规整到 schema 层单入口。
- 业务层只消费 canonical 形状，避免在 Service 内出现 `or` 兜底链与字段 alias。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.constants import DatabaseType

JsonDict = dict[str, Any]


def _normalize_str_list(value: object, *, dict_key: str | None = None) -> list[str]:
    if not isinstance(value, list):
        return []

    output: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            output.append(item)
            continue
        if dict_key and isinstance(item, dict):
            candidate = item.get(dict_key)
            if isinstance(candidate, str) and candidate:
                output.append(candidate)
    return output


def normalize_permission_snapshot_categories_v4(db_type: str, categories: Mapping[str, object]) -> JsonDict:
    """Normalize v4 snapshot categories into canonical shapes (single entry).

    当前收敛范围（与审计报告 P0 对齐）：
    - PostgreSQL: `predefined_roles` 允许 list[str] 或 list[{"role": str}]
    - SQL Server: `server_roles`/`database_roles` 允许 list[str] 或 list[{"name": str}]（以及 dict 映射到这些 list）
    - Oracle: `oracle_roles` 允许 list[str] 或 list[{"role": str}]
    """

    normalized: JsonDict = dict(categories)

    if db_type == DatabaseType.POSTGRESQL:
        if "predefined_roles" in categories:
            normalized["predefined_roles"] = _normalize_str_list(categories.get("predefined_roles"), dict_key="role")
        return normalized

    if db_type == DatabaseType.SQLSERVER:
        if "server_roles" in categories:
            normalized["server_roles"] = _normalize_str_list(categories.get("server_roles"), dict_key="name")

        if "database_roles" in categories:
            database_roles_value = categories.get("database_roles")
            if isinstance(database_roles_value, dict):
                normalized_database_roles: dict[str, list[str]] = {}
                for key, entry in database_roles_value.items():
                    if not isinstance(key, str) or not key:
                        continue
                    normalized_database_roles[key] = _normalize_str_list(entry, dict_key="name")
                normalized["database_roles"] = normalized_database_roles
            elif isinstance(database_roles_value, list):
                normalized["database_roles"] = {"__all__": _normalize_str_list(database_roles_value, dict_key="name")}
        return normalized

    if db_type == DatabaseType.ORACLE:
        if "oracle_roles" in categories:
            normalized["oracle_roles"] = _normalize_str_list(categories.get("oracle_roles"), dict_key="role")
        return normalized

    return normalized
