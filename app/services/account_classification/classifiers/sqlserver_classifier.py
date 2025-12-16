"""SQL Server 规则分类器.

实现 SQL Server 数据库的账户分类规则评估逻辑,支持服务器角色、数据库角色和权限的匹配.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.utils.structlog_config import log_error

from .base import CLASSIFIER_EVALUATION_EXCEPTIONS, BaseRuleClassifier

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.account_permission import AccountPermission
    from app.types import RuleExpression


class SQLServerRuleClassifier(BaseRuleClassifier):
    """SQL Server 规则分类器.

    实现 SQL Server 数据库的账户分类规则评估,支持以下规则类型:
    - server_roles: 服务器角色匹配
    - database_roles: 数据库角色匹配
    - server_permissions: 服务器权限匹配
    - database_permissions: 数据库权限匹配

    Attributes:
        db_type: 数据库类型标识符,固定为 'sqlserver'.

    Example:
        >>> classifier = SQLServerRuleClassifier()
        >>> rule = {'server_roles': ['sysadmin'], 'operator': 'OR'}
        >>> classifier.evaluate(account, rule)
        True

    """

    db_type = "sqlserver"

    def evaluate(self, account: AccountPermission, rule_expression: RuleExpression) -> bool:
        """评估账户是否满足 SQL Server 规则表达式.

        Args:
            account: 账户权限对象.
            rule_expression: 规则表达式字典,支持以下字段:
                - operator: 逻辑运算符('AND' 或 'OR'),默认为 'OR'
                - server_roles: 服务器角色列表
                - database_roles: 数据库角色列表
                - server_permissions: 服务器权限列表
                - database_permissions: 数据库权限列表

        Returns:
            如果账户满足规则返回 True,否则返回 False.

        Example:
            >>> rule = {
            ...     'database_roles': ['db_owner'],
            ...     'operator': 'AND'
            ... }
            >>> classifier.evaluate(account, rule)
            True

        """
        try:
            permissions = account.get_permissions_by_db_type() or {}
            operator = self._resolve_operator(rule_expression)
            match_results = [
                self._match_server_roles(permissions, rule_expression),
                self._match_database_roles(permissions, rule_expression),
                self._match_server_permissions(permissions, rule_expression, operator),
                self._match_database_permissions(permissions, rule_expression),
            ]
            return self._combine_results(match_results, operator)
        except CLASSIFIER_EVALUATION_EXCEPTIONS as exc:
            log_error("评估SQL Server规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _resolve_operator(rule_expression: RuleExpression) -> str:
        operator = str(rule_expression.get("operator", "OR")).upper()
        return operator if operator in {"AND", "OR"} else "OR"

    @staticmethod
    def _combine_results(results: list[bool], operator: str) -> bool:
        """根据逻辑运算符合并匹配结果.

        Args:
            results: 每个子条件的布尔结果.
            operator: 'AND' 或 'OR',决定组合策略.

        Returns:
            bool: 结果列表为空时返回 True,否则按运算符聚合.

        """
        if not results:
            return True
        if operator == "AND":
            return all(results)
        return any(results)

    def _match_server_roles(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
    ) -> bool:
        required_server_roles = self._ensure_str_sequence(rule_expression.get("server_roles"), dict_key="name")
        if not required_server_roles:
            return True
        actual_names = set(self._ensure_str_sequence(permissions.get("server_roles"), dict_key="name"))
        return all(role in actual_names for role in required_server_roles)

    def _match_database_roles(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
    ) -> bool:
        required_roles = self._ensure_str_sequence(rule_expression.get("database_roles"), dict_key="name")
        if not required_roles:
            return True
        database_roles = permissions.get("database_roles", {})
        if not isinstance(database_roles, dict):
            return False
        for roles in database_roles.values():
            role_names = set(self._ensure_str_sequence(roles, dict_key="name"))
            if any(role in role_names for role in required_roles):
                return True
        return False

    def _match_server_permissions(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        required_perms = self._ensure_str_sequence(rule_expression.get("server_permissions"), dict_key="permission")
        if not required_perms:
            return True
        actual_names = set(self._ensure_str_sequence(permissions.get("server_permissions"), dict_key="permission"))
        if operator == "AND":
            return all(perm in actual_names for perm in required_perms)
        return any(perm in actual_names for perm in required_perms)

    def _match_database_permissions(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
    ) -> bool:
        required_perms = self._ensure_str_sequence(rule_expression.get("database_permissions"), dict_key="permission")
        if not required_perms:
            return True
        database_permissions = permissions.get("database_permissions", {})
        if not isinstance(database_permissions, dict):
            return False
        for perms in database_permissions.values():
            db_perm_names = set(self._ensure_str_sequence(perms, dict_key="permission"))
            if any(perm in db_perm_names for perm in required_perms):
                return True
        return False

    @staticmethod
    def _ensure_str_sequence(value: object, *, dict_key: str | None = None) -> list[str]:
        """将任意输入规范化为字符串列表."""
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            normalized: list[str] = []
            for item in value:
                if isinstance(item, (str, int, float, bool)):
                    normalized.append(str(item))
                elif dict_key and isinstance(item, dict):
                    dict_value = item.get(dict_key)
                    if isinstance(dict_value, (str, int, float, bool)):
                        normalized.append(str(dict_value))
            return normalized
        if isinstance(value, dict) and dict_key:
            dict_value = value.get(dict_key)
            if isinstance(dict_value, (str, int, float, bool)):
                return [str(dict_value)]
            return []
        if isinstance(value, (str, int, float, bool)):
            return [str(value)]
        return []
