from types import SimpleNamespace

import pytest

from app.utils.data_validator import DataValidator


@pytest.mark.unit
def test_validate_db_type_uses_dynamic_configs(monkeypatch) -> None:
    from app.services import database_type_service

    monkeypatch.setattr(
        database_type_service.DatabaseTypeService,
        "get_active_types",
        staticmethod(lambda: [SimpleNamespace(name="mongodb"), SimpleNamespace(name="mysql")]),
    )

    assert DataValidator.validate_db_type("mongodb") is None


@pytest.mark.unit
def test_validate_db_type_with_custom_override() -> None:
    DataValidator.set_custom_db_types(["clickhouse"])
    try:
        assert DataValidator.validate_db_type("clickhouse") is None
        assert DataValidator.validate_db_type("postgresql") == "不支持的数据库类型: postgresql"
    finally:
        DataValidator.set_custom_db_types(None)
