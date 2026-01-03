import pytest
from werkzeug.datastructures import MultiDict

from app.utils.data_validator import DataValidator


@pytest.mark.unit
def test_validate_db_type_uses_static_allowlist() -> None:
    assert DataValidator.validate_db_type("MYSQL") is None
    assert DataValidator.validate_db_type("pg") is None
    assert DataValidator.validate_db_type("mongodb") == "不支持的数据库类型: mongodb"


@pytest.mark.unit
def test_validate_db_type_with_custom_override() -> None:
    DataValidator.set_custom_db_types(["clickhouse"])
    try:
        assert DataValidator.validate_db_type("clickhouse") is None
        assert DataValidator.validate_db_type("postgresql") == "不支持的数据库类型: postgresql"
    finally:
        DataValidator.set_custom_db_types(None)


@pytest.mark.unit
def test_sanitize_form_data_uses_getlist_for_multidict() -> None:
    payload: MultiDict[str, str] = MultiDict(
        [
            ("old_password", "SomePass1A"),
            ("new_password", "NewPass1A"),
            ("confirm_password", "NewPass1A"),
        ],
    )

    sanitized = DataValidator.sanitize_form_data(payload)
    assert sanitized["old_password"] == "SomePass1A"
    assert sanitized["new_password"] == "NewPass1A"
    assert sanitized["confirm_password"] == "NewPass1A"
