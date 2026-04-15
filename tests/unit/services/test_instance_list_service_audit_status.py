"""实例列表服务审计状态派生测试."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.core.types.instances import InstanceListFilters, InstanceListMetrics
from app.core.types.listing import PaginatedResult
from app.services.instances.instance_list_service import InstanceListService


def _build_filters() -> InstanceListFilters:
    return InstanceListFilters(
        page=1,
        limit=20,
        sort_field="id",
        sort_order="desc",
        search="",
        db_type="",
        status="",
        audit_status="",
        managed_status="",
        backup_status="",
        tags=[],
        include_deleted=False,
    )


def _build_instance(*, instance_id: int, db_type: str = "sqlserver") -> SimpleNamespace:
    return SimpleNamespace(
        id=instance_id,
        name=f"instance-{instance_id}",
        db_type=db_type,
        host="127.0.0.1",
        port=1433,
        description=None,
        is_active=True,
        deleted_at=None,
        main_version="16.0",
    )


def _build_metrics() -> InstanceListMetrics:
    return InstanceListMetrics(
        database_counts={},
        account_counts={},
        last_sync_times={},
        tags_map={},
        audit_facts_map={},
        jumpserver_managed_ids=set(),
    )


class _StubRepository:
    def __init__(self, *, items, metrics: InstanceListMetrics) -> None:
        self._page = PaginatedResult(items=list(items), total=len(items), page=1, pages=1, limit=20)
        self._metrics = metrics

    def list_instances(self, filters: InstanceListFilters):  # type: ignore[no-untyped-def]
        assert filters.page == 1
        return self._page, self._metrics


@pytest.mark.unit
@pytest.mark.parametrize(
    ("db_type", "facts", "expected"),
    [
        ("sqlserver", {"has_audit": True, "enabled_audit_count": 1}, "enabled"),
        ("sqlserver", {"has_audit": True, "enabled_audit_count": 0}, "configured_disabled"),
        ("sqlserver", {"has_audit": False, "enabled_audit_count": 0}, "not_configured"),
        ("mysql", None, "not_configured"),
    ],
)
def test_instance_list_service_derives_audit_status_from_snapshot_facts(
    db_type: str,
    facts: dict[str, object] | None,
    expected: str,
) -> None:
    instance = _build_instance(instance_id=1, db_type=db_type)
    metrics = _build_metrics()
    if facts is not None:
        metrics = replace(metrics, audit_facts_map={1: facts})

    service = InstanceListService(repository=_StubRepository(items=[instance], metrics=metrics))

    result = service.list_instances(_build_filters())

    assert result.items[0].audit_status == expected
