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
    assert "备份信息" in html
    assert 'data-action="sync-audit-info"' in html
    assert html.index('data-action="sync-accounts"') < html.index('data-action="sync-capacity"')
    assert html.index('data-action="sync-capacity"') < html.index('data-action="sync-audit-info"')
    assert html.index("账户信息") < html.index("容量信息")
    assert html.index("容量信息") < html.index("审计信息")
    assert html.index("审计信息") < html.index("备份信息")
    assert 'id="accounts-tab"' in html and "nav-link active" in html
    assert 'id="accounts-pane"' in html and "show active instance-data-pane" in html
    assert 'id="backup-tab"' in html
    assert 'id="backup-pane"' in html
    assert '<div class="instance-data-pane__stack">' in html.split('id="backup-pane"', 1)[1]
    assert 'id="backupInfoContent"' in html.split('id="backup-pane"', 1)[1]


@pytest.mark.unit
def test_instances_detail_page_keeps_manual_sync_buttons_enabled_for_disabled_instance(app, auth_client) -> None:
    _ensure_tables(app)

    with app.app_context():
        instance = Instance(
            name="sqlserver-disabled",
            db_type="sqlserver",
            host="127.0.0.1",
            port=1433,
            is_active=False,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    response = auth_client.get(f"/instances/{instance_id}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for action in ('sync-accounts', 'sync-capacity', 'sync-audit-info'):
        segment = html.split(f'data-action="{action}"', 1)[1].split('>', 1)[0]
        assert 'disabled title="实例已停用' not in segment


@pytest.mark.unit
def test_instances_detail_page_uses_shared_filter_band_classes(app, auth_client) -> None:
    _ensure_tables(app)

    with app.app_context():
        instance = Instance(
            name="mysql-filter-band",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    response = auth_client.get(f"/instances/{instance_id}")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="instance-accounts-filter-form"' in html
    assert 'id="instance-databases-filter-form"' in html
    assert "filter-band__form" in html
    assert "filter-band__toggle" in html
    assert "filter-band__field filter-band__field--lg" in html
    assert "filter-band__meta" in html
