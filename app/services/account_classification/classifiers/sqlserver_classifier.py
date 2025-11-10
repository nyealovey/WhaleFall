"""SQL Server rule classifier."""

from __future__ import annotations

from typing import Any

from app.utils.structlog_config import log_error

from .base import BaseRuleClassifier


class SQLServerRuleClassifier(BaseRuleClassifier):
    db_type = "sqlserver"

    def evaluate(self, account, rule_expression: dict[str, Any]) -> bool:  # noqa: ANN001
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()
            match_results: list[bool] = []

            required_server_roles = rule_expression.get("server_roles", [])
            if required_server_roles:
                actual_server_roles = permissions.get("server_roles", [])
                actual_server_role_names = {
                    role.get("name") if isinstance(role, dict) else role for role in actual_server_roles
                }
                match_results.append(all(role in actual_server_role_names for role in required_server_roles))

            required_database_roles = rule_expression.get("database_roles", [])
            if required_database_roles:
                database_roles = permissions.get("database_roles", {})
                role_match = False
                for roles in database_roles.values():
                    role_names = {role.get("name") if isinstance(role, dict) else role for role in roles}
                    if any(role in role_names for role in required_database_roles):
                        role_match = True
                        break
                match_results.append(role_match)

            required_server_perms = rule_expression.get("server_permissions", [])
            if required_server_perms:
                actual_server_perms = permissions.get("server_permissions", [])
                actual_perm_names = {
                    perm.get("permission") if isinstance(perm, dict) else perm for perm in actual_server_perms
                }
                match_results.append(
                    all(perm in actual_perm_names for perm in required_server_perms)
                    if operator == "AND"
                    else any(perm in actual_perm_names for perm in required_server_perms)
                )

            required_database_perms = rule_expression.get("database_permissions", [])
            if required_database_perms:
                database_permissions = permissions.get("database_permissions", {})
                database_perms_match = False
                for perms in database_permissions.values():
                    db_perm_names = {
                        perm.get("permission") if isinstance(perm, dict) else perm
                        for perm in (perms or [])
                    }
                    if any(perm in db_perm_names for perm in required_database_perms):
                        database_perms_match = True
                        break
                match_results.append(database_perms_match)

            return self._combine_results(match_results, operator)
        except Exception as exc:  # noqa: BLE001
            log_error("评估SQL Server规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _combine_results(results: list[bool], operator: str) -> bool:
        if not results:
            return True
        if operator == "AND":
            return all(results)
        return any(results)
