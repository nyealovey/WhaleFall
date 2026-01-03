"""Build query-friendly permission facts from raw permissions/snapshot.

`permission_snapshot` is the raw/audit payload. `permission_facts` is a derived
representation meant for statistics queries and rule evaluation inputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
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
        # Fallback shape: mapping of privilege -> enabled boolean.
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


def _extract_snapshot_type_specific(snapshot: object, *, db_type: str) -> JsonDict:
    if not isinstance(snapshot, dict):
        return {}
    if snapshot.get("version") != 4:
        return {}

    type_specific = snapshot.get("type_specific")
    if not isinstance(type_specific, dict):
        return {}

    entry = type_specific.get(db_type)
    if isinstance(entry, dict):
        return dict(entry)
    return {}


def _parse_iso_datetime(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _is_expired(valid_until: object) -> bool:
    if not isinstance(valid_until, str) or not valid_until.strip():
        return False
    parsed = _parse_iso_datetime(valid_until)
    if parsed is None:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed <= datetime.now(tz=UTC)


def _extract_snapshot_errors(snapshot: Mapping[str, object] | None) -> list[str]:
    if not isinstance(snapshot, dict):
        return []
    raw_errors = snapshot.get("errors") or []
    if not isinstance(raw_errors, list):
        return []
    return [item for item in raw_errors if isinstance(item, str) and item]


def _resolve_categories(snapshot: Mapping[str, object] | None, errors: list[str]) -> dict[str, Any]:
    categories = _extract_snapshot_categories(snapshot)
    if categories is None:
        errors.append("SNAPSHOT_MISSING")
        return {}
    return categories


def _extract_roles(db_type: str, categories: Mapping[str, object]) -> list[str]:
    if db_type == DatabaseType.MYSQL:
        roles_value = categories.get("roles")
        if isinstance(roles_value, dict):
            return _ensure_str_list(roles_value.get("direct"))
        return _ensure_str_list(roles_value)

    if db_type == DatabaseType.POSTGRESQL:
        return _ensure_str_list_from_dicts(categories.get("predefined_roles"), dict_key="role") or _ensure_str_list(
            categories.get("predefined_roles"),
        )

    if db_type == DatabaseType.SQLSERVER:
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

        return [*server_roles, *database_roles]

    if db_type == DatabaseType.ORACLE:
        return _ensure_str_list_from_dicts(categories.get("oracle_roles"), dict_key="role") or _ensure_str_list(
            categories.get("oracle_roles"),
        )

    return []


def _extract_privileges(categories: Mapping[str, object]) -> tuple[JsonDict, list[str], list[str], list[str]]:
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

    return privileges, global_privileges, server_privileges, system_privileges


def _add_capability(
    capabilities: list[str],
    capability_reasons: dict[str, list[str]],
    *,
    name: str,
    reason: str,
) -> None:
    if name not in capability_reasons:
        capabilities.append(name)
        capability_reasons[name] = []
    capability_reasons[name].append(reason)


def _collect_mysql_capabilities(
    *,
    capabilities: list[str],
    capability_reasons: dict[str, list[str]],
    type_specific: Mapping[str, object],
    global_privileges: list[str],
) -> None:
    if type_specific.get("super_priv") is True:
        _add_capability(capabilities, capability_reasons, name="SUPERUSER", reason="type_specific.super_priv=True")
    if type_specific.get("account_locked") is True:
        _add_capability(capabilities, capability_reasons, name="LOCKED", reason="type_specific.account_locked=True")
    if "GRANT OPTION" in global_privileges:
        _add_capability(
            capabilities,
            capability_reasons,
            name="GRANT_ADMIN",
            reason="global_privileges contains GRANT OPTION",
        )


def _collect_postgresql_capabilities(
    *,
    capabilities: list[str],
    capability_reasons: dict[str, list[str]],
    role_attributes: Mapping[str, object],
    type_specific: Mapping[str, object],
) -> None:
    if role_attributes.get("rolsuper") is True or role_attributes.get("can_super") is True:
        _add_capability(capabilities, capability_reasons, name="SUPERUSER", reason="role_attributes.can_super=True")
    if role_attributes.get("rolcreaterole") is True or role_attributes.get("can_create_role") is True:
        _add_capability(
            capabilities,
            capability_reasons,
            name="GRANT_ADMIN",
            reason="role_attributes.can_create_role=True",
        )
    if role_attributes.get("can_login") is False:
        _add_capability(capabilities, capability_reasons, name="LOCKED", reason="role_attributes.can_login=False")
    if _is_expired(type_specific.get("valid_until")):
        _add_capability(capabilities, capability_reasons, name="LOCKED", reason="type_specific.valid_until expired")

    for attr_name, enabled in role_attributes.items():
        if not isinstance(attr_name, str) or not attr_name:
            continue
        if enabled is True:
            _add_capability(
                capabilities,
                capability_reasons,
                name=attr_name,
                reason=f"role_attributes.{attr_name}=True",
            )


def _collect_sqlserver_capabilities(
    *,
    capabilities: list[str],
    capability_reasons: dict[str, list[str]],
    roles: list[str],
    server_privileges: list[str],
    type_specific: Mapping[str, object],
) -> None:
    if "sysadmin" in roles:
        _add_capability(capabilities, capability_reasons, name="SUPERUSER", reason="server_roles contains sysadmin")
    if "securityadmin" in roles:
        _add_capability(
            capabilities,
            capability_reasons,
            name="GRANT_ADMIN",
            reason="server_roles contains securityadmin",
        )
    if "CONTROL SERVER" in server_privileges:
        _add_capability(
            capabilities,
            capability_reasons,
            name="GRANT_ADMIN",
            reason="server_permissions contains CONTROL SERVER",
        )

    connect_to_engine = type_specific.get("connect_to_engine")
    if isinstance(connect_to_engine, str) and connect_to_engine.upper() == "DENY":
        _add_capability(capabilities, capability_reasons, name="LOCKED", reason="type_specific.connect_to_engine=DENY")
    if type_specific.get("is_locked_out") is True:
        _add_capability(capabilities, capability_reasons, name="LOCKED", reason="type_specific.is_locked_out=True")
    if type_specific.get("is_password_expired") is True:
        _add_capability(
            capabilities,
            capability_reasons,
            name="LOCKED",
            reason="type_specific.is_password_expired=True",
        )
    if type_specific.get("must_change_password") is True:
        _add_capability(
            capabilities,
            capability_reasons,
            name="LOCKED",
            reason="type_specific.must_change_password=True",
        )


def _collect_oracle_capabilities(
    *,
    capabilities: list[str],
    capability_reasons: dict[str, list[str]],
    roles: list[str],
    system_privileges: list[str],
    type_specific: Mapping[str, object],
) -> None:
    if "DBA" in roles:
        _add_capability(capabilities, capability_reasons, name="SUPERUSER", reason="oracle_roles contains DBA")
        _add_capability(capabilities, capability_reasons, name="GRANT_ADMIN", reason="oracle_roles contains DBA")
    if "GRANT ANY PRIVILEGE" in system_privileges:
        _add_capability(
            capabilities,
            capability_reasons,
            name="GRANT_ADMIN",
            reason="system_privileges contains GRANT ANY PRIVILEGE",
        )

    account_status = type_specific.get("account_status")
    if isinstance(account_status, str) and account_status.strip() and account_status.strip().upper() != "OPEN":
        _add_capability(capabilities, capability_reasons, name="LOCKED", reason="type_specific.account_status!=OPEN")


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

    errors = _extract_snapshot_errors(snapshot)
    categories = _resolve_categories(snapshot, errors)
    if not categories:
        errors.append("PERMISSION_DATA_MISSING")

    type_specific = _extract_snapshot_type_specific(snapshot, db_type=db_type)

    roles = _extract_roles(db_type, categories)
    privileges, global_privileges, server_privileges, system_privileges = _extract_privileges(categories)
    role_attributes = _ensure_dict(categories.get("role_attributes"))

    capabilities: list[str] = []
    capability_reasons: dict[str, list[str]] = {}

    if db_type == DatabaseType.MYSQL:
        _collect_mysql_capabilities(
            capabilities=capabilities,
            capability_reasons=capability_reasons,
            type_specific=type_specific,
            global_privileges=global_privileges,
        )
    elif db_type == DatabaseType.POSTGRESQL:
        _collect_postgresql_capabilities(
            capabilities=capabilities,
            capability_reasons=capability_reasons,
            role_attributes=role_attributes,
            type_specific=type_specific,
        )
    elif db_type == DatabaseType.SQLSERVER:
        _collect_sqlserver_capabilities(
            capabilities=capabilities,
            capability_reasons=capability_reasons,
            roles=roles,
            server_privileges=server_privileges,
            type_specific=type_specific,
        )
    elif db_type == DatabaseType.ORACLE:
        _collect_oracle_capabilities(
            capabilities=capabilities,
            capability_reasons=capability_reasons,
            roles=roles,
            system_privileges=system_privileges,
            type_specific=type_specific,
        )

    return {
        "version": 2,
        "db_type": db_type,
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
