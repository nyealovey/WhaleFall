"""SQL Server 审计信息采集服务."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from app.core.constants import DatabaseType
from app.services.connection_adapters.adapters.base import ConnectionAdapterError, DatabaseConnection
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.database_type_utils import normalize_database_type
from app.utils.time_utils import time_utils

AUDIT_INFO_CONFIG_KEY = "audit_info"


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _boolify(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _intify(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _isoformat(value: object) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return _stringify(value)


def _quote_identifier(name: str) -> str:
    return f"[{name.replace(']', ']]')}]"


def _quote_literal(value: str) -> str:
    return value.replace("'", "''")


def _target_summary(audit: Mapping[str, object]) -> str:
    file_path = _stringify(audit.get("file_path"))
    if file_path:
        return file_path
    target_type = _stringify(audit.get("target_type"))
    return target_type or "未配置"


def build_sqlserver_audit_facts(snapshot: Mapping[str, object]) -> dict[str, Any]:
    server_audits_value = snapshot.get("server_audits")
    server_audits = server_audits_value if isinstance(server_audits_value, list) else []
    server_specs_value = snapshot.get("audit_specifications")
    server_specs = server_specs_value if isinstance(server_specs_value, list) else []
    db_specs_value = snapshot.get("database_audit_specifications")
    db_specs = db_specs_value if isinstance(db_specs_value, list) else []

    audit_count = len(server_audits)
    enabled_audit_count = sum(
        1 for item in server_audits if isinstance(item, Mapping) and _boolify(item.get("enabled"))
    )
    specification_count = len(server_specs) + len(db_specs)
    covered_database_names = sorted(
        {
            database_name
            for item in db_specs
            if isinstance(item, Mapping)
            for database_name in [_stringify(item.get("database_name"))]
            if database_name
        },
    )
    target_types = sorted(
        {
            target_type
            for item in server_audits
            if isinstance(item, Mapping)
            for target_type in [_stringify(item.get("target_type"))]
            if target_type
        },
    )
    failure_policies = sorted(
        {
            policy
            for item in server_audits
            if isinstance(item, Mapping)
            for policy in [_stringify(item.get("on_failure"))]
            if policy
        },
    )

    audit_names = {
        audit_name
        for item in server_audits
        if isinstance(item, Mapping)
        for audit_name in [_stringify(item.get("name"))]
        if audit_name
    }
    warnings: list[str] = []
    for specification in [*server_specs, *db_specs]:
        if not isinstance(specification, Mapping):
            continue
        audit_name = _stringify(specification.get("audit_name"))
        if audit_name and audit_name not in audit_names:
            warnings.append(f"AUDIT_TARGET_MISSING:{audit_name}")

    return {
        "version": 1,
        "supported": True,
        "has_audit": audit_count > 0,
        "audit_count": audit_count,
        "enabled_audit_count": enabled_audit_count,
        "specification_count": specification_count,
        "covered_database_count": len(covered_database_names),
        "target_types": target_types,
        "failure_policies": failure_policies,
        "warnings": warnings,
    }


class SQLServerAuditInfoSyncService:
    """采集 SQL Server 实例的审计配置."""

    def __init__(self, connection_factory: type[ConnectionFactory] | None = None) -> None:
        self._connection_factory = connection_factory or ConnectionFactory

    def sync_instance_audit(self, *, instance) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        db_type = normalize_database_type(str(getattr(instance, "db_type", "") or ""))
        if db_type != DatabaseType.SQLSERVER:
            raise ValueError("当前仅支持 SQL Server 审计信息采集")

        connection = self._connection_factory.create_connection(instance)
        if connection is None:
            raise ConnectionAdapterError("不支持的数据库连接类型")
        if not connection.connect():
            raise ConnectionAdapterError("无法建立数据库连接")

        try:
            snapshot = self._collect_snapshot(connection)
        finally:
            connection.disconnect()

        facts = build_sqlserver_audit_facts(snapshot)
        return {
            "snapshot": snapshot,
            "facts": facts,
            "summary": {
                "audit_count": facts["audit_count"],
                "enabled_audit_count": facts["enabled_audit_count"],
                "specification_count": facts["specification_count"],
                "covered_database_count": facts["covered_database_count"],
            },
        }

    def _collect_snapshot(self, connection: DatabaseConnection) -> dict[str, Any]:
        server_audits = self._collect_server_audits(connection)
        audit_name_by_guid = {
            audit_guid: audit["name"]
            for audit in server_audits
            for audit_guid in [_stringify(audit.get("audit_guid"))]
            if audit_guid
        }
        server_specs = self._collect_server_audit_specifications(connection, audit_name_by_guid)
        database_specs = self._collect_database_audit_specifications(connection, audit_name_by_guid)
        return {
            "version": 1,
            "supported": True,
            "db_type": DatabaseType.SQLSERVER,
            "server_audits": server_audits,
            "audit_specifications": server_specs,
            "database_audit_specifications": database_specs,
            "errors": [],
            "meta": {
                "collected_at": time_utils.now().isoformat(),
                "collector": "sqlserver_audit_info_v1",
            },
        }

    @staticmethod
    def _collect_server_audits(connection: DatabaseConnection) -> list[dict[str, Any]]:
        rows = connection.execute_query(
            """
            SELECT
                sa.audit_id,
                sa.name,
                CAST(sa.audit_guid AS NVARCHAR(36)) AS audit_guid,
                sa.type_desc,
                sa.on_failure_desc,
                sa.queue_delay,
                sa.is_state_enabled,
                sa.create_date,
                sa.modify_date,
                sfa.log_file_path AS file_path,
                sfa.max_file_size,
                sfa.max_rollover_files,
                sfa.max_files,
                sfa.reserve_disk_space
            FROM sys.server_audits sa
            LEFT JOIN sys.server_file_audits sfa ON sfa.audit_id = sa.audit_id
            ORDER BY sa.name ASC
            """,
        )
        audits: list[dict[str, Any]] = []
        for row in rows:
            name = _stringify(row[1] if len(row) > 1 else None)
            if not name:
                continue
            audit = {
                "audit_id": _intify(row[0] if len(row) > 0 else None),
                "name": name,
                "audit_guid": _stringify(row[2] if len(row) > 2 else None),
                "target_type": _stringify(row[3] if len(row) > 3 else None),
                "on_failure": _stringify(row[4] if len(row) > 4 else None),
                "queue_delay": _intify(row[5] if len(row) > 5 else None),
                "enabled": _boolify(row[6] if len(row) > 6 else None),
                "created_at": _isoformat(row[7] if len(row) > 7 else None),
                "updated_at": _isoformat(row[8] if len(row) > 8 else None),
                "file_path": _stringify(row[9] if len(row) > 9 else None),
                "max_size_mb": _intify(row[10] if len(row) > 10 else None),
                "max_rollover_files": _intify(row[11] if len(row) > 11 else None),
                "max_files": _intify(row[12] if len(row) > 12 else None),
                "reserve_disk_space": _boolify(row[13] if len(row) > 13 else None),
            }
            audit["target_summary"] = _target_summary(audit)
            audits.append(audit)
        return audits

    @staticmethod
    def _collect_server_audit_specifications(
        connection: DatabaseConnection,
        audit_name_by_guid: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        rows = connection.execute_query(
            """
            SELECT
                sas.name,
                CAST(sas.audit_guid AS NVARCHAR(36)) AS audit_guid,
                sas.is_state_enabled,
                sas.create_date,
                sas.modify_date,
                sad.audit_action_name,
                sad.audited_result,
                sad.class_desc
            FROM sys.server_audit_specifications sas
            LEFT JOIN sys.server_audit_specification_details sad
              ON sad.server_specification_id = sas.server_specification_id
            ORDER BY sas.name ASC, sad.audit_action_name ASC
            """,
        )
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            name = _stringify(row[0] if len(row) > 0 else None)
            if not name:
                continue
            audit_guid = _stringify(row[1] if len(row) > 1 else None)
            spec = grouped.setdefault(
                name,
                {
                    "scope": "server",
                    "name": name,
                    "audit_name": audit_name_by_guid.get(audit_guid or "", audit_guid),
                    "enabled": _boolify(row[2] if len(row) > 2 else None),
                    "created_at": _isoformat(row[3] if len(row) > 3 else None),
                    "updated_at": _isoformat(row[4] if len(row) > 4 else None),
                    "actions": [],
                },
            )
            action_name = _stringify(row[5] if len(row) > 5 else None)
            if action_name:
                spec["actions"].append(
                    {
                        "name": action_name,
                        "audited_result": _stringify(row[6] if len(row) > 6 else None),
                        "class_desc": _stringify(row[7] if len(row) > 7 else None),
                    },
                )
        for spec in grouped.values():
            spec["action_count"] = len(spec["actions"])
        return [grouped[key] for key in sorted(grouped.keys())]

    def _collect_database_audit_specifications(
        self,
        connection: DatabaseConnection,
        audit_name_by_guid: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        databases = self._collect_online_databases(connection)
        collected: list[dict[str, Any]] = []
        for database_name in databases:
            collected.extend(
                self._collect_single_database_audit_specifications(
                    connection,
                    database_name=database_name,
                    audit_name_by_guid=audit_name_by_guid,
                ),
            )
        return collected

    @staticmethod
    def _collect_online_databases(connection: DatabaseConnection) -> list[str]:
        rows = connection.execute_query(
            """
            SELECT name
            FROM sys.databases
            WHERE state = 0
            ORDER BY name ASC
            """,
        )
        return [database_name for row in rows if (database_name := _stringify(row[0] if row else None))]

    @staticmethod
    def _collect_single_database_audit_specifications(
        connection: DatabaseConnection,
        *,
        database_name: str,
        audit_name_by_guid: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        database_literal = _quote_literal(database_name)
        database_identifier = _quote_identifier(database_name)
        try:
            rows = connection.execute_query(
                f"""
                SELECT
                    N'{database_literal}' AS database_name,
                    das.name,
                    CAST(das.audit_guid AS NVARCHAR(36)) AS audit_guid,
                    das.is_state_enabled,
                    das.create_date,
                    das.modify_date,
                    dsd.audit_action_name,
                    dsd.audited_result,
                    dsd.class_desc
                FROM {database_identifier}.sys.database_audit_specifications das
                LEFT JOIN {database_identifier}.sys.database_audit_specification_details dsd
                  ON dsd.database_specification_id = das.database_specification_id
                ORDER BY das.name ASC, dsd.audit_action_name ASC
                """,
            )
        except Exception as exc:
            raise RuntimeError(f"读取数据库 {database_name} 审计配置失败: {exc}") from exc

        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            resolved_database_name = _stringify(row[0] if len(row) > 0 else None) or database_name
            name = _stringify(row[1] if len(row) > 1 else None)
            if not name:
                continue
            audit_guid = _stringify(row[2] if len(row) > 2 else None)
            key = (resolved_database_name, name)
            spec = grouped.setdefault(
                key,
                {
                    "scope": "database",
                    "database_name": resolved_database_name,
                    "name": name,
                    "audit_name": audit_name_by_guid.get(audit_guid or "", audit_guid),
                    "enabled": _boolify(row[3] if len(row) > 3 else None),
                    "created_at": _isoformat(row[4] if len(row) > 4 else None),
                    "updated_at": _isoformat(row[5] if len(row) > 5 else None),
                    "actions": [],
                },
            )
            action_name = _stringify(row[6] if len(row) > 6 else None)
            if action_name:
                spec["actions"].append(
                    {
                        "name": action_name,
                        "audited_result": _stringify(row[7] if len(row) > 7 else None),
                        "class_desc": _stringify(row[8] if len(row) > 8 else None),
                    },
                )
        for spec in grouped.values():
            spec["action_count"] = len(spec["actions"])
        return [grouped[key] for key in sorted(grouped.keys())]
