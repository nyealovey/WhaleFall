from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

from app import db
from app.models.instance import Instance

ROOT_DIR = Path(__file__).resolve().parents[3]


class _DatabaseInfoTabContentParser(HTMLParser):
    _VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__()
        self._stack: list[dict[str, str]] = []
        self._tab_content_depth: int | None = None
        self.direct_pane_ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {
            key: value or ""
            for key, value in attrs
        }
        if (
            self._tab_content_depth is not None
            and len(self._stack) == self._tab_content_depth + 1
            and tag == "div"
        ):
            class_names = set(attr_map.get("class", "").split())
            if {"tab-pane", "instance-data-pane"}.issubset(class_names):
                self.direct_pane_ids.append(attr_map.get("id", ""))

        if tag not in self._VOID_TAGS:
            self._stack.append({"tag": tag, "id": attr_map.get("id", "")})
        if attr_map.get("id") == "databaseInfoTabContent" and tag not in self._VOID_TAGS:
            self._tab_content_depth = len(self._stack) - 1

    def handle_endtag(self, tag: str) -> None:
        while self._stack:
            node = self._stack.pop()
            if (
                self._tab_content_depth is not None
                and len(self._stack) < self._tab_content_depth + 1
            ):
                self._tab_content_depth = None
            if node["tag"] == tag:
                break


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


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


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
    assert html.index("账户信息") < html.index("账户信息（AG）")
    assert html.index("账户信息（AG）") < html.index("容量信息")
    assert html.index("容量信息") < html.index("审计信息")
    assert html.index("审计信息") < html.index("备份信息")
    assert 'id="accounts-tab"' in html and "nav-link active" in html
    assert 'id="accounts-pane"' in html and "show active instance-data-pane" in html
    assert 'id="ag-accounts-tab"' in html
    assert 'id="ag-accounts-pane"' in html
    assert 'id="backup-tab"' in html
    assert 'id="backup-pane"' in html
    backup_pane_html = html.split('id="backup-pane"', 1)[1]
    assert '<div class="instance-data-pane__stack">' in backup_pane_html
    assert 'id="backupInfoContent"' in backup_pane_html
    assert "尚未加载备份信息" not in backup_pane_html


@pytest.mark.unit
def test_instances_detail_page_keeps_all_data_panes_under_same_tab_content(app, auth_client) -> None:
    _ensure_tables(app)

    with app.app_context():
        instance = Instance(
            name="sqlserver-tabs-structure",
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
    parser = _DatabaseInfoTabContentParser()
    parser.feed(response.get_data(as_text=True))
    assert parser.direct_pane_ids == [
        "accounts-pane",
        "ag-accounts-pane",
        "capacity-pane",
        "audit-pane",
        "backup-pane",
    ]


@pytest.mark.unit
def test_instances_detail_page_places_ag_accounts_in_dedicated_tab(app, auth_client) -> None:
    _ensure_tables(app)

    with app.app_context():
        instance = Instance(
            name="sqlserver-ag-accounts-tab",
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
    accounts_pane = html.split('id="accounts-pane"', 1)[1].split('id="ag-accounts-pane"', 1)[0]
    ag_accounts_pane = html.split('id="ag-accounts-pane"', 1)[1]
    assert "instance-ag-accounts-section" not in accounts_pane
    assert "instance-ag-accounts-section" in ag_accounts_pane
    assert "agAccountTotalCount" in ag_accounts_pane
    assert "agAccountSearchInput" in ag_accounts_pane
    assert "instance-ag-accounts-grid" in ag_accounts_pane
    assert "<table" not in ag_accounts_pane.split('id="capacity-pane"', 1)[0]


@pytest.mark.unit
def test_instance_detail_ag_accounts_uses_accounts_grid_style_and_actions() -> None:
    content = _read_text("app/static/js/modules/views/instances/detail.js")
    ready_block = content.split("ready(() => {", 1)[1].split("});", 1)[0]

    assert "initializeAgAccountsTab();" in ready_block
    assert "loadAgAccounts();" not in ready_block
    assert "const agAccountsTab = document.getElementById('ag-accounts-tab');" in content
    assert "agAccountsTab.addEventListener('shown.bs.tab'" in content
    assert "initializeAgAccountsGrid();" in content
    assert "buildAgAccountsGridColumns()" in content
    assert "name: '监听器'" in content
    assert "renderAccountActions(getRowMeta(row))" in content
    assert "viewInstanceAccountPermissions(accountId)" in content
    assert "viewAccountChangeHistory(accountId)" in content
    assert "agAccountsTableBody" not in content


@pytest.mark.unit
def test_instance_detail_regular_accounts_request_is_limited_to_instance_owner() -> None:
    content = _read_text("app/static/js/modules/views/instances/detail.js")

    assert "&owner_type=instance" in content


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
    for action in ("sync-accounts", "sync-capacity", "sync-audit-info"):
        segment = html.split(f'data-action="{action}"', 1)[1].split(">", 1)[0]
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
