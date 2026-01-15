"""请求 payload 解析与规范化.

目标:
- 统一处理 JSON dict 与 Werkzeug MultiDict(form/query).
- 提供最小的输入规范化(字符串 strip/NUL 清理),并允许对敏感字段保留 raw 值.
- 支持按字段固定 list 形状,避免 MultiDict 单值/多值导致 payload 形状漂移.

注意:
- 本模块只负责 "取参形状" 与 "基础规范化",不做业务校验.
- 业务字段校验应交由 schema 层(pydantic)完成.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from flask import has_request_context, request

from app.core.types.structures import MutablePayloadDict, PayloadValue, ScalarValue

_STRING_LIKE_TYPES = (str, bytes, bytearray)
_PARSE_PAYLOAD_MARKER = "_wf_parse_payload_called"


def _guard_parse_payload_called_once() -> None:
    if not has_request_context():
        return
    if getattr(request, _PARSE_PAYLOAD_MARKER, False):
        raise RuntimeError("parse_payload 只允许在一次请求链路内执行一次")
    setattr(request, _PARSE_PAYLOAD_MARKER, True)


def parse_payload(
    payload: object | None,
    *,
    list_fields: Sequence[str] = (),
    preserve_raw_fields: Sequence[str] = (),
    boolean_fields_default_false: Sequence[str] = (),
    preserve_raw_password_fields_by_name: bool = False,
) -> MutablePayloadDict:
    """解析并规范化 payload.

    Args:
        payload: JSON dict 或 MultiDict 兼容对象.
        list_fields: 需要固定为 list 形状的字段名集合(单值也输出 list).
        preserve_raw_fields: 需要保留 raw 字符串的字段名集合(例如 password 字段).
        boolean_fields_default_false: 仅对 MultiDict 生效: 当字段缺失时默认补 False(用于 checkbox 未勾选的场景).
        preserve_raw_password_fields_by_name: 为了兼容旧行为,默认对字段名包含 "password" 的字段保留 raw.

    Returns:
        规范化后的 payload dict.

    """
    _guard_parse_payload_called_once()
    list_field_set = set(list_fields)
    raw_field_set = set(preserve_raw_fields)

    if payload is None:
        return {}

    if hasattr(payload, "getlist"):
        parsed = _parse_multidict(
            payload,
            list_fields=list_field_set,
            preserve_raw_fields=raw_field_set,
            preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
        )
        for key in boolean_fields_default_false:
            if key not in parsed:
                parsed[key] = False
        return parsed

    if isinstance(payload, Mapping):
        return _parse_mapping(
            payload,
            list_fields=list_field_set,
            preserve_raw_fields=raw_field_set,
            preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
        )

    raise TypeError("payload 必须为 mapping 或 MultiDict 兼容对象")


def _parse_multidict(
    payload: object,
    *,
    list_fields: set[str],
    preserve_raw_fields: set[str],
    preserve_raw_password_fields_by_name: bool,
) -> MutablePayloadDict:
    multi_dict = cast(Any, payload)
    sanitized: MutablePayloadDict = {}
    keys = list(multi_dict.keys())
    for key in keys:
        values = list(multi_dict.getlist(key) or [])
        if not values:
            sanitized[key] = None
            continue

        cleaned_values: list[ScalarValue] = [
            _sanitize_scalar_value(
                value,
                field_name=key,
                preserve_raw_fields=preserve_raw_fields,
                preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
            )
            for value in values
        ]
        if key in list_fields:
            sanitized[key] = cleaned_values
        else:
            sanitized[key] = cleaned_values[-1]
    return sanitized


def _parse_mapping(
    payload: Mapping[str, object],
    *,
    list_fields: set[str],
    preserve_raw_fields: set[str],
    preserve_raw_password_fields_by_name: bool,
) -> MutablePayloadDict:
    sanitized: MutablePayloadDict = {}
    for key, value in payload.items():
        sanitized[key] = _sanitize_value(
            value,
            field_name=key,
            force_list=(key in list_fields),
            preserve_raw_fields=preserve_raw_fields,
            preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
        )
    return sanitized


def _sanitize_value(
    value: object,
    *,
    field_name: str,
    force_list: bool,
    preserve_raw_fields: set[str],
    preserve_raw_password_fields_by_name: bool,
) -> PayloadValue:
    if force_list:
        if value is None:
            return []
        if isinstance(value, Sequence) and not isinstance(value, _STRING_LIKE_TYPES):
            return [
                _sanitize_scalar_value(
                    item,
                    field_name=field_name,
                    preserve_raw_fields=preserve_raw_fields,
                    preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
                )
                for item in value
            ]
        return [
            _sanitize_scalar_value(
                value,
                field_name=field_name,
                preserve_raw_fields=preserve_raw_fields,
                preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
            ),
        ]

    if isinstance(value, Sequence) and not isinstance(value, _STRING_LIKE_TYPES):
        if not value:
            return None
        return _sanitize_scalar_value(
            value[-1],
            field_name=field_name,
            preserve_raw_fields=preserve_raw_fields,
            preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
        )

    return _sanitize_scalar_value(
        value,
        field_name=field_name,
        preserve_raw_fields=preserve_raw_fields,
        preserve_raw_password_fields_by_name=preserve_raw_password_fields_by_name,
    )


def _sanitize_scalar_value(
    value: object,
    *,
    field_name: str,
    preserve_raw_fields: set[str],
    preserve_raw_password_fields_by_name: bool,
) -> ScalarValue:
    if value is None:
        return None

    preserve_raw = _should_preserve_raw(field_name, preserve_raw_fields, preserve_raw_password_fields_by_name)
    if isinstance(value, (bool, int, float)):
        return cast(ScalarValue, value)
    if isinstance(value, (bytes, bytearray)):
        decoded = value.decode(errors="ignore")
        return decoded if preserve_raw else _strip_nul(decoded)
    if isinstance(value, str):
        return value if preserve_raw else _strip_nul(value)
    raw = str(value)
    return raw if preserve_raw else _strip_nul(raw)


def _strip_nul(value: str) -> str:
    return value.replace("\x00", "").strip()


def _should_preserve_raw(
    field_name: str,
    preserve_raw_fields: set[str],
    preserve_raw_password_fields_by_name: bool,
) -> bool:
    return field_name in preserve_raw_fields or (
        preserve_raw_password_fields_by_name and "password" in field_name.lower()
    )
