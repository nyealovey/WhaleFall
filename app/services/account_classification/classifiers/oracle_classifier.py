"""Oracle 规则分类器。

实现 Oracle 数据库的账户分类规则评估逻辑，支持角色、系统权限和对象权限的匹配。
"""

from __future__ import annotations

from typing import Any

from app.utils.structlog_config import log_error

from .base import BaseRuleClassifier


class OracleRuleClassifier(BaseRuleClassifier):
    """Oracle 规则分类器。

    实现 Oracle 数据库的账户分类规则评估，支持以下规则类型：
    - roles: 角色匹配
    - system_privileges: 系统权限匹配
    - object_privileges: 对象权限匹配

    Attributes:
        db_type: 数据库类型标识符，固定为 'oracle'。

    Example:
        >>> classifier = OracleRuleClassifier()
        >>> rule = {'roles': ['DBA'], 'operator': 'OR'}
        >>> classifier.evaluate(account, rule)
        True
    """

    db_type = "oracle"

    def evaluate(self, account, rule_expression: dict[str, Any]) -> bool:  # noqa: ANN001
        """评估账户是否满足 Oracle 规则表达式。

        Args:
            account: 账户权限对象。
            rule_expression: 规则表达式字典，支持以下字段：
                - operator: 逻辑运算符（'AND' 或 'OR'），默认为 'OR'
                - roles: 角色列表
                - system_privileges: 系统权限列表
                - object_privileges: 对象权限列表

        Returns:
            如果账户满足规则返回 True，否则返回 False。

        Example:
            >>> rule = {
            ...     'system_privileges': ['CREATE SESSION', 'CREATE TABLE'],
            ...     'operator': 'AND'
            ... }
            >>> classifier.evaluate(account, rule)
            True
        """
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()
            match_results: list[bool] = []

            required_roles = rule_expression.get("roles", [])
            if required_roles:
                actual_roles = (
                    permissions.get("oracle_roles")
                    or permissions.get("roles")
                    or []
                )
                role_names = {
                    role.get("role") if isinstance(role, dict) else role for role in (actual_roles or [])
                }
                match_results.append(all(role in role_names for role in required_roles))

            required_system_privs = rule_expression.get("system_privileges", [])
            if required_system_privs:
                system_privileges = (
                    permissions.get("system_privileges")
                    or permissions.get("oracle_system_privileges")
                    or []
                )
                system_priv_names = {
                    priv.get("privilege") if isinstance(priv, dict) else priv for priv in (system_privileges or [])
                }
                match_results.append(
                    all(priv in system_priv_names for priv in required_system_privs)
                    if operator == "AND"
                    else any(priv in system_priv_names for priv in required_system_privs)
                )

            required_object_privs = rule_expression.get("object_privileges", [])
            if required_object_privs:
                object_privileges = permissions.get("object_privileges", [])
                object_match = False
                for privilege in object_privileges or []:
                    priv_name = privilege.get("privilege") if isinstance(privilege, dict) else privilege
                    object_name = privilege.get("object_name") if isinstance(privilege, dict) else None
                    for requirement in required_object_privs:
                        required_priv = requirement.get("privilege")
                        required_object = requirement.get("object_name")
                        priv_ok = required_priv in (priv_name, "*")
                        obj_ok = required_object in (object_name, "*")
                        if priv_ok and obj_ok:
                            object_match = True
                            break
                    if object_match and operator == "OR":
                        break
                match_results.append(object_match)

            required_tablespace = rule_expression.get("tablespace_privileges", [])
            if required_tablespace:
                tablespace_privileges = self._normalize_tablespace_privileges(
                    permissions.get("tablespace_privileges_oracle")
                    or permissions.get("tablespace_privileges")
                    or {}
                )
                tablespace_match = False
                for privilege in tablespace_privileges:
                    priv_name = privilege.get("privilege") if isinstance(privilege, dict) else privilege
                    tablespace_name = privilege.get("tablespace_name") if isinstance(privilege, dict) else None
                    for requirement in required_tablespace:
                        required_priv = requirement.get("privilege")
                        required_tablespace_name = requirement.get("tablespace_name")
                        priv_ok = required_priv in (priv_name, "*")
                        ts_ok = required_tablespace_name in (tablespace_name, "*")
                        if priv_ok and ts_ok:
                            tablespace_match = True
                            break
                    if tablespace_match and operator == "OR":
                        break
                match_results.append(tablespace_match)

            return self._combine_results(match_results, operator)
        except Exception as exc:  # noqa: BLE001
            log_error("评估Oracle规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _combine_results(results: list[bool], operator: str) -> bool:
        if not results:
            return True
        if operator == "AND":
            return all(results)
        return any(results)

    @staticmethod
    def _normalize_tablespace_privileges(source: Any) -> list[dict[str, Any]]:
        """支持 dict/list 两种结构的表空间权限。"""
        normalized: list[dict[str, Any]] = []
        if isinstance(source, dict):
            for tablespace_name, privileges in source.items():
                perms = privileges if isinstance(privileges, list) else [privileges]
                for privilege in perms:
                    normalized.append(
                        {
                            "tablespace_name": tablespace_name,
                            "privilege": privilege,
                        }
                    )
        elif isinstance(source, list):
            normalized = [item for item in source if isinstance(item, dict)]
        return normalized
