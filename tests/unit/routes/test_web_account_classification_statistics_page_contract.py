"""账户分类统计页面筛选契约测试."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.routes.accounts.classification_statistics as route_module


@pytest.mark.unit
def test_web_account_classification_statistics_page_uses_shared_filter_fields(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(
        route_module._classifications_read_service,
        "list_classifications",
        lambda: [
            SimpleNamespace(id=1, display_name="高风险", code="high"),
        ],
    )
    monkeypatch.setattr(
        route_module._filter_options_service,
        "list_instance_select_options",
        lambda db_type=None: [{"value": "1", "label": "prod-mysql-1"}],
    )

    response = auth_client.get("/accounts/statistics/classifications")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="account-classification-statistics-filter"' in html
    assert "filter-field--lg" in html
    assert "filter-field--sm" in html
    assert "col-md-2 col-12" not in html
