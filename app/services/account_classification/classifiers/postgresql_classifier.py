"""PostgreSQL rule classifier."""

from __future__ import annotations

from typing import Any

from app.utils.structlog_config import log_error

from .base import BaseRuleClassifier


class PostgreSQLRuleClassifier(BaseRuleClassifier):
    db_type = "postgresql"

    def evaluate(self, account, rule_expression: dict[str, Any]) -> bool:  # noqa: ANN001
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()
            match_results: list[bool] = []

            required_predefined_roles = rule_expression.get("predefined_roles", [])
            if required_predefined_roles:
                actual_predefined_roles = permissions.get("predefined_roles", [])
                predefined_roles_set = {
                    r["role"] if isinstance(r, dict) else r for r in (actual_predefined_roles or [])
                }
                match_results.append(all(role in predefined_roles_set for role in required_predefined_roles))

            required_role_attrs = rule_expression.get("role_attributes", [])
            if required_role_attrs:
                role_attrs = permissions.get("role_attributes", {})
                match_results.append(all(role_attrs.get(attr, False) for attr in required_role_attrs))

            required_database_perms = rule_expression.get("database_privileges", [])
            if required_database_perms:
                database_perms = permissions.get("database_privileges", {})
                database_match = False
                for db_perms in database_perms.values():
                    db_perm_names = self._extract_priv_names(db_perms)
                    if any(perm in db_perm_names for perm in required_database_perms):
                        database_match = True
                        break
                match_results.append(database_match)

            required_tablespace_perms = rule_expression.get("tablespace_privileges", [])
            if required_tablespace_perms:
                tablespace_perms = permissions.get("tablespace_privileges", {})
                ts_match = False
                for ts_perms in tablespace_perms.values():
                    ts_perm_names = self._extract_priv_names(ts_perms)
                    if any(perm in ts_perm_names for perm in required_tablespace_perms):
                        ts_match = True
                        break
                match_results.append(ts_match)

            return self._combine_results(match_results, operator)
        except Exception as exc:  # noqa: BLE001
            log_error("评估PostgreSQL规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _extract_priv_names(perms: Any) -> set[str]:
        names: set[str] = set()
        if isinstance(perms, list):
            for perm in perms:
                if isinstance(perm, str):
                    names.add(perm)
                elif isinstance(perm, dict) and perm.get("granted"):
                    names.add(perm.get("privilege"))
        elif isinstance(perms, dict):
            names = {
                perm["privilege"]
                for perm in perms.values()
                if isinstance(perm, dict) and perm.get("granted")
            }
        return names

    @staticmethod
    def _combine_results(results: list[bool], operator: str) -> bool:
        if not results:
            return True
        if operator == "AND":
            return all(results)
        return any(results)
