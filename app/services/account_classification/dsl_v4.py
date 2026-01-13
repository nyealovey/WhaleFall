"""Account classification DSL v4 (re-export).

说明:
- 为了让 schema 层复用 DSL 校验而不依赖 `app.services.*`,
  DSL v4 实现已迁移到 `app/utils/account_classification_dsl_v4.py`.
- 本模块保留为向后兼容的 re-export, 避免大量改动 import 路径.
"""

from __future__ import annotations

from app.utils.account_classification_dsl_v4 import (
    DSL_ERROR_INVALID_ARGS,
    DSL_ERROR_MISSING_ARGS,
    DSL_ERROR_UNKNOWN_FUNCTION,
    DSL_V4_VERSION,
    DslEvaluationOutcome,
    DslV4Evaluator,
    collect_dsl_v4_validation_errors,
    is_dsl_v4_expression,
)

__all__ = [
    "DSL_ERROR_INVALID_ARGS",
    "DSL_ERROR_MISSING_ARGS",
    "DSL_ERROR_UNKNOWN_FUNCTION",
    "DSL_V4_VERSION",
    "DslEvaluationOutcome",
    "DslV4Evaluator",
    "collect_dsl_v4_validation_errors",
    "is_dsl_v4_expression",
]

