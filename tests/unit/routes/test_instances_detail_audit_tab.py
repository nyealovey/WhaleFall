from __future__ import annotations

import pytest

from app import db
from app.models.instance import Instance


def _ensure_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["credentials"],
                db.metadata.tables["instance_tags"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
            ],
        )


@pytest.mark.unit
def test_instances_detail_page_includes_audit_tab_and_sync_action(app, auth_client) -> None:
    _ensure_tables(app)

    with app.app_context():
        instance = Instance(
            name="sqlserver-1",
            db_type="sqlserver",
            host="127.0.0.1",
            port=1433,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    response = auth_client.get(f"/instances/{instance_id}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "审计信息" in html
    assert 'data-action="sync-audit-info"' in html
