import pytest

from app.services.account_classification.classifiers.oracle_classifier import OracleRuleClassifier
from app.services.account_classification.classifiers.postgresql_classifier import PostgreSQLRuleClassifier
from app.services.account_classification.classifiers.sqlserver_classifier import SQLServerRuleClassifier


class StubAccount:
    def __init__(self, permissions: dict[str, object]) -> None:
        self._permissions = permissions

    def get_permissions_by_db_type(self) -> dict[str, object]:
        return self._permissions


@pytest.mark.unit
def test_sqlserver_or_operator_does_not_match_all_accounts() -> None:
    classifier = SQLServerRuleClassifier()
    account = StubAccount(
        {
            "server_roles": [],
            "server_permissions": [],
            "database_roles": {},
            "database_permissions": {},
        },
    )
    rule_expression = {"operator": "OR", "server_permissions": ["CONTROL SERVER"]}
    assert classifier.evaluate(account, rule_expression) is False


@pytest.mark.unit
def test_sqlserver_or_operator_matches_when_permission_hit() -> None:
    classifier = SQLServerRuleClassifier()
    account = StubAccount(
        {
            "server_roles": [],
            "server_permissions": [{"permission": "CONTROL SERVER"}],
            "database_roles": {},
            "database_permissions": {},
        },
    )
    rule_expression = {"operator": "OR", "server_permissions": ["CONTROL SERVER"]}
    assert classifier.evaluate(account, rule_expression) is True


@pytest.mark.unit
def test_sqlserver_supports_legacy_database_privileges_key() -> None:
    classifier = SQLServerRuleClassifier()
    account = StubAccount(
        {
            "server_roles": [],
            "server_permissions": [],
            "database_roles": {},
            "database_permissions": {
                "testdb": [{"permission": "DELETE"}],
            },
        },
    )
    rule_expression = {"operator": "OR", "database_privileges": ["DELETE"]}
    assert classifier.evaluate(account, rule_expression) is True


@pytest.mark.unit
def test_postgresql_or_operator_respects_selected_conditions() -> None:
    classifier = PostgreSQLRuleClassifier()
    account = StubAccount(
        {
            "predefined_roles": [],
            "role_attributes": {},
            "database_privileges": {
                "db1": ["CREATE"],
            },
            "tablespace_privileges": {},
        },
    )
    rule_expression = {"operator": "OR", "database_privileges": ["DROP"]}
    assert classifier.evaluate(account, rule_expression) is False


@pytest.mark.unit
def test_oracle_supports_simple_role_matching() -> None:
    classifier = OracleRuleClassifier()
    account = StubAccount(
        {
            "oracle_roles": ["DBA"],
            "oracle_system_privileges": [],
            "oracle_tablespace_privileges": {},
            "type_specific": {},
        },
    )
    rule_expression = {"operator": "OR", "roles": ["DBA"]}
    assert classifier.evaluate(account, rule_expression) is True


@pytest.mark.unit
def test_oracle_tablespace_privileges_accept_string_list() -> None:
    classifier = OracleRuleClassifier()
    account = StubAccount(
        {
            "oracle_roles": [],
            "oracle_system_privileges": [],
            "oracle_tablespace_privileges": {
                "USERS": ["UNLIMITED TABLESPACE"],
            },
            "type_specific": {},
        },
    )
    rule_expression = {"operator": "OR", "tablespace_privileges": ["UNLIMITED TABLESPACE"]}
    assert classifier.evaluate(account, rule_expression) is True

