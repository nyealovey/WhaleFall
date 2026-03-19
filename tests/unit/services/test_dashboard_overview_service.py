from __future__ import annotations

from contextlib import nullcontext

import pytest

import app.services.dashboard.dashboard_overview_service as dashboard_module


@pytest.mark.unit
def test_dashboard_overview_uses_instance_total_that_includes_deleted(monkeypatch) -> None:
    monkeypatch.setattr(dashboard_module.UsersRepository, "count_users", staticmethod(lambda: 3))
    monkeypatch.setattr(
        dashboard_module.AccountStatisticsRepository,
        "fetch_summary",
        staticmethod(
            lambda: {
                "total_accounts": 12,
                "active_accounts": 11,
                "normal_accounts": 10,
                "locked_accounts": 1,
                "deleted_accounts": 1,
            }
        ),
    )
    monkeypatch.setattr(
        dashboard_module.AccountStatisticsRepository,
        "fetch_classification_overview",
        staticmethod(lambda: {"classifications": [], "total": 0, "auto": 0}),
    )
    monkeypatch.setattr(
        dashboard_module.InstanceStatisticsRepository,
        "fetch_summary",
        staticmethod(
            lambda: {
                "total_instances": 82,
                "current_instances": 78,
                "active_instances": 78,
                "normal_instances": 78,
                "disabled_instances": 0,
                "deleted_instances": 4,
            }
        ),
    )
    monkeypatch.setattr(
        dashboard_module.DatabaseStatisticsRepository,
        "fetch_summary",
        staticmethod(
            lambda: {
                "total_databases": 10,
                "active_databases": 8,
                "inactive_databases": 1,
                "deleted_databases": 1,
                "total_instances": 2,
            }
        ),
    )
    monkeypatch.setattr(dashboard_module.db.session, "begin_nested", lambda: nullcontext())
    monkeypatch.setattr(
        dashboard_module,
        "CapacityInstancesRepository",
        lambda: type(
            "_CapacityRepo",
            (),
            {"summarize_latest_stats": staticmethod(lambda _filters: ([], 0, 0, 0))},
        )(),
    )
    monkeypatch.setattr(dashboard_module, "log_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard_module, "log_warning", lambda *args, **kwargs: None)

    overview = dashboard_module.get_system_overview.__wrapped__()

    assert overview["instances"] == {
        "total": 82,
        "active": 78,
        "inactive": 0,
        "deleted": 4,
    }
    assert overview["accounts"] == {
        "total": 12,
        "active": 11,
        "normal": 10,
        "locked": 1,
        "deleted": 1,
    }
    assert overview["databases"] == {
        "total": 10,
        "active": 8,
        "inactive": 1,
        "deleted": 1,
    }
