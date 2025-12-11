"""SQL Server 规则分类器.

实现 SQL Server 数据库的账户分类规则评估逻辑,支持服务器角色、数据库角色和权限的匹配.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from app.utils.structlog_config import log_error

from .base import CLASSIFIER_EVALUATION_EXCEPTIONS, BaseRuleClassifier

if TYPE_CHECKING:
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
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()
            match_results: list[bool] = []

            required_server_roles = cast("Sequence[str] | None", rule_expression.get("server_roles")) or []
            if required_server_roles:
                actual_server_roles = permissions.get("server_roles", [])
                actual_server_role_names = {
                    role.get("name") if isinstance(role, dict) else role for role in actual_server_roles
                }
                match_results.append(all(role in actual_server_role_names for role in required_server_roles))

            required_database_roles = cast("Sequence[str] | None", rule_expression.get("database_roles")) or []
            if required_database_roles:
                database_roles = permissions.get("database_roles", {})
                role_match = False
                for roles in database_roles.values():
                    role_names = {role.get("name") if isinstance(role, dict) else role for role in roles}
                    if any(role in role_names for role in required_database_roles):
                        role_match = True
                        break
                match_results.append(role_match)

            required_server_perms = cast("Sequence[str] | None", rule_expression.get("server_permissions")) or []
            if required_server_perms:
                actual_server_perms = permissions.get("server_permissions", [])
                actual_perm_names = {
                    perm.get("permission") if isinstance(perm, dict) else perm for perm in actual_server_perms
                }
                match_results.append(
                    (
                        all(perm in actual_perm_names for perm in required_server_perms)
                        if operator == "AND"
                        else any(perm in actual_perm_names for perm in required_server_perms)
                    ),
                )

            required_database_perms = cast("Sequence[str] | None", rule_expression.get("database_permissions")) or []
            if required_database_perms:
                database_permissions = permissions.get("database_permissions", {})
                database_perms_match = False
                for perms in database_permissions.values():
                    db_perm_names = {
                        perm.get("permission") if isinstance(perm, dict) else perm for perm in (perms or [])
                    }
                    if any(perm in db_perm_names for perm in required_database_perms):
                        database_perms_match = True
                        break
                match_results.append(database_perms_match)

            return self._combine_results(match_results, operator)
        except CLASSIFIER_EVALUATION_EXCEPTIONS as exc:
            log_error("评估SQL Server规则失败", module="account_classification", error=str(exc))
            return False

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
