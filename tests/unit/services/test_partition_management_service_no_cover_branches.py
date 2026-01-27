from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace

import pytest

import app.services.partition_management_service as partition_management_service_module
from app.core.exceptions import DatabaseError
from app.services.partition_management_service import PartitionManagementService


@pytest.mark.unit
def test_create_partition_logs_and_reports_failure_when_create_partition_table_raises(monkeypatch) -> None:
    service = PartitionManagementService()
    service.tables = {
        "stats": {
            "table_name": "database_size_stats",
            "partition_prefix": "database_size_stats_",
            "partition_column": "collected_date",
            "display_name": "数据库统计表",
        },
    }

    @contextmanager
    def _begin_nested():
        yield

    log_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        log_calls.append((message, dict(kwargs)))

    monkeypatch.setattr(service, "_partition_exists", lambda _name: False)
    monkeypatch.setattr(partition_management_service_module.db.session, "begin_nested", _begin_nested)

    def _raise_create(**_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(service._repository, "create_partition_table", _raise_create)
    monkeypatch.setattr(partition_management_service_module, "log_error", _fake_log_error)

    with pytest.raises(DatabaseError):
        service.create_partition(date(2099, 12, 27))

    assert any(msg == "创建分区发生未知错误" for msg, _ in log_calls)


@pytest.mark.unit
def test_cleanup_old_partitions_logs_and_reports_failure_when_drop_partition_table_raises(monkeypatch) -> None:
    service = PartitionManagementService()
    service.tables = {
        "stats": {
            "table_name": "database_size_stats",
            "partition_prefix": "database_size_stats_",
            "partition_column": "collected_date",
            "display_name": "数据库统计表",
        },
    }

    @contextmanager
    def _begin_nested():
        yield

    log_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        log_calls.append((message, dict(kwargs)))

    monkeypatch.setattr(partition_management_service_module.db.session, "begin_nested", _begin_nested)
    monkeypatch.setattr(service, "_get_partitions_to_cleanup", lambda *_args, **_kwargs: ["p_2099_01"])

    def _raise_drop(**_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(service._repository, "drop_partition_table", _raise_drop)
    monkeypatch.setattr(partition_management_service_module, "log_error", _fake_log_error)

    with pytest.raises(DatabaseError):
        service.cleanup_old_partitions(retention_months=1)

    assert any(msg == "删除旧分区遇到未捕获异常" for msg, _ in log_calls)


@pytest.mark.unit
def test_get_table_partitions_skips_bad_row_when_extract_date_raises(monkeypatch) -> None:
    service = PartitionManagementService()

    rows = [SimpleNamespace(tablename="bad_name", size="1 MB", size_bytes=123)]
    monkeypatch.setattr(service._repository, "fetch_partition_rows", lambda **_kwargs: rows)

    def _raise_extract(*_args: object, **_kwargs: object) -> object:
        raise ValueError("boom")

    monkeypatch.setattr(service, "_extract_date_from_partition_name", _raise_extract)

    warning_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_warning(message: str, **kwargs: object) -> None:
        warning_calls.append((message, dict(kwargs)))

    monkeypatch.setattr(partition_management_service_module, "log_warning", _fake_log_warning)

    table_config = {
        "table_name": "database_size_stats",
        "partition_prefix": "database_size_stats_",
        "partition_column": "collected_date",
        "display_name": "数据库统计表",
    }
    partitions = service._get_table_partitions("stats", table_config)

    assert partitions == []
    assert any(msg == "处理单个分区信息失败" for msg, _ in warning_calls)
