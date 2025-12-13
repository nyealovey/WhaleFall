"""PostgreSQL 规则分类器.

实现 PostgreSQL 数据库的账户分类规则评估逻辑,支持预定义角色、角色属性、数据库权限和模式权限的匹配.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.utils.structlog_config import log_error

from .base import CLASSIFIER_EVALUATION_EXCEPTIONS, BaseRuleClassifier

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.account_permission import AccountPermission
    from app.types import RuleExpression


class PostgreSQLRuleClassifier(BaseRuleClassifier):
    """PostgreSQL 规则分类器.

    实现 PostgreSQL 数据库的账户分类规则评估,支持以下规则类型:
    - predefined_roles: 预定义角色匹配
    - role_attributes: 角色属性匹配(如 SUPERUSER、CREATEDB 等)
    - database_privileges: 数据库级权限匹配
    - schema_privileges: 模式级权限匹配

    Attributes:
        db_type: 数据库类型标识符,固定为 'postgresql'.

    Example:
        >>> classifier = PostgreSQLRuleClassifier()
        >>> rule = {'predefined_roles': ['pg_read_all_data'], 'operator': 'OR'}
        >>> classifier.evaluate(account, rule)
        True

    """

    db_type = "postgresql"

    def evaluate(self, account: AccountPermission, rule_expression: RuleExpression) -> bool:
        """评估账户是否满足 PostgreSQL 规则表达式.

        Args:
            account: 账户权限对象.
            rule_expression: 规则表达式字典,支持以下字段:
                - operator: 逻辑运算符('AND' 或 'OR'),默认为 'OR'
                - predefined_roles: 预定义角色列表
                - role_attributes: 角色属性列表
                - database_privileges: 数据库权限列表
                - schema_privileges: 模式权限列表

        Returns:
            如果账户满足规则返回 True,否则返回 False.

        Example:
            >>> rule = {
            ...     'role_attributes': ['SUPERUSER'],
            ...     'operator': 'AND'
            ... }
            >>> classifier.evaluate(account, rule)
            False

        """
        try:
            permissions = account.get_permissions_by_db_type() or {}
            operator = self._resolve_operator(rule_expression)
            match_results = [
                self._match_predefined_roles(permissions, rule_expression),
                self._match_role_attributes(permissions, rule_expression),
                self._match_privileges(
                    permissions.get("database_privileges", {}),
                    rule_expression.get("database_privileges"),
                ),
                self._match_privileges(
                    permissions.get("tablespace_privileges", {}),
                    rule_expression.get("tablespace_privileges"),
                ),
            ]
            return self._combine_results(match_results, operator)
        except CLASSIFIER_EVALUATION_EXCEPTIONS as exc:
            log_error("评估PostgreSQL规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _resolve_operator(rule_expression: RuleExpression) -> str:
        operator = str(rule_expression.get("operator", "OR")).upper()
        return operator if operator in {"AND", "OR"} else "OR"

    @staticmethod
    def _extract_priv_names(perms: object) -> set[str]:
        """提取权限名称集合.

        Args:
            perms: 可能为 list/dict 的权限结构.

        Returns:
            set[str]: 去重后的权限名称集合,仅包含已授权的权限.

        """
        names: set[str] = set()
        if isinstance(perms, list):
            for perm in perms:
                if isinstance(perm, str):
                    names.add(perm)
                elif isinstance(perm, dict) and perm.get("granted"):
                    names.add(perm.get("privilege"))
        elif isinstance(perms, dict):
            names = {perm["privilege"] for perm in perms.values() if isinstance(perm, dict) and perm.get("granted")}
        return names

    @staticmethod
    def _combine_results(results: list[bool], operator: str) -> bool:
        """根据 operator 聚合布尔结果.

        Args:
            results: 子条件布尔结果列表.
            operator: 'AND' 或 'OR'.

        Returns:
            bool: results 为空时返回 True,否则按运算符聚合.

        """
        if not results:
            return True
        if operator == "AND":
            return all(results)
        return any(results)

    def _match_predefined_roles(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
    ) -> bool:
        required_predefined_roles = cast("Sequence[str] | None", rule_expression.get("predefined_roles")) or []
        if not required_predefined_roles:
            return True
        actual_predefined_roles = permissions.get("predefined_roles", [])
        predefined_roles_set = {
            role.get("role") if isinstance(role, dict) else role for role in (actual_predefined_roles or [])
        }
        return all(role in predefined_roles_set for role in required_predefined_roles)

    def _match_role_attributes(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
    ) -> bool:
        required_role_attrs = cast("Sequence[str] | None", rule_expression.get("role_attributes")) or []
        if not required_role_attrs:
            return True
        role_attrs = permissions.get("role_attributes", {})
        return all(role_attrs.get(attr, False) for attr in required_role_attrs)

    def _match_privileges(
        self,
        privilege_map: object,
        required_privileges: object,
    ) -> bool:
        required = cast("Sequence[str] | None", required_privileges) or []
        if not required:
            return True
        if not isinstance(privilege_map, dict):
            return False
        for db_perms in privilege_map.values():
            if any(perm in self._extract_priv_names(db_perms) for perm in required):
                return True
        return False
