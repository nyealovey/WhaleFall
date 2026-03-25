"""实例列表页面契约测试."""

from __future__ import annotations

import pytest

import app.routes.instances.manage as route_module


@pytest.mark.unit
def test_web_instances_list_page_embeds_vendor_db_type_assets(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(route_module.CredentialsRepository, "list_active_credentials", staticmethod(lambda: []))
    monkeypatch.setattr(route_module._filter_options_service, "list_active_tag_options", lambda: [])

    response = auth_client.get("/instances/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'data-db-type-map=' in html
    assert "db-types/mysql.png" in html
    assert "db-types/postgresql.png" in html
    assert "db-types/sqlserver.png" in html
    assert "db-types/oracle.png" in html
    assert 'id="audit_status"' in html
    assert 'id="managed_status"' in html


@pytest.mark.unit
def test_web_instances_list_tag_filter_hides_placeholder_when_tags_selected(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(route_module.CredentialsRepository, "list_active_credentials", staticmethod(lambda: []))
    monkeypatch.setattr(
        route_module._filter_options_service,
        "list_active_tag_options",
        lambda: [{"value": "prod", "label": "生产环境"}],
    )

    response = auth_client.get("/instances/?tags=prod")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    button_html = html.split('id="instance-tag-selector-open"', 1)[1].split("</button>", 1)[0]
    assert "生产环境" in button_html
    assert "选择标签" not in button_html
