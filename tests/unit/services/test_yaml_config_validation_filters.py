"""filters YAML 配置读取入口的 schema 门禁测试."""

from __future__ import annotations

from typing import Any, cast

import pytest
import yaml

from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.services.database_sync.database_filters import DatabaseSyncFilterManager


class _DummyInstance:
    def __init__(self, db_type: str) -> None:
        self.db_type = db_type


@pytest.mark.unit
def test_account_filters_yaml_validated_at_entry(tmp_path) -> None:
    """账户同步 filters 应在读取入口完成校验/规范化."""
    config_path = tmp_path / "account_filters.yaml"
    config_path.write_text(
        "\n".join(
            [
                "account_filters:",
                "  MySQL:",
                "    exclude_users: [' root ', '']",
                "    exclude_patterns:",
                "      - ' mysql% '",
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    manager = DatabaseFilterManager(config_path=config_path)

    rules = manager.filter_rules
    assert "mysql" in rules
    assert rules["mysql"]["exclude_users"] == ["root"]
    assert rules["mysql"]["exclude_patterns"] == ["mysql%"]


@pytest.mark.unit
def test_account_filters_yaml_invalid_schema_raises_value_error(tmp_path) -> None:
    config_path = tmp_path / "account_filters.yaml"
    config_path.write_text("account_filters: []\n", encoding="utf-8")

    with pytest.raises(ValueError):
        DatabaseFilterManager(config_path=config_path)


@pytest.mark.unit
def test_database_filters_yaml_validated_at_entry(tmp_path) -> None:
    """容量同步 database filters 应在读取入口完成校验/规范化."""
    config_path = tmp_path / "database_filters.yaml"
    config_path.write_text(
        "\n".join(
            [
                "database_filters:",
                "  mysql:",
                "    exclude_databases: [' information_schema ']",
                "    exclude_patterns: [' tmp_% ']",
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    manager = DatabaseSyncFilterManager(config_path=config_path)

    instance = cast(Any, _DummyInstance("mysql"))
    should_exclude, reason = manager.should_exclude_database(instance, "information_schema")
    assert should_exclude is True
    assert reason == "exclude_database"

    should_exclude, reason = manager.should_exclude_database(instance, "tmp_foo")
    assert should_exclude is True
    assert reason == "exclude_pattern:tmp_%"


@pytest.mark.unit
def test_database_filters_yaml_invalid_schema_raises_value_error(tmp_path) -> None:
    config_path = tmp_path / "database_filters.yaml"
    config_path.write_text("version: '1.0'\n", encoding="utf-8")

    with pytest.raises(ValueError):
        DatabaseSyncFilterManager(config_path=config_path)


@pytest.mark.unit
def test_database_filters_yaml_invalid_syntax_raises_value_error(tmp_path) -> None:
    config_path = tmp_path / "database_filters.yaml"
    config_path.write_text("database_filters: [\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        DatabaseSyncFilterManager(config_path=config_path)

    assert isinstance(exc_info.value.__cause__, yaml.YAMLError)
