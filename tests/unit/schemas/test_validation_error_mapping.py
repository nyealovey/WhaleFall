import pytest
from pydantic import field_validator

from app.core.exceptions import ValidationError
from app.schemas.base import PayloadSchema
from app.schemas.validation import SchemaMessageKeyError, validate_or_raise


class _DemoSchema(PayloadSchema):
    username: str

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("用户名不能为空")
        return value


@pytest.mark.unit
def test_validate_or_raise_uses_original_value_error_message() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(_DemoSchema, {"username": "   "})

    assert str(excinfo.value) == "用户名不能为空"


@pytest.mark.unit
def test_validate_or_raise_maps_message_key_by_field() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(
            _DemoSchema,
            {"username": "   "},
            message_key_by_field={"username": "USERNAME_INVALID"},
        )

    assert excinfo.value.message_key == "USERNAME_INVALID"


class _MessageKeySchema(PayloadSchema):
    password: str

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        raise SchemaMessageKeyError("密码不符合规则", message_key="PASSWORD_INVALID")


@pytest.mark.unit
def test_validate_or_raise_respects_schema_message_key() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(_MessageKeySchema, {"password": "weak"})

    assert str(excinfo.value) == "密码不符合规则"
    assert excinfo.value.message_key == "PASSWORD_INVALID"
