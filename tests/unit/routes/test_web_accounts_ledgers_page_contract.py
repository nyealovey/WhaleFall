"""账户台账页面契约测试."""

from __future__ import annotations

import pytest

import app.routes.accounts.ledgers as route_module


@pytest.mark.unit
def test_web_accounts_ledgers_page_embeds_png_db_type_assets(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(route_module._filter_options_service, "list_active_tag_options", lambda: [])
    monkeypatch.setattr(route_module._filter_options_service, "list_classification_options", lambda: [])

    response = auth_client.get("/accounts/ledgers")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-db-type-map=' in html
    assert "db-types/mysql.png" in html
    assert "db-types/postgresql.png" in html
    assert "db-types/sqlserver.png" in html
    assert "db-types/oracle.png" in html
