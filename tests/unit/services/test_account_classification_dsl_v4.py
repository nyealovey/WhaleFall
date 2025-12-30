import pytest

from app.services.account_classification.dsl_v4 import (
    DSL_ERROR_MISSING_ARGS,
    DSL_ERROR_UNKNOWN_FUNCTION,
    DslV4Evaluator,
    collect_dsl_v4_validation_errors,
)


@pytest.mark.unit
def test_dsl_v4_validation_accepts_minimal_expression() -> None:
    expression = {
        "version": 4,
        "expr": {
            "op": "AND",
            "args": [
                {"fn": "has_role", "args": {"name": "admin"}},
                {"fn": "has_privilege", "args": {"name": "SELECT", "scope": "global"}},
            ],
        },
    }
    assert collect_dsl_v4_validation_errors(expression) == []


@pytest.mark.unit
def test_dsl_v4_evaluator_short_circuits_or() -> None:
    expression = {
        "version": 4,
        "expr": {
            "op": "OR",
            "args": [
                {"fn": "has_role", "args": {"name": "admin"}},
                {"fn": "unknown_fn", "args": {}},
            ],
        },
    }
    facts = {"roles": ["admin"]}
    outcome = DslV4Evaluator(facts=facts).evaluate(expression)
    assert outcome.matched is True
    assert DSL_ERROR_UNKNOWN_FUNCTION not in outcome.errors


@pytest.mark.unit
def test_dsl_v4_evaluator_short_circuits_and() -> None:
    expression = {
        "version": 4,
        "expr": {
            "op": "AND",
            "args": [
                {"fn": "has_role", "args": {"name": "missing"}},
                {"fn": "unknown_fn", "args": {}},
            ],
        },
    }
    facts = {"roles": ["admin"]}
    outcome = DslV4Evaluator(facts=facts).evaluate(expression)
    assert outcome.matched is False
    assert DSL_ERROR_UNKNOWN_FUNCTION not in outcome.errors


@pytest.mark.unit
def test_dsl_v4_evaluator_reports_missing_args() -> None:
    expression = {
        "version": 4,
        "expr": {
            "op": "AND",
            "args": [
                {"fn": "has_role", "args": {}},
            ],
        },
    }
    outcome = DslV4Evaluator(facts={"roles": ["admin"]}).evaluate(expression)
    assert outcome.matched is False
    assert DSL_ERROR_MISSING_ARGS in outcome.errors


@pytest.mark.unit
def test_dsl_v4_has_privilege_supports_scopes() -> None:
    expression = {
        "version": 4,
        "expr": {
            "op": "AND",
            "args": [
                {"fn": "has_privilege", "args": {"name": "SELECT", "scope": "global"}},
                {"fn": "has_privilege", "args": {"name": "CONTROL SERVER", "scope": "server"}},
                {"fn": "has_privilege", "args": {"name": "CREATE", "scope": "database"}},
                {"fn": "has_privilege", "args": {"name": "UNLIMITED TABLESPACE", "scope": "tablespace"}},
            ],
        },
    }
    facts = {
        "privileges": {
            "global": ["SELECT"],
            "server": ["CONTROL SERVER"],
            "system": [],
            "database": {"db1": ["CREATE"]},
            "tablespace": {"ts1": ["UNLIMITED TABLESPACE"]},
        },
    }
    assert DslV4Evaluator(facts=facts).evaluate(expression).matched is True
