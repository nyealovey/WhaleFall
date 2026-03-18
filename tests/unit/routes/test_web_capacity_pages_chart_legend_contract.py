"""容量统计页图例布局契约测试."""

from __future__ import annotations

import pytest

import app.routes.capacity.databases as capacity_databases_route
from app.services.capacity.capacity_databases_page_service import CapacityDatabasesPageContext


@pytest.mark.unit
def test_web_capacity_instances_page_renders_external_legend_slots(auth_client) -> None:
    response = auth_client.get("/capacity/instances")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "容量统计(实例)" in html
    assert "capacity-chart-panel" in html
    assert 'id="instanceChartLegend"' in html
    assert 'id="instanceChangeChartLegend"' in html
    assert 'id="instanceChangePercentChartLegend"' in html
    assert 'data-role="multiselect"' in html
    assert 'data-role="multiselect-trigger"' in html
    assert 'data-role="multiselect-menu"' in html
    assert 'data-role="multiselect-summary"' in html
    assert 'data-role="db-type-filter"' in html
    assert 'data-role="instance-filter"' in html
    assert 'name="db_type"' in html and 'type="checkbox"' in html
    assert 'name="instance"' in html and 'type="checkbox"' in html


@pytest.mark.unit
def test_web_capacity_databases_page_renders_external_legend_slots(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(
        capacity_databases_route._capacity_databases_page_service,
        "build_context",
        lambda **_: CapacityDatabasesPageContext(
            database_type_options=[{"value": "mysql", "label": "MySQL"}],
            instance_options=[{"value": "1", "label": "demo (mysql)", "db_type": "mysql"}],
            database_options=[],
            db_types=["mysql"],
            instances=["1"],
            database_id="",
            database="",
        ),
    )

    response = auth_client.get("/capacity/databases")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "容量统计(数据库)" in html
    assert "capacity-chart-panel" in html
    assert 'id="databaseChartLegend"' in html
    assert 'id="databaseChangeChartLegend"' in html
    assert 'id="databaseChangePercentChartLegend"' in html
    assert 'data-role="multiselect"' in html
    assert 'data-role="multiselect-trigger"' in html
    assert 'data-role="multiselect-menu"' in html
    assert 'data-role="multiselect-summary"' in html
    assert 'data-role="db-type-filter"' in html
    assert 'data-role="instance-filter"' in html
    assert 'type="checkbox"' in html
