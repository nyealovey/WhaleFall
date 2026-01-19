"""Internal data contract 的统一返回结构.

说明:
- 该结构用于 internal payload（snapshot/cache/JSON column）的读入口，支持 fail-fast 或 best-effort。
- best-effort 时禁止返回裸 `{}`/`[]` 作为“成功”，必须返回可判定的结构（见标准）。
"""

from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict

from app.core.types.structures import JsonValue


class InternalContractOkResult(TypedDict):
    """internal contract 读取成功结果."""

    ok: Literal[True]
    contract: str
    version: int
    supported_versions: list[int]
    data: JsonValue


class InternalContractErrorResult(TypedDict):
    """internal contract 读取失败结果(best-effort)."""

    ok: Literal[False]
    contract: str
    version: int | None
    supported_versions: list[int]
    error_code: str
    message: str
    errors: list[str]


InternalContractResult: TypeAlias = InternalContractOkResult | InternalContractErrorResult


def build_internal_contract_ok(
    *,
    contract: str,
    version: int,
    supported_versions: list[int],
    data: JsonValue,
) -> InternalContractOkResult:
    """构造成功结果."""
    return {
        "ok": True,
        "contract": contract,
        "version": version,
        "supported_versions": list(supported_versions),
        "data": data,
    }


def build_internal_contract_error(
    *,
    contract: str,
    version: int | None,
    supported_versions: list[int],
    error_code: str,
    message: str,
    errors: list[str] | None = None,
) -> InternalContractErrorResult:
    """构造失败结果."""
    resolved_errors = list(errors or [])
    if error_code not in resolved_errors:
        resolved_errors.insert(0, error_code)

    return {
        "ok": False,
        "contract": contract,
        "version": version,
        "supported_versions": list(supported_versions),
        "error_code": error_code,
        "message": message,
        "errors": resolved_errors,
    }


__all__ = [
    "InternalContractErrorResult",
    "InternalContractOkResult",
    "InternalContractResult",
    "build_internal_contract_error",
    "build_internal_contract_ok",
]
