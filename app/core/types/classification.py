"""账户分类相关类型定义."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias, TypedDict

from app.core.types.structures import JsonDict, JsonValue

RuleExpression: TypeAlias = Mapping[str, JsonValue]


class ClassificationEngineResult(TypedDict, total=False):
    """底层分类引擎返回的原始结果结构."""

    success: bool
    message: str
    error: str
    classified_accounts: int
    total_classifications_added: int
    failed_count: int
    errors: list[str]
    total_accounts: int
    total_rules: int
    total_matches: int
    db_type_results: JsonDict


__all__ = ["ClassificationEngineResult", "RuleExpression"]
