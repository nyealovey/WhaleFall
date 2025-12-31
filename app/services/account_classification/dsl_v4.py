"""Account classification DSL v4.

DSL v4 shape (minimal):

{
  "version": 4,
  "expr": {
    "op": "AND" | "OR",
    "args": [
      {"fn": "has_capability", "args": {"name": "GRANT_ADMIN"}},
      {"fn": "has_privilege", "args": {"name": "SELECT", "scope": "global"}}
    ]
  }
}

Supported core functions:
- db_type_in(types: list[str])
- is_superuser()
- has_capability(name: str)
- has_role(name: str)
- has_privilege(name: str, scope: str, database?: str)

Notes:
- Unknown function / invalid args should fail closed (return False).
- AND/OR must short-circuit like Python `and` / `or`.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.utils.structlog_config import log_error

DSL_ERROR_UNKNOWN_FUNCTION = "UNKNOWN_DSL_FUNCTION"
DSL_ERROR_INVALID_ARGS = "INVALID_DSL_ARGS"
DSL_ERROR_MISSING_ARGS = "MISSING_DSL_ARGS"

try:  # pragma: no cover - optional dependency
    from prometheus_client import Counter as _Counter
    from prometheus_client import Histogram as _Histogram
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    _Counter = None
    _Histogram = None


class _NoopMetric:
    def labels(self, *args: object, **kwargs: object) -> _NoopMetric:
        return self

    def inc(self, *args: object, **kwargs: object) -> None:
        return

    def observe(self, *args: object, **kwargs: object) -> None:
        return


def _build_counter(name: str, documentation: str, labelnames: list[str]) -> _NoopMetric:
    if _Counter is None:  # pragma: no cover
        return _NoopMetric()
    return _Counter(name, documentation, labelnames)  # type: ignore[return-value]


def _build_histogram(name: str, documentation: str, labelnames: list[str]) -> _NoopMetric:
    if _Histogram is None:  # pragma: no cover
        return _NoopMetric()
    return _Histogram(name, documentation, labelnames)  # type: ignore[return-value]


dsl_evaluation_duration = _build_histogram(
    "account_classification_dsl_evaluation_duration_seconds",
    "DSL evaluation duration per function",
    ["function"],
)
dsl_evaluation_errors = _build_counter(
    "account_classification_dsl_evaluation_errors_total",
    "DSL evaluation errors",
    ["error_type"],
)


def is_dsl_v4_expression(expression: object) -> bool:
    if not isinstance(expression, Mapping):
        return False
    return expression.get("version") == 4 and isinstance(expression.get("expr"), Mapping)


def collect_dsl_v4_validation_errors(expression: object) -> list[str]:
    """Validate expression structure and return human-readable errors (empty when valid)."""
    errors: list[str] = []

    if not isinstance(expression, Mapping):
        return ["rule_expression 必须为对象"]

    if expression.get("version") != 4:
        errors.append("rule_expression.version 必须为 4")
        return errors

    root_expr = expression.get("expr")
    if not isinstance(root_expr, Mapping):
        errors.append("rule_expression.expr 必须为对象")
        return errors

    def _path(parent: str, key: str) -> str:
        return f"{parent}.{key}" if parent else key

    def _validate_node(node: object, *, path: str) -> None:
        if not isinstance(node, Mapping):
            errors.append(f"{path} 必须为对象")
            return

        if "op" in node:
            op = node.get("op")
            if not isinstance(op, str) or not op.strip():
                errors.append(f"{path}.op 必须为字符串")
                return
            op_norm = op.strip().upper()
            if op_norm not in {"AND", "OR", "NOT"}:
                errors.append(f"{path}.op 不支持: {op}")
                return
            args = node.get("args")
            if not isinstance(args, list):
                errors.append(f"{path}.args 必须为数组")
                return
            if op_norm == "NOT" and len(args) != 1:
                errors.append(f"{path}.args 在 NOT 时必须仅包含 1 个子表达式")
            for idx, item in enumerate(args):
                _validate_node(item, path=f"{path}.args[{idx}]")
            return

        if "fn" in node:
            fn = node.get("fn")
            if not isinstance(fn, str) or not fn.strip():
                errors.append(f"{path}.fn 必须为字符串")
                return
            fn_name = fn.strip()

            raw_args = node.get("args", {})
            if raw_args is None:
                raw_args = {}
            if not isinstance(raw_args, Mapping):
                errors.append(f"{path}.args 必须为对象")
                return

            # Function-specific minimal validation
            if fn_name == "db_type_in":
                types = raw_args.get("types")
                if types is None:
                    errors.append(f"{path}.args.types 缺失")
                elif not isinstance(types, list) or not all(isinstance(item, str) and item for item in types):
                    errors.append(f"{path}.args.types 必须为非空字符串数组")
                return

            if fn_name == "is_superuser":
                return

            if fn_name in {"has_capability", "has_role"}:
                name = raw_args.get("name")
                if not isinstance(name, str) or not name.strip():
                    errors.append(f"{path}.args.name 必须为非空字符串")
                return

            if fn_name == "has_privilege":
                name = raw_args.get("name")
                scope = raw_args.get("scope")
                database = raw_args.get("database")
                if not isinstance(name, str) or not name.strip():
                    errors.append(f"{path}.args.name 必须为非空字符串")
                if not isinstance(scope, str) or not scope.strip():
                    errors.append(f"{path}.args.scope 必须为非空字符串")
                elif scope.strip().lower() not in {"global", "server", "database", "tablespace"}:
                    errors.append(f"{path}.args.scope 不支持: {scope}")
                if database is not None and (not isinstance(database, str) or not database.strip()):
                    errors.append(f"{path}.args.database 必须为非空字符串或省略")
                return

            errors.append(f"{path}.fn 未知函数: {fn_name}")
            return

        errors.append(f"{path} 必须包含 op 或 fn")

    _validate_node(root_expr, path="rule_expression.expr")
    return errors


@dataclass(slots=True)
class DslEvaluationOutcome:
    matched: bool
    errors: list[str]


class DslV4Evaluator:
    """Evaluate DSL v4 expression against permission facts."""

    def __init__(self, *, facts: Mapping[str, object] | None) -> None:
        self._facts = facts if isinstance(facts, Mapping) else {}
        self._errors: list[str] = []

    def evaluate(self, expression: object) -> DslEvaluationOutcome:
        if not is_dsl_v4_expression(expression):
            self._record_error(
                DSL_ERROR_INVALID_ARGS,
                reason="not_dsl_v4",
            )
            return DslEvaluationOutcome(matched=False, errors=list(self._errors))

        expr = expression.get("expr") if isinstance(expression, Mapping) else None
        matched = self._eval_node(expr)
        return DslEvaluationOutcome(matched=matched, errors=list(self._errors))

    # ------------------------------ Internals ------------------------------
    def _record_error(self, error_type: str, **context: object) -> None:
        self._errors.append(error_type)
        try:
            dsl_evaluation_errors.labels(error_type=error_type).inc()
        except ValueError:  # pragma: no cover - defensive: prometheus registry conflicts
            pass
        log_error(
            "dsl_v4_evaluation_error",
            module="account_classification",
            error_type=error_type,
            **context,
        )

    def _eval_node(self, node: object) -> bool:
        if not isinstance(node, Mapping):
            self._record_error(DSL_ERROR_INVALID_ARGS, reason="node_not_mapping")
            return False

        if "op" in node:
            return self._eval_op(node)
        if "fn" in node:
            return self._eval_fn(node)

        self._record_error(DSL_ERROR_INVALID_ARGS, reason="missing_op_or_fn")
        return False

    def _eval_op(self, node: Mapping[str, object]) -> bool:
        op_raw = node.get("op")
        if not isinstance(op_raw, str) or not op_raw.strip():
            self._record_error(DSL_ERROR_INVALID_ARGS, reason="op_not_string")
            return False
        op = op_raw.strip().upper()

        args = node.get("args", [])
        if not isinstance(args, list):
            self._record_error(DSL_ERROR_INVALID_ARGS, reason="args_not_list", op=op)
            return False

        if op == "NOT":
            if len(args) != 1:
                self._record_error(DSL_ERROR_INVALID_ARGS, reason="not_requires_single_arg")
                return False
            return not self._eval_node(args[0])

        if op == "AND":
            for item in args:
                if not self._eval_node(item):
                    return False
            return True

        if op == "OR":
            for item in args:
                if self._eval_node(item):
                    return True
            return False

        self._record_error(DSL_ERROR_INVALID_ARGS, reason="unknown_op", op=op)
        return False

    def _eval_fn(self, node: Mapping[str, object]) -> bool:
        fn_raw = node.get("fn")
        if not isinstance(fn_raw, str) or not fn_raw.strip():
            self._record_error(DSL_ERROR_INVALID_ARGS, reason="fn_not_string")
            return False
        fn = fn_raw.strip()

        raw_args = node.get("args", {})
        if raw_args is None:
            raw_args = {}
        if not isinstance(raw_args, Mapping):
            self._record_error(DSL_ERROR_INVALID_ARGS, reason="fn_args_not_mapping", fn=fn)
            return False
        args = dict(raw_args)

        started = time.perf_counter()
        try:
            if fn == "db_type_in":
                return self._fn_db_type_in(args)
            if fn == "is_superuser":
                return bool(self._facts.get("is_superuser", False))
            if fn == "has_capability":
                return self._fn_has_capability(args)
            if fn == "has_role":
                return self._fn_has_role(args)
            if fn == "has_privilege":
                return self._fn_has_privilege(args)
        finally:
            try:
                dsl_evaluation_duration.labels(function=fn).observe(time.perf_counter() - started)
            except ValueError:  # pragma: no cover - defensive: prometheus registry conflicts
                pass

        self._record_error(DSL_ERROR_UNKNOWN_FUNCTION, fn=fn)
        return False

    def _fn_db_type_in(self, args: dict[str, object]) -> bool:
        raw_types = args.get("types")
        if raw_types is None:
            self._record_error(DSL_ERROR_MISSING_ARGS, fn="db_type_in", missing="types")
            return False
        if not isinstance(raw_types, list):
            self._record_error(DSL_ERROR_INVALID_ARGS, fn="db_type_in", field="types")
            return False
        types = [item.strip().lower() for item in raw_types if isinstance(item, str) and item.strip()]
        if not types:
            self._record_error(DSL_ERROR_INVALID_ARGS, fn="db_type_in", field="types_empty")
            return False

        db_type_raw = self._facts.get("db_type")
        db_type = db_type_raw.strip().lower() if isinstance(db_type_raw, str) else ""
        return db_type in types

    def _fn_has_capability(self, args: dict[str, object]) -> bool:
        name = args.get("name")
        if not isinstance(name, str) or not name.strip():
            self._record_error(DSL_ERROR_MISSING_ARGS, fn="has_capability", missing="name")
            return False
        raw_capabilities = self._facts.get("capabilities")
        capabilities = self._ensure_str_list(raw_capabilities)
        return name in capabilities

    def _fn_has_role(self, args: dict[str, object]) -> bool:
        name = args.get("name")
        if not isinstance(name, str) or not name.strip():
            self._record_error(DSL_ERROR_MISSING_ARGS, fn="has_role", missing="name")
            return False
        raw_roles = self._facts.get("roles")
        roles = self._ensure_str_list(raw_roles)
        return name in roles

    def _fn_has_privilege(self, args: dict[str, object]) -> bool:
        name = args.get("name")
        scope_raw = args.get("scope")
        database = args.get("database")

        if not isinstance(name, str) or not name.strip():
            self._record_error(DSL_ERROR_MISSING_ARGS, fn="has_privilege", missing="name")
            return False
        if not isinstance(scope_raw, str) or not scope_raw.strip():
            self._record_error(DSL_ERROR_MISSING_ARGS, fn="has_privilege", missing="scope")
            return False
        if database is not None and (not isinstance(database, str) or not database.strip()):
            self._record_error(DSL_ERROR_INVALID_ARGS, fn="has_privilege", field="database")
            return False

        scope = scope_raw.strip().lower()
        privileges = self._facts.get("privileges")
        if not isinstance(privileges, Mapping):
            return False

        if scope == "global":
            return name in self._ensure_str_list(privileges.get("global"))

        if scope == "server":
            server_privs = self._ensure_str_list(privileges.get("server"))
            system_privs = self._ensure_str_list(privileges.get("system"))
            return name in {*(server_privs or []), *(system_privs or [])}

        if scope == "tablespace":
            return self._mapping_has_privilege(privileges.get("tablespace"), name, database=database)

        if scope == "database":
            if self._mapping_has_privilege(privileges.get("database"), name, database=database):
                return True
            if self._mapping_has_privilege(privileges.get("database_permissions"), name, database=database):
                return True
            return self._mapping_has_privilege(privileges.get("tablespace"), name, database=database)

        self._record_error(DSL_ERROR_INVALID_ARGS, fn="has_privilege", field="scope", scope=scope)
        return False

    @staticmethod
    def _ensure_str_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str) and item]

    def _mapping_has_privilege(self, value: object, name: str, *, database: str | None) -> bool:
        if not isinstance(value, Mapping):
            return False
        if database:
            bucket = value.get(database)
            return name in self._ensure_str_list(bucket)
        for bucket in value.values():
            if name in self._ensure_str_list(bucket):
                return True
        return False
