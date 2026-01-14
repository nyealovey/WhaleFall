"""账户分类写路径 schema."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic import StrictStr, field_validator, model_validator

from app.core.constants import DatabaseType
from app.core.constants.classification_constants import ICON_OPTIONS, OPERATOR_OPTIONS, RISK_LEVEL_OPTIONS
from app.schemas.base import PayloadSchema
from app.schemas.validation import SchemaMessageKeyError
from app.utils.account_classification_dsl_v4 import collect_dsl_v4_validation_errors, is_dsl_v4_expression
from app.utils.database_type_utils import normalize_database_type
from app.utils.payload_converters import as_bool
from app.utils.theme_color_utils import is_valid_theme_color

_RISK_LEVEL_VALUES = {item["value"] for item in RISK_LEVEL_OPTIONS}
_ICON_VALUES = {item["value"] for item in ICON_OPTIONS}
_OPERATOR_VALUES = {item["value"] for item in OPERATOR_OPTIONS}
_DB_TYPE_VALUES = {normalize_database_type(item) for item in DatabaseType.RELATIONAL}


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise TypeError("参数格式错误")
    return data


def _require_fields(data: Any, *, required: tuple[str, ...]) -> Any:
    mapping = _ensure_mapping(data)
    missing: list[str] = []
    for field in required:
        if field not in mapping:
            missing.append(field)
            continue
        value = mapping.get(field)
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
    if missing:
        raise ValueError(f"缺少必填字段: {', '.join(missing)}")
    return data


def _parse_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


def _parse_description(value: Any, *, fallback: str | None) -> str:
    if value is None:
        return fallback or ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_priority(value: Any, *, fallback: int | None) -> int | None:
    if value is None:
        return fallback
    if isinstance(value, bool):
        raise ValueError("优先级必须为整数")  # noqa: TRY004
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("优先级必须为整数") from exc
    return max(0, min(parsed, 100))


def _parse_positive_int(value: Any, *, message: str) -> int:
    if value is None or value == "":
        raise ValueError(message)
    if isinstance(value, bool):
        raise ValueError(message)  # noqa: TRY004
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc
    if parsed <= 0:
        raise ValueError(message)
    return parsed


def _normalize_rule_expression(value: Any) -> tuple[str, dict[str, object]]:
    raw_value = value
    if raw_value is None:
        raise ValueError("缺少 rule_expression 字段")
    if isinstance(raw_value, str):
        if not raw_value.strip():
            raise ValueError("缺少 rule_expression 字段")
        try:
            raw_value = json.loads(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"规则表达式格式错误: {exc}") from exc

    if raw_value is None:
        raw_value = {}
    if not isinstance(raw_value, dict):
        raise ValueError("规则表达式必须为对象")  # noqa: TRY004

    normalized = json.dumps(raw_value, ensure_ascii=False, sort_keys=True)
    return normalized, raw_value


class AccountClassificationCreatePayload(PayloadSchema):
    """创建账户分类 payload."""

    name: StrictStr
    description: StrictStr = ""
    risk_level: StrictStr = "medium"
    color: StrictStr = "info"
    icon_name: StrictStr = "fa-tag"
    priority: int = 0

    @model_validator(mode="before")
    @classmethod
    def _require_name(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        raw_name = mapping.get("name")
        if raw_name is None or (isinstance(raw_name, str) and not raw_name.strip()):
            raise ValueError("分类名称不能为空")
        return data

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("分类名称不能为空")
        return cleaned

    @field_validator("description", mode="before")
    @classmethod
    def _parse_description(cls, value: Any) -> str:
        return _parse_description(value, fallback="")

    @field_validator("risk_level", mode="before")
    @classmethod
    def _parse_risk_level(cls, value: Any) -> str:
        if value is None:
            return "medium"
        if isinstance(value, str):
            return value.strip().lower()
        return str(value).strip().lower()

    @field_validator("risk_level")
    @classmethod
    def _validate_risk_level(cls, value: str) -> str:
        if value not in _RISK_LEVEL_VALUES:
            raise ValueError("风险等级取值无效")
        return value

    @field_validator("color", mode="before")
    @classmethod
    def _parse_color(cls, value: Any) -> str:
        if value is None:
            return "info"
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator("color")
    @classmethod
    def _validate_color(cls, value: str) -> str:
        if not is_valid_theme_color(value):
            raise ValueError("无效的颜色选择")
        return value

    @field_validator("icon_name", mode="before")
    @classmethod
    def _parse_icon_name(cls, value: Any) -> str:
        if value is None:
            return "fa-tag"
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator("icon_name")
    @classmethod
    def _validate_icon_name(cls, value: str) -> str:
        if value not in _ICON_VALUES:
            raise ValueError("图标取值无效")
        return value

    @field_validator("priority", mode="before")
    @classmethod
    def _parse_priority(cls, value: Any) -> int:
        parsed = _parse_priority(value, fallback=0)
        if parsed is None:
            raise ValueError("优先级必须为整数")
        return parsed


class AccountClassificationUpdatePayload(PayloadSchema):
    """更新账户分类 payload(支持按字段更新)."""

    name: StrictStr | None = None
    description: StrictStr | None = None
    risk_level: StrictStr | None = None
    color: StrictStr | None = None
    icon_name: StrictStr | None = None
    priority: int | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _parse_name(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("分类名称不能为空")
        return cleaned

    @field_validator("description", mode="before")
    @classmethod
    def _parse_description(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _parse_description(value, fallback=None)

    @field_validator("risk_level", mode="before")
    @classmethod
    def _parse_risk_level(cls, value: Any) -> str | None:
        parsed = _parse_optional_string(value)
        return parsed.lower() if parsed else None

    @field_validator("risk_level")
    @classmethod
    def _validate_risk_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in _RISK_LEVEL_VALUES:
            raise ValueError("风险等级取值无效")
        return value

    @field_validator("color", mode="before")
    @classmethod
    def _parse_color(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("color")
    @classmethod
    def _validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_valid_theme_color(value):
            raise ValueError("无效的颜色选择")
        return value

    @field_validator("icon_name", mode="before")
    @classmethod
    def _parse_icon_name(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("icon_name")
    @classmethod
    def _validate_icon_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in _ICON_VALUES:
            raise ValueError("图标取值无效")
        return value

    @field_validator("priority", mode="before")
    @classmethod
    def _parse_priority(cls, value: Any) -> int | None:
        return _parse_priority(value, fallback=None)


class AccountClassificationRuleCreatePayload(PayloadSchema):
    """创建分类规则 payload."""

    rule_name: StrictStr
    classification_id: int
    db_type: StrictStr
    operator: StrictStr
    rule_expression: str
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _require_fields(cls, data: Any) -> Any:
        return _require_fields(data, required=("rule_name", "classification_id", "db_type", "operator", "rule_expression"))

    @field_validator("rule_name")
    @classmethod
    def _validate_rule_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("缺少必填字段: rule_name")
        return cleaned

    @field_validator("classification_id", mode="before")
    @classmethod
    def _parse_classification_id(cls, value: Any) -> int:
        return _parse_positive_int(value, message="选择的分类不存在")

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str:
        parsed = _parse_optional_string(value)
        if not parsed:
            raise ValueError("数据库类型取值无效")
        return normalize_database_type(parsed)

    @field_validator("db_type")
    @classmethod
    def _validate_db_type(cls, value: str) -> str:
        if value not in _DB_TYPE_VALUES:
            raise ValueError("数据库类型取值无效")
        return value

    @field_validator("operator", mode="before")
    @classmethod
    def _parse_operator(cls, value: Any) -> str:
        parsed = _parse_optional_string(value)
        if not parsed:
            raise ValueError("匹配逻辑取值无效")
        return parsed.strip().upper()

    @field_validator("operator")
    @classmethod
    def _validate_operator(cls, value: str) -> str:
        if value not in _OPERATOR_VALUES:
            raise ValueError("匹配逻辑取值无效")
        return value

    @field_validator("rule_expression", mode="before")
    @classmethod
    def _parse_rule_expression(cls, value: Any) -> str:
        normalized, parsed = _normalize_rule_expression(value)

        if not is_dsl_v4_expression(parsed):
            raise SchemaMessageKeyError("仅支持 DSL v4 表达式(version=4)", message_key="DSL_V4_REQUIRED")

        errors = collect_dsl_v4_validation_errors(parsed)
        if errors:
            raise SchemaMessageKeyError(
                "DSL v4 规则表达式校验失败",
                message_key="INVALID_DSL_EXPRESSION",
                extra={"errors": errors},
            )

        return normalized

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool:
        if value is None:
            return True
        return as_bool(value, default=True)


class AccountClassificationRuleUpdatePayload(PayloadSchema):
    """更新分类规则 payload."""

    rule_name: StrictStr
    classification_id: int
    db_type: StrictStr
    operator: StrictStr
    rule_expression: str | None = None
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _require_fields(cls, data: Any) -> Any:
        return _require_fields(data, required=("rule_name", "classification_id", "db_type", "operator"))

    @field_validator("rule_name")
    @classmethod
    def _validate_rule_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("缺少必填字段: rule_name")
        return cleaned

    @field_validator("classification_id", mode="before")
    @classmethod
    def _parse_classification_id(cls, value: Any) -> int:
        return _parse_positive_int(value, message="选择的分类不存在")

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str:
        parsed = _parse_optional_string(value)
        if not parsed:
            raise ValueError("数据库类型取值无效")
        return normalize_database_type(parsed)

    @field_validator("db_type")
    @classmethod
    def _validate_db_type(cls, value: str) -> str:
        if value not in _DB_TYPE_VALUES:
            raise ValueError("数据库类型取值无效")
        return value

    @field_validator("operator", mode="before")
    @classmethod
    def _parse_operator(cls, value: Any) -> str:
        parsed = _parse_optional_string(value)
        if not parsed:
            raise ValueError("匹配逻辑取值无效")
        return parsed.strip().upper()

    @field_validator("operator")
    @classmethod
    def _validate_operator(cls, value: str) -> str:
        if value not in _OPERATOR_VALUES:
            raise ValueError("匹配逻辑取值无效")
        return value

    @field_validator("rule_expression", mode="before")
    @classmethod
    def _parse_rule_expression(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized, parsed = _normalize_rule_expression(value)

        if not is_dsl_v4_expression(parsed):
            raise SchemaMessageKeyError("仅支持 DSL v4 表达式(version=4)", message_key="DSL_V4_REQUIRED")

        errors = collect_dsl_v4_validation_errors(parsed)
        if errors:
            raise SchemaMessageKeyError(
                "DSL v4 规则表达式校验失败",
                message_key="INVALID_DSL_EXPRESSION",
                extra={"errors": errors},
            )

        return normalized

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return as_bool(value, default=False)
