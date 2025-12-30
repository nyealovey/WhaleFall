"""Build query-friendly permission facts from raw permissions/snapshot.

`permission_snapshot` is the raw/audit payload. `permission_facts` is a derived
representation meant for statistics queries and rule evaluation inputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.constants import DatabaseType

JsonDict = dict[str, Any]


def _ensure_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _ensure_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _ensure_str_list_from_dicts(value: object, *, dict_key: str) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            output.append(item)
            continue
        if isinstance(item, dict):
            val = item.get(dict_key)
            if isinstance(val, str) and val:
                output.append(val)
    return output


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


def _extract_snapshot_categories(snapshot: object) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict):
        return None
    if snapshot.get("version") != 4:
        return None
    categories = snapshot.get("categories")
    if isinstance(categories, dict):
        return dict(categories)
    return None


def build_permission_facts(
    *,
    record: object,
    snapshot: Mapping[str, object] | None = None,
) -> JsonDict:
    """Build a stable, query-friendly permission facts payload.

    Notes:
    - Prefer snapshot categories when available (v4).
    """

    db_type = str(getattr(record, "db_type", "") or "").lower()
    is_superuser = bool(getattr(record, "is_superuser", False))
    is_locked = bool(getattr(record, "is_locked", False))

    errors: list[str] = []
    if isinstance(snapshot, dict):
        raw_errors = snapshot.get("errors") or []
        if isinstance(raw_errors, list):
            errors = [item for item in raw_errors if isinstance(item, str) and item]
    categories = _extract_snapshot_categories(snapshot)
    if categories is None:
        errors.append("SNAPSHOT_MISSING")
        categories = {}
    if not categories:
        errors.append("PERMISSION_DATA_MISSING")

    roles: list[str] = []
    if db_type == DatabaseType.MYSQL:
        roles_value = categories.get("roles")
        if isinstance(roles_value, dict):
            roles = _ensure_str_list(roles_value.get("direct"))
        else:
            roles = _ensure_str_list(roles_value)
    elif db_type == DatabaseType.POSTGRESQL:
        roles = _ensure_str_list_from_dicts(categories.get("predefined_roles"), dict_key="role") or _ensure_str_list(
            categories.get("predefined_roles"),
        )
    elif db_type == DatabaseType.SQLSERVER:
        server_roles = _ensure_str_list_from_dicts(categories.get("server_roles"), dict_key="name") or _ensure_str_list(
            categories.get("server_roles"),
        )

        database_roles: list[str] = []
        database_roles_value = categories.get("database_roles")
        if isinstance(database_roles_value, dict):
            for entry in database_roles_value.values():
                database_roles.extend(_ensure_str_list_from_dicts(entry, dict_key="name") or _ensure_str_list(entry))
        elif isinstance(database_roles_value, list):
            database_roles = _ensure_str_list_from_dicts(database_roles_value, dict_key="name") or _ensure_str_list(
                database_roles_value,
            )

        roles = [*server_roles, *database_roles]
    elif db_type == DatabaseType.ORACLE:
        roles = _ensure_str_list_from_dicts(categories.get("oracle_roles"), dict_key="role") or _ensure_str_list(
            categories.get("oracle_roles"),
        )

    privileges: JsonDict = {}
    global_privileges = _extract_privilege_list(categories.get("global_privileges"))
    if global_privileges:
        privileges["global"] = global_privileges

    server_privileges = _extract_privilege_list(categories.get("server_permissions"))
    if server_privileges:
        privileges["server"] = server_privileges

    system_privileges = _extract_privilege_list(categories.get("system_privileges"))
    if system_privileges:
        privileges["system"] = system_privileges

    database_privileges = _extract_mapping_of_lists(categories.get("database_privileges"))
    if database_privileges:
        privileges["database"] = database_privileges

    database_permissions = _extract_mapping_of_lists(categories.get("database_permissions"))
    if database_permissions:
        privileges["database_permissions"] = database_permissions

    tablespace_privileges = _extract_mapping_of_lists(categories.get("tablespace_privileges"))
    if tablespace_privileges:
        privileges["tablespace"] = tablespace_privileges

    role_attributes = _ensure_dict(categories.get("role_attributes"))

    capabilities: list[str] = []
    capability_reasons: dict[str, list[str]] = {}

    def _add_capability(name: str, reason: str) -> None:
        if name not in capability_reasons:
            capabilities.append(name)
            capability_reasons[name] = []
        capability_reasons[name].append(reason)

    if is_superuser:
        _add_capability("SUPERUSER", "is_superuser=True")

    if db_type == DatabaseType.POSTGRESQL:
        if role_attributes.get("rolsuper") is True or role_attributes.get("can_super") is True:
            _add_capability("SUPERUSER", "role_attributes.can_super=True")
        if role_attributes.get("rolcreaterole") is True or role_attributes.get("can_create_role") is True:
            _add_capability("GRANT_ADMIN", "role_attributes.can_create_role=True")

        for attr_name, enabled in role_attributes.items():
            if not isinstance(attr_name, str) or not attr_name:
                continue
            if enabled is True:
                _add_capability(attr_name, f"role_attributes.{attr_name}=True")

    if db_type == DatabaseType.SQLSERVER:
        if "sysadmin" in roles:
            _add_capability("SUPERUSER", "server_roles contains sysadmin")
        if "securityadmin" in roles:
            _add_capability("GRANT_ADMIN", "server_roles contains securityadmin")
        if "CONTROL SERVER" in server_privileges:
            _add_capability("GRANT_ADMIN", "server_permissions contains CONTROL SERVER")

    if db_type == DatabaseType.ORACLE:
        if "DBA" in roles:
            _add_capability("SUPERUSER", "oracle_roles contains DBA")
            _add_capability("GRANT_ADMIN", "oracle_roles contains DBA")
        if "GRANT ANY PRIVILEGE" in system_privileges:
            _add_capability("GRANT_ADMIN", "system_privileges contains GRANT ANY PRIVILEGE")

    if db_type == DatabaseType.MYSQL:
        if "GRANT OPTION" in global_privileges:
            _add_capability("GRANT_ADMIN", "global_privileges contains GRANT OPTION")

    return {
        "version": 1,
        "db_type": db_type,
        "is_superuser": is_superuser,
        "is_locked": is_locked,
        "capabilities": sorted(set(capabilities)),
        "capability_reasons": capability_reasons,
        "roles": sorted(set(roles)),
        "privileges": privileges,
        "errors": errors,
        "meta": {
            "source": "snapshot",
            "snapshot_version": 4,
        },
    }
