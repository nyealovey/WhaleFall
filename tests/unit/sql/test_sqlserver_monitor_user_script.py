from pathlib import Path

import pytest


@pytest.mark.unit
def test_sqlserver_monitor_user_script_documents_audit_catalog_permissions() -> None:
    script = Path("sql/ops/monitor-user/setup_sqlserver_monitor_user.sql").read_text(encoding="utf-8")

    assert "WhaleFall 审计信息页（catalog 只读）" in script
    assert "VIEW ANY DEFINITION" in script
    assert "GRANT VIEW DEFINITION TO [monitor_user];" in script
    assert "sys.server_audits" in script
    assert "sys.database_audit_specifications" in script
    assert "sys.dm_server_audit_status" in script
