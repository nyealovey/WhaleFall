"""MySQL rule classifier."""

from __future__ import annotations

from typing import Any

from app.utils.structlog_config import log_error

from .base import BaseRuleClassifier


class MySQLRuleClassifier(BaseRuleClassifier):
    db_type = "mysql"

    def evaluate(self, account, rule_expression: dict[str, Any]) -> bool:  # noqa: ANN001
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()

            required_global = rule_expression.get("global_privileges", [])
            if required_global:
                actual_global = permissions.get("global_privileges", [])
                actual_global_set: set[str] = set()
                if actual_global:
                    if isinstance(actual_global, list):
                        for perm in actual_global:
                            if isinstance(perm, str):
                                actual_global_set.add(perm)
                            elif isinstance(perm, dict) and perm.get("granted"):
                                actual_global_set.add(perm.get("privilege"))
                    else:
                        actual_global_set = {
                            p["privilege"]
                            for p in actual_global
                            if isinstance(p, dict) and p.get("granted")
                        }
                if operator == "AND":
                    if not all(perm in actual_global_set for perm in required_global):
                        return False
                elif not any(perm in actual_global_set for perm in required_global):
                    return False

            exclude_global = rule_expression.get("exclude_privileges", [])
            if exclude_global:
                actual_global = permissions.get("global_privileges", [])
                actual_global_set = set(actual_global or [])
                if any(perm in actual_global_set for perm in exclude_global):
                    return False

            required_databases = rule_expression.get("database_privileges", [])
            if required_databases:
                database_privileges = permissions.get("database_privileges", {})
                database_match = False
                for db_name, db_perms in database_privileges.items():
                    for requirement in required_databases:
                        requirement_dict = self._normalize_db_requirement(requirement)
                        if not requirement_dict:
                            continue
                        requirement_db = requirement_dict.get("database", "*")
                        if requirement_db not in ("*", db_name):
                            continue
                        perms = self._ensure_list(requirement_dict.get("privileges", []))
                        db_perm_names = self._extract_perm_names(db_perms)
                        if operator == "AND":
                            if all(perm in db_perm_names for perm in perms):
                                database_match = True
                            else:
                                database_match = False
                                break
                        elif any(perm in db_perm_names for perm in perms):
                            database_match = True
                    if not database_match and operator == "AND":
                        break
                if not database_match:
                    return False

            required_tables = rule_expression.get("table_privileges", [])
            if required_tables:
                table_privileges = permissions.get("table_privileges", {})
                table_match = False
                for db_name, tables in table_privileges.items():
                    for table_name, table_perms in tables.items():
                        for requirement in required_tables:
                            requirement_dict = self._normalize_table_requirement(requirement)
                            if not requirement_dict:
                                continue
                            requirement_db = requirement_dict.get("database", "*")
                            requirement_table = requirement_dict.get("table", "*")
                            if requirement_db not in ("*", db_name):
                                continue
                            if requirement_table not in ("*", table_name):
                                continue
                            perms = self._ensure_list(requirement_dict.get("privileges", []))
                            table_perm_names = self._extract_perm_names(table_perms)
                            if operator == "AND":
                                if all(perm in table_perm_names for perm in perms):
                                    table_match = True
                                else:
                                    table_match = False
                                    break
                            elif any(perm in table_perm_names for perm in perms):
                                table_match = True
                        if not table_match and operator == "AND":
                            break
                    if not table_match and operator == "AND":
                        break
                if not table_match:
                    return False

            required_roles = rule_expression.get("roles", [])
            if required_roles:
                actual_roles = permissions.get("roles", [])
                actual_roles_set = {role.get("role") if isinstance(role, dict) else role for role in actual_roles}
                if operator == "AND":
                    if not all(role in actual_roles_set for role in required_roles):
                        return False
                elif not any(role in actual_roles_set for role in required_roles):
                    return False

            return True
        except Exception as exc:  # noqa: BLE001
            log_error("评估MySQL规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _extract_perm_names(perms: Any) -> set[str]:
        perm_names: set[str] = set()
        if isinstance(perms, list):
            for perm in perms:
                if isinstance(perm, str):
                    perm_names.add(perm)
                elif isinstance(perm, dict) and perm.get("granted"):
                    perm_names.add(perm.get("privilege"))
        elif isinstance(perms, dict):
            for perm_name, granted in perms.items():
                if granted:
                    perm_names.add(perm_name)
        return perm_names

    @staticmethod
    def _normalize_db_requirement(requirement: Any) -> dict[str, Any] | None:
        if isinstance(requirement, dict):
            return requirement
        if isinstance(requirement, str):
            return {"database": "*", "privileges": [requirement]}
        return None

    @staticmethod
    def _normalize_table_requirement(requirement: Any) -> dict[str, Any] | None:
        if isinstance(requirement, dict):
            return requirement
        if isinstance(requirement, str):
            return {"database": "*", "table": "*", "privileges": [requirement]}
        return None

    @staticmethod
    def _ensure_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
