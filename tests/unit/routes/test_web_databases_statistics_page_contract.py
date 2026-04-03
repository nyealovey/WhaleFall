"""数据库统计页面与入口契约测试."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import app.routes.databases.ledgers as route_module


@dataclass(slots=True)
class _DummyDatabaseStatisticsPageResult:
    total_databases: int = 8
    active_databases: int = 6
    inactive_databases: int = 1
    deleted_databases: int = 2
    total_instances: int = 3
    total_size_mb: int = 4096
    avg_size_mb: float = 682.7
    max_size_mb: int = 2048
    db_type_stats: list[dict[str, object]] = None  # type: ignore[assignment]
    instance_stats: list[dict[str, object]] = None  # type: ignore[assignment]
    sync_status_stats: list[dict[str, object]] = None  # type: ignore[assignment]
    capacity_rankings: list[dict[str, object]] = None  # type: ignore[assignment]


@pytest.mark.unit
def test_web_databases_ledgers_page_contains_statistics_entry(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(route_module._filter_options_service, "list_active_tag_options", list)

    response = auth_client.get("/databases/ledgers")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'href="/databases/statistics"' in html
    assert "数据库统计" in html
    assert "data-db-type-map=" in html
    assert "db-types/mysql.png" in html
    assert "db-types/postgresql.png" in html
    assert "db-types/sqlserver.png" in html
    assert "db-types/oracle.png" in html


@pytest.mark.unit
def test_web_databases_statistics_page_renders_refreshable_dashboard(auth_client, monkeypatch) -> None:
    class _DummyDatabaseStatisticsReadService:
        def build_statistics(self) -> _DummyDatabaseStatisticsPageResult:
            return _DummyDatabaseStatisticsPageResult(
                db_type_stats=[{"db_type": "mysql", "count": 4}],
                instance_stats=[{"instance_id": 1, "instance_name": "prod-mysql-1", "db_type": "mysql", "count": 4}],
                sync_status_stats=[{"value": "completed", "label": "已更新", "variant": "success", "count": 4}],
                capacity_rankings=[
                    {
                        "instance_id": 1,
                        "instance_name": "prod-mysql-1",
                        "db_type": "mysql",
                        "database_name": "app_db",
                        "size_mb": 2048,
                        "size_label": "2.00 GB",
                        "collected_at": "2026-03-16T10:00:00+00:00",
                    },
                ],
            )

    monkeypatch.setattr(
        route_module,
        "DatabaseStatisticsReadService",
        _DummyDatabaseStatisticsReadService,
        raising=False,
    )

    response = auth_client.get("/databases/statistics")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "数据库统计" in html
    assert 'data-action="refresh-stats"' in html
    assert "DatabaseStatisticsPage" in html
