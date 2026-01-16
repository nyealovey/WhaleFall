"""Permission snapshot v4 internal contract adapter/normalizer.

目的：
- 收敛 `permission_snapshot(v4)` 的形状兼容与类型规整到 schema 层单入口。
- 业务层只消费 canonical 形状，避免在 Service 内出现 `or` 兜底链与字段 alias。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.constants import DatabaseType
from app.core.types import InternalContractResult, build_internal_contract_error, build_internal_contract_ok

JsonDict = dict[str, Any]

PERMISSION_SNAPSHOT_VERSION_V4 = 4
PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS: list[int] = [PERMISSION_SNAPSHOT_VERSION_V4]

INTERNAL_CONTRACT_INVALID_PAYLOAD = "INTERNAL_CONTRACT_INVALID_PAYLOAD"
INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS = "INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS"
INTERNAL_CONTRACT_UNKNOWN_VERSION = "INTERNAL_CONTRACT_UNKNOWN_VERSION"


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


def parse_permission_snapshot_categories_v4(snapshot: object) -> InternalContractResult:
    """解析 permission_snapshot(v4) 的 categories.

    说明:
    - 该函数用于 internal contract 的读入口（单入口 canonicalization 之前的版本/形状判定）。
    - 未知版本默认应 fail-fast；若调用方是 best-effort 链路，可使用本函数返回的错误结构做显式失败。
    """
    contract = "permission_snapshot.categories"

    if not isinstance(snapshot, Mapping):
        return build_internal_contract_error(
            contract=contract,
            version=None,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_INVALID_PAYLOAD,
            message="permission_snapshot 必须为 dict",
        )

    raw_version = snapshot.get("version")
    version = raw_version if type(raw_version) is int else None
    if version is None:
        return build_internal_contract_error(
            contract=contract,
            version=None,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS,
            message="permission_snapshot.version 缺失或不是整数",
        )
    if version != PERMISSION_SNAPSHOT_VERSION_V4:
        return build_internal_contract_error(
            contract=contract,
            version=version,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_UNKNOWN_VERSION,
            message=f"permission_snapshot.version={version} 不受支持",
        )

    categories = snapshot.get("categories")
    if not isinstance(categories, dict):
        return build_internal_contract_error(
            contract=contract,
            version=version,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS,
            message="permission_snapshot.categories 缺失或不是 dict",
        )

    return build_internal_contract_ok(
        contract=contract,
        version=version,
        supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
        data=dict(categories),
    )


def parse_permission_snapshot_type_specific_v4(snapshot: object) -> InternalContractResult:
    """解析 permission_snapshot(v4) 的 type_specific.

    说明:
    - 该函数用于 internal contract 的读入口（单入口 canonicalization 之前的版本/形状判定）。
    - 未知版本默认应 fail-fast；若调用方是 best-effort 链路，可使用本函数返回的错误结构做显式失败。
    """
    contract = "permission_snapshot.type_specific"

    if not isinstance(snapshot, Mapping):
        return build_internal_contract_error(
            contract=contract,
            version=None,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_INVALID_PAYLOAD,
            message="permission_snapshot 必须为 dict",
        )

    raw_version = snapshot.get("version")
    version = raw_version if type(raw_version) is int else None
    if version is None:
        return build_internal_contract_error(
            contract=contract,
            version=None,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS,
            message="permission_snapshot.version 缺失或不是整数",
        )
    if version != PERMISSION_SNAPSHOT_VERSION_V4:
        return build_internal_contract_error(
            contract=contract,
            version=version,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_UNKNOWN_VERSION,
            message=f"permission_snapshot.version={version} 不受支持",
        )

    type_specific = snapshot.get("type_specific")
    if not isinstance(type_specific, dict):
        return build_internal_contract_error(
            contract=contract,
            version=version,
            supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
            error_code=INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS,
            message="permission_snapshot.type_specific 缺失或不是 dict",
        )

    return build_internal_contract_ok(
        contract=contract,
        version=version,
        supported_versions=PERMISSION_SNAPSHOT_SUPPORTED_VERSIONS,
        data=dict(type_specific),
    )


def normalize_permission_snapshot_type_specific_v4(db_type: str, type_specific: Mapping[str, object]) -> JsonDict:
    """Normalize v4 snapshot type_specific into canonical shapes (single entry).

    当前 v4 约定：`type_specific` 为 mapping，按 `db_type` 分桶：
    - type_specific[db_type] 为 dict（不同数据库的特有字段集合）
    - 该 normalize 函数返回单一 db_type 的 canonical dict（未知/非法形状返回空 dict）
    """
    entry = type_specific.get(db_type)
    if isinstance(entry, dict):
        return dict(entry)
    return {}


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
