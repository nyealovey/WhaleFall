from pathlib import Path

import pytest


@pytest.mark.unit
def test_instance_audit_ui_hides_guid_and_database_column_and_plus_n_summary() -> None:
    source = Path("app/static/js/modules/views/instances/detail.js").read_text(encoding="utf-8")

    assert "audit.audit_guid" not in source
    assert "<th>数据库</th>" not in source
    assert "+${labels.length - 3}" not in source
