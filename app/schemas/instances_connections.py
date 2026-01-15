"""Instances connections 写路径 schema."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import StrictStr, field_validator, model_validator

from app.core.constants.database_types import DatabaseType
from app.schemas.base import PayloadSchema
from app.schemas.validation import SchemaMessageKeyError

MIN_ALLOWED_PORT = 1
MAX_ALLOWED_PORT = 65535
MAX_BATCH_TEST_SIZE = 50


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise SchemaMessageKeyError("请求体必须是 JSON 对象", message_key="VALIDATION_ERROR")
    return data


def _parse_int(value: Any, *, message: str) -> int:
    if value is None or value == "":
        raise ValueError(message)
    if isinstance(value, bool):
        raise ValueError(message)  # noqa: TRY004
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc


class InstanceConnectionTestPayload(PayloadSchema):
    """连接测试 payload."""

    instance_id: int | None = None
    db_type: StrictStr | None = None
    host: StrictStr | None = None
    port: int | None = None
    credential_id: int | None = None
    name: StrictStr | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_mode_and_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        if not mapping:
            raise SchemaMessageKeyError("请求数据不能为空", message_key="VALIDATION_ERROR")

        if "instance_id" in mapping:
            raw_id = mapping.get("instance_id")
            if raw_id is None or raw_id == "":
                raise SchemaMessageKeyError("instance_id 不能为空", message_key="VALIDATION_ERROR")
            # 既有实例测试仅需要 instance_id,其余字段忽略(保持与历史行为一致)
            return {"instance_id": raw_id}

        missing: list[str] = []
        for field_name in ("db_type", "host", "port", "credential_id"):
            value = mapping.get(field_name)
            if value is None:
                missing.append(field_name)
                continue
            if isinstance(value, str) and not value.strip():
                missing.append(field_name)
        if missing:
            raise SchemaMessageKeyError(f"缺少必需参数: {', '.join(missing)}", message_key="VALIDATION_ERROR")

        return data

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int | None:
        if value is None:
            return None
        return _parse_int(value, message="instance_id 必须是整数")

    @field_validator("credential_id", mode="before")
    @classmethod
    def _parse_credential_id(cls, value: Any) -> int | None:
        if value is None:
            return None
        return _parse_int(value, message="credential_id 必须是整数")

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("不支持的数据库类型")  # noqa: TRY004
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        return cleaned

    @field_validator("db_type")
    @classmethod
    def _validate_db_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in DatabaseType.RELATIONAL:
            raise ValueError(f"不支持的数据库类型: {value}")
        return value

    @field_validator("host", mode="before")
    @classmethod
    def _parse_host(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return str(value)
        return value

    @field_validator("port", mode="before")
    @classmethod
    def _parse_port(cls, value: Any) -> int | None:
        if value is None:
            return None
        port = _parse_int(value, message="端口号必须是有效的数字")
        if port < MIN_ALLOWED_PORT or port > MAX_ALLOWED_PORT:
            raise ValueError(f"端口号必须在{MIN_ALLOWED_PORT}-{MAX_ALLOWED_PORT}之间")
        return port


class InstanceConnectionParamsPayload(PayloadSchema):
    """连接参数验证 payload."""

    db_type: StrictStr
    port: int
    credential_id: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        db_type = mapping.get("db_type")
        port = mapping.get("port")
        if db_type is None or (isinstance(db_type, str) and not db_type.strip()):
            raise SchemaMessageKeyError("缺少 db_type", message_key="VALIDATION_ERROR")
        if port is None or port == "":
            raise SchemaMessageKeyError("缺少端口", message_key="VALIDATION_ERROR")
        return data

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("不支持的数据库类型")  # noqa: TRY004
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("缺少 db_type")
        if cleaned not in DatabaseType.RELATIONAL:
            raise ValueError(f"不支持的数据库类型: {cleaned}")
        return cleaned

    @field_validator("port", mode="before")
    @classmethod
    def _parse_port(cls, value: Any) -> int:
        port = _parse_int(value, message="端口号必须是有效的数字")
        if port < MIN_ALLOWED_PORT or port > MAX_ALLOWED_PORT:
            raise ValueError(f"端口号必须在{MIN_ALLOWED_PORT}-{MAX_ALLOWED_PORT}之间")
        return port

    @field_validator("credential_id", mode="before")
    @classmethod
    def _parse_credential_id(cls, value: Any) -> int | None:
        if value is None:
            return None
        return _parse_int(value, message="credential_id 必须是整数")


class InstanceConnectionBatchTestPayload(PayloadSchema):
    """批量连接测试 payload."""

    instance_ids: list[int]

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        if "instance_ids" not in mapping:
            raise SchemaMessageKeyError("缺少实例ID列表", message_key="VALIDATION_ERROR")
        return data

    @field_validator("instance_ids", mode="before")
    @classmethod
    def _parse_instance_ids(cls, value: Any) -> list[int]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ValueError("实例ID列表不能为空")  # noqa: TRY004
        raw_list = list(value)
        if not raw_list:
            raise ValueError("实例ID列表不能为空")

        parsed: list[int] = []
        for item in raw_list:
            if isinstance(item, bool):
                raise ValueError("实例ID列表必须为整数")  # noqa: TRY004
            try:
                parsed.append(int(item))
            except (TypeError, ValueError) as exc:
                raise ValueError("实例ID列表必须为整数") from exc

        if len(parsed) > MAX_BATCH_TEST_SIZE:
            raise ValueError(f"批量测试数量不能超过{MAX_BATCH_TEST_SIZE}个")

        return parsed
