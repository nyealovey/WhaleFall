"""Adapt v4 snapshot view into legacy permission fields used by the UI/API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.constants import DatabaseType


def _ensure_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _ensure_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _extract_privilege_list(value: object) -> list[str]:
    if isinstance(value, list):
        return _ensure_str_list(value)
    if isinstance(value, dict):
        granted = value.get("granted")
        if isinstance(granted, list):
            return _ensure_str_list(granted)
        # fallback: {"SELECT": true}
        return [key for key, enabled in value.items() if isinstance(key, str) and enabled]
    return []


def _extract_mapping_of_lists(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}

    output: dict[str, list[str]] = {}
    for key, entry in value.items():
        if not isinstance(key, str) or not key:
            continue
        if isinstance(entry, list):
            output[key] = _ensure_str_list(entry)
            continue
        if isinstance(entry, dict):
            output[key] = _extract_privilege_list(entry)
    return output


def build_ledger_permissions_payload(snapshot_view: Mapping[str, object], db_type: str) -> dict[str, Any]:
    """Return legacy-shaped permissions payload for permission modal rendering."""
    categories = snapshot_view.get("categories")
    if not isinstance(categories, dict):
        return {}

    normalized_db_type = (db_type or "").lower()
    if normalized_db_type == DatabaseType.MYSQL:
        return {
            "global_privileges": _extract_privilege_list(categories.get("global_privileges")),
            "database_privileges": _extract_mapping_of_lists(categories.get("database_privileges")),
        }

    if normalized_db_type == DatabaseType.POSTGRESQL:
        return {
            "predefined_roles": _ensure_str_list(categories.get("predefined_roles")),
            "role_attributes": _ensure_dict(categories.get("role_attributes")),
            "database_privileges_pg": _extract_mapping_of_lists(categories.get("database_privileges")),
        }

    if normalized_db_type == DatabaseType.SQLSERVER:
        return {
            "server_roles": _ensure_str_list(categories.get("server_roles")),
            "server_permissions": _ensure_str_list(categories.get("server_permissions")),
            "database_roles": _ensure_dict(categories.get("database_roles")),
            "database_permissions": _ensure_dict(categories.get("database_permissions")),
        }

    if normalized_db_type == DatabaseType.ORACLE:
        raw_system_privileges = _ensure_str_list(categories.get("system_privileges"))
        tablespace_privileges = _extract_mapping_of_lists(categories.get("tablespace_privileges"))
        merged_system_privileges = sorted(
            {*raw_system_privileges, *(item for bucket in tablespace_privileges.values() for item in bucket)}
        )
        return {
            "oracle_roles": _ensure_str_list(categories.get("oracle_roles")),
            "oracle_system_privileges": merged_system_privileges,
        }

    return dict(categories)
