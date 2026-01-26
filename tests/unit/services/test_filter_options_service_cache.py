from __future__ import annotations

from typing import Any, cast

import pytest
from flask_caching import Cache

from app.services.common.filter_options_service import FilterOptionsService
from app.utils.cache_utils import CacheManager, CacheManagerRegistry


class _DummyCache:
    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self._store.get(key)

    def set(self, key: str, value: object, *, timeout: int) -> None:  # noqa: ARG002
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


@pytest.mark.unit
def test_filter_options_service_caches_instance_select_options_empty_list(monkeypatch) -> None:
    calls = {"repo": 0}

    class _Repo:
        def list_active_instances(self, *, db_type=None):  # noqa: ANN001
            calls["repo"] += 1
            return []

    manager = CacheManager(cache=cast(Cache, _DummyCache()))
    monkeypatch.setattr(CacheManagerRegistry, "_manager", manager, raising=False)

    service = FilterOptionsService(repository=cast(Any, _Repo()))
    assert service.list_instance_select_options(db_type=None) == []
    assert service.list_instance_select_options(db_type=None) == []
    assert calls["repo"] == 1


@pytest.mark.unit
def test_filter_options_service_instance_select_options_cache_key_varies_by_db_type(monkeypatch) -> None:
    calls = {"repo": 0}

    class _Repo:
        def list_active_instances(self, *, db_type=None):  # noqa: ANN001
            calls["repo"] += 1
            return []

    manager = CacheManager(cache=cast(Cache, _DummyCache()))
    monkeypatch.setattr(CacheManagerRegistry, "_manager", manager, raising=False)

    service = FilterOptionsService(repository=cast(Any, _Repo()))
    assert service.list_instance_select_options(db_type=None) == []
    assert service.list_instance_select_options(db_type="mysql") == []
    assert service.list_instance_select_options(db_type="mysql") == []
    assert calls["repo"] == 2
