import pytest

from app.services.config_sync.sqlserver_audit_info_sync_service import (
    SQLServerAuditInfoSyncService,
    build_sqlserver_audit_facts,
)


@pytest.mark.unit
def test_build_sqlserver_audit_facts_counts_targets_and_specs() -> None:
    snapshot = {
        "version": 1,
        "supported": True,
        "db_type": "sqlserver",
        "server_audits": [
            {
                "name": "audit-file",
                "enabled": True,
                "target_type": "FILE",
                "on_failure": "CONTINUE",
            },
            {
                "name": "audit-app",
                "enabled": False,
                "target_type": "APPLICATION_LOG",
                "on_failure": "FAIL_OPERATION",
            },
        ],
        "audit_specifications": [
            {
                "scope": "server",
                "name": "server-spec",
                "enabled": True,
                "audit_name": "audit-file",
                "action_count": 2,
            },
        ],
        "database_audit_specifications": [
            {
                "scope": "database",
                "database_name": "db_a",
                "name": "db-spec-a",
                "enabled": True,
                "audit_name": "audit-file",
                "action_count": 1,
            },
            {
                "scope": "database",
                "database_name": "db_b",
                "name": "db-spec-b",
                "enabled": False,
                "audit_name": "audit-app",
                "action_count": 3,
            },
        ],
        "errors": [],
        "meta": {},
    }

    facts = build_sqlserver_audit_facts(snapshot)

    assert facts["version"] == 1
    assert facts["supported"] is True
    assert facts["has_audit"] is True
    assert facts["audit_count"] == 2
    assert facts["enabled_audit_count"] == 1
    assert facts["specification_count"] == 3
    assert facts["covered_database_count"] == 2
    assert facts["target_types"] == ["APPLICATION_LOG", "FILE"]
    assert facts["failure_policies"] == ["CONTINUE", "FAIL_OPERATION"]


@pytest.mark.unit
def test_build_sqlserver_audit_facts_marks_empty_snapshot_without_audit() -> None:
    facts = build_sqlserver_audit_facts(
        {
            "version": 1,
            "supported": True,
            "db_type": "sqlserver",
            "server_audits": [],
            "audit_specifications": [],
            "database_audit_specifications": [],
            "errors": [],
            "meta": {},
        },
    )

    assert facts["has_audit"] is False
    assert facts["audit_count"] == 0
    assert facts["enabled_audit_count"] == 0
    assert facts["specification_count"] == 0
    assert facts["covered_database_count"] == 0


@pytest.mark.unit
def test_collect_server_audits_uses_log_file_path_column() -> None:
    class _FakeConnection:
        def __init__(self) -> None:
            self.last_sql = ""

        def execute_query(self, sql: str):  # type: ignore[no-untyped-def]
            self.last_sql = sql
            return [
                (
                    1,
                    "audit-main",
                    "guid-1",
                    "FILE",
                    "CONTINUE",
                    1000,
                    1,
                    None,
                    None,
                    "D:\\SQLAudit\\",
                    128,
                    10,
                    20,
                    0,
                ),
            ]

    connection = _FakeConnection()
    audits = SQLServerAuditInfoSyncService._collect_server_audits(connection)  # type: ignore[arg-type]

    assert "log_file_path" in connection.last_sql
    assert "max_files" not in connection.last_sql
    assert "sfa.file_path" not in connection.last_sql
    assert audits[0]["file_path"] == "D:\\SQLAudit\\"
    assert "max_files" not in audits[0]


@pytest.mark.unit
def test_collect_database_audit_specifications_builds_object_display_text() -> None:
    class _FakeConnection:
        def __init__(self) -> None:
            self.last_sql = ""

        def execute_query(self, sql: str):  # type: ignore[no-untyped-def]
            self.last_sql = sql
            return [
                (
                    "master",
                    "Audit_OSCMDEXEC",
                    "guid-1",
                    1,
                    None,
                    None,
                    "EXECUTE",
                    "SUCCESS",
                    "OBJECT",
                    12345,
                    0,
                    "dbo",
                    "xp_cmdshell_proxy_account",
                    None,
                    None,
                ),
            ]

    connection = _FakeConnection()
    specs = SQLServerAuditInfoSyncService._collect_single_database_audit_specifications(  # type: ignore[arg-type]
        connection,
        database_name="master",
        audit_name_by_guid={"guid-1": "SIEM"},
    )

    assert ".sys.all_objects" in connection.last_sql
    assert ".sys.objects" not in connection.last_sql
    assert specs[0]["action_count"] == 1
    assert specs[0]["actions"][0]["display_text"] == "EXECUTE dbo.xp_cmdshell_proxy_account"


@pytest.mark.unit
def test_collect_snapshot_keeps_server_level_data_when_one_database_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SQLServerAuditInfoSyncService()

    monkeypatch.setattr(
        service,
        "_collect_server_audits",
        lambda _connection: [{"name": "SIEM", "enabled": True, "target_type": "APPLICATION_LOG"}],
    )
    monkeypatch.setattr(
        service,
        "_collect_server_audit_specifications",
        lambda _connection, _audit_name_by_guid: [
            {
                "scope": "server",
                "name": "server-spec",
                "audit_name": "SIEM",
                "enabled": True,
                "actions": [],
                "action_count": 0,
            },
        ],
    )

    def _fake_collect_database_audits(_connection, _audit_name_by_guid):  # type: ignore[no-untyped-def]
        return (
            [
                {
                    "scope": "database",
                    "database_name": "readable_db",
                    "name": "db-spec",
                    "audit_name": "SIEM",
                    "enabled": True,
                    "actions": [],
                    "action_count": 0,
                },
            ],
            [
                {
                    "scope": "database_audit_specification",
                    "database_name": "AzureDevOps_AI-Lab",
                    "error_code": 978,
                    "reason": "DATABASE_NOT_READABLE",
                    "error_message": "The target database is in an availability group and is currently accessible for connections when the application intent is set to read only.",
                },
            ],
        )

    monkeypatch.setattr(service, "_collect_database_audit_specifications", _fake_collect_database_audits)

    snapshot = service._collect_snapshot(object())  # type: ignore[arg-type]
    facts = build_sqlserver_audit_facts(snapshot)

    assert snapshot["server_audits"][0]["name"] == "SIEM"
    assert snapshot["database_audit_specifications"][0]["database_name"] == "readable_db"
    assert snapshot["meta"]["partial_success"] is True
    assert snapshot["meta"]["collected_database_count"] == 1
    assert snapshot["meta"]["failed_database_count"] == 1
    assert snapshot["meta"]["failed_databases"] == ["AzureDevOps_AI-Lab"]
    assert snapshot["errors"][0]["reason"] == "DATABASE_NOT_READABLE"
    assert facts["warnings"] == ["DATABASE_AUDIT_SPECIFICATIONS_PARTIAL:AzureDevOps_AI-Lab"]
