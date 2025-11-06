import pytest

from app.services.database_sync.database_filters import DatabaseSyncFilterManager


class DummyInstance:
    def __init__(self, db_type: str) -> None:
        self.db_type = db_type


def test_should_exclude_exact(tmp_path):
    config = tmp_path / "filters.yaml"
    config.write_text(
        """
version: "1.0"
description: "test"

database_filters:
  mysql:
    exclude_databases:
      - mysql
      - information_schema
    exclude_patterns:
      - tmp_%
"""
    )
    manager = DatabaseSyncFilterManager(config)
    instance = DummyInstance("mysql")

    assert manager.should_exclude_database(instance, "mysql")[0]
    assert manager.should_exclude_database(instance, "information_schema")[0]
    assert not manager.should_exclude_database(instance, "userdb")[0]


def test_should_exclude_pattern(tmp_path):
    config = tmp_path / "filters.yaml"
    config.write_text(
        """
version: "1.0"
description: "test"

database_filters:
  mysql:
    exclude_databases: []
    exclude_patterns:
      - tmp_%
      - test__name
"""
    )
    manager = DatabaseSyncFilterManager(config)
    instance = DummyInstance("mysql")

    assert manager.should_exclude_database(instance, "tmp_cache")[0]
    assert manager.should_exclude_database(instance, "TEST__NAME")[0]
    assert not manager.should_exclude_database(instance, "temp_cache")[0]


def test_filter_helpers(tmp_path):
    config = tmp_path / "filters.yaml"
    config.write_text(
        """
version: "1.0"
description: "test"

database_filters:
  mysql:
    exclude_databases:
      - sys
    exclude_patterns:
      - tmp_%
"""
    )
    manager = DatabaseSyncFilterManager(config)
    instance = DummyInstance("mysql")

    allowed, excluded = manager.filter_database_names(instance, ["sys", "tmp_a", "primary"])
    assert allowed == ["primary"]
    assert sorted(excluded) == ["sys", "tmp_a"]

    payload = [
        {"database_name": "sys", "size_mb": 1},
        {"database_name": "primary", "size_mb": 2},
    ]
    kept, filtered = manager.filter_capacity_payload(instance, payload)
    assert kept == [{"database_name": "primary", "size_mb": 2}]
    assert filtered == ["sys"]


def test_unknown_db_type_returns_false(tmp_path):
    config = tmp_path / "filters.yaml"
    config.write_text("version: '1.0'\ndescription: test\ndatabase_filters: {}\n")
    manager = DatabaseSyncFilterManager(config)
    instance = DummyInstance("unknown")
    assert manager.should_exclude_database(instance, "foo") == (False, None)
