"""MySQL 规则分类器.

实现 MySQL 数据库的账户分类规则评估逻辑,支持全局权限、数据库权限、表权限和角色的匹配.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.utils.structlog_config import log_error

from .base import CLASSIFIER_EVALUATION_EXCEPTIONS, BaseRuleClassifier

if TYPE_CHECKING:
    from app.models.account_permission import AccountPermission
    from app.types import RuleExpression


class MySQLRuleClassifier(BaseRuleClassifier):
    """MySQL 规则分类器.

    实现 MySQL 数据库的账户分类规则评估,支持以下规则类型:
    - global_privileges: 全局权限匹配
    - exclude_privileges: 排除权限匹配
    - database_privileges: 数据库级权限匹配
    - table_privileges: 表级权限匹配
    - roles: 角色匹配

    Attributes:
        db_type: 数据库类型标识符,固定为 'mysql'.

    Example:
        >>> classifier = MySQLRuleClassifier()
        >>> rule = {'global_privileges': ['SELECT', 'INSERT'], 'operator': 'AND'}
        >>> classifier.evaluate(account, rule)
        True

    """

    db_type = "mysql"

    def evaluate(self, account: AccountPermission, rule_expression: RuleExpression) -> bool:
        """评估账户是否满足 MySQL 规则表达式.

        Args:
            account: 账户权限对象.
            rule_expression: 规则表达式字典,支持以下字段:
                - operator: 逻辑运算符('AND' 或 'OR'),默认为 'OR'
                - global_privileges: 全局权限列表
                - exclude_privileges: 排除权限列表
                - database_privileges: 数据库权限列表
                - table_privileges: 表权限列表
                - roles: 角色列表

        Returns:
            如果账户满足规则返回 True,否则返回 False.

        Example:
            >>> rule = {
            ...     'global_privileges': ['SELECT', 'INSERT'],
            ...     'operator': 'AND'
            ... }
            >>> classifier.evaluate(account, rule)
            True

        """
        try:
            permissions = account.get_permissions_by_db_type() or {}
            operator = self._resolve_operator(rule_expression)
            if not permissions:
                return False

            checks: list[bool] = [
                self._match_global_privileges(permissions, rule_expression, operator),
                not self._has_excluded_privileges(permissions, rule_expression),
                self._match_database_privileges(permissions, rule_expression, operator),
                self._match_table_privileges(permissions, rule_expression, operator),
                self._match_roles(permissions, rule_expression, operator),
            ]
            return all(checks)
        except CLASSIFIER_EVALUATION_EXCEPTIONS as exc:
            log_error("评估MySQL规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _resolve_operator(rule_expression: RuleExpression) -> str:
        """解析规则组合运算符."""
        operator = str(rule_expression.get("operator", "OR")).upper()
        if operator not in {"AND", "OR"}:
            return "OR"
        return operator

    def _match_global_privileges(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        """校验全局权限要求."""
        required_global = self._ensure_list(rule_expression.get("global_privileges", []))
        if not required_global:
            return True
        actual_global_set = self._extract_perm_names(permissions.get("global_privileges"))
        if operator == "AND":
            return all(perm in actual_global_set for perm in required_global)
        return any(perm in actual_global_set for perm in required_global)

    def _has_excluded_privileges(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
    ) -> bool:
        """判断是否命中排除的全局权限."""
        exclude_global = self._ensure_list(rule_expression.get("exclude_privileges", []))
        if not exclude_global:
            return False
        actual_global = self._extract_perm_names(permissions.get("global_privileges"))
        return any(perm in actual_global for perm in exclude_global)

    def _match_database_privileges(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        """校验数据库级权限."""
        raw_required = rule_expression.get("database_privileges")
        required_databases = raw_required if isinstance(raw_required, list) else []
        normalized = [self._normalize_db_requirement(item) for item in required_databases]
        normalized = [item for item in normalized if item]
        if not normalized:
            return True

        database_privileges = permissions.get("database_privileges", {})
        if not isinstance(database_privileges, dict):
            return False

        def requirement_met(requirement: dict[str, object]) -> bool:
            target_db = requirement.get("database", "*")
            perms = self._ensure_list(requirement.get("privileges", []))
            for db_name, db_perms in database_privileges.items():
                if target_db not in ("*", db_name):
                    continue
                if all(perm in self._extract_perm_names(db_perms) for perm in perms):
                    return True
            return False

        if operator == "AND":
            return all(requirement_met(req) for req in normalized)
        return any(requirement_met(req) for req in normalized)

    def _match_table_privileges(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        """校验表级权限."""
        raw_required = rule_expression.get("table_privileges")
        required_tables = raw_required if isinstance(raw_required, list) else []
        normalized = [self._normalize_table_requirement(item) for item in required_tables]
        normalized = [item for item in normalized if item]
        if not normalized:
            return True

        table_privileges = permissions.get("table_privileges", {})
        if not isinstance(table_privileges, dict):
            return False

        if operator == "AND":
            return all(
                self._table_requirement_met(table_privileges, requirement)
                for requirement in normalized
            )
        return any(self._table_requirement_met(table_privileges, requirement) for requirement in normalized)

    def _table_requirement_met(
        self,
        table_privileges: object,
        requirement: dict[str, object],
    ) -> bool:
        """判断单个表权限要求是否满足."""
        if not isinstance(table_privileges, dict):
            return False
        target_db = requirement.get("database", "*")
        target_table = requirement.get("table", "*")
        perms = self._ensure_list(requirement.get("privileges", []))
        for db_name, tables in table_privileges.items():
            if target_db not in ("*", db_name):
                continue
            if not isinstance(tables, dict):
                continue
            for table_name, table_perms in tables.items():
                if target_table not in ("*", table_name):
                    continue
                if all(perm in self._extract_perm_names(table_perms) for perm in perms):
                    return True
        return False

    def _match_roles(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        """校验角色要求."""
        required_roles = self._ensure_list(rule_expression.get("roles", []))
        if not required_roles:
            return True
        actual_roles = permissions.get("roles", [])
        actual_roles_set = set(self._ensure_list(actual_roles, dict_key="role"))
        if operator == "AND":
            return all(role in actual_roles_set for role in required_roles)
        return any(role in actual_roles_set for role in required_roles)

    @staticmethod
    def _extract_perm_names(perms: object) -> set[str]:
        """从权限数据中提取权限名称集合.

        Args:
            perms: 权限数据,可以是列表、字典或其他格式.

        Returns:
            权限名称集合.

        """
        perm_names: set[str] = set()
        if isinstance(perms, list):
            for perm in perms:
                if isinstance(perm, str):
                    perm_names.add(perm)
                elif isinstance(perm, dict):
                    privilege = perm.get("privilege")
                    if perm.get("granted") and isinstance(privilege, str):
                        perm_names.add(privilege)
        elif isinstance(perms, dict):
            for perm_name, granted in perms.items():
                if isinstance(perm_name, str) and granted:
                    perm_names.add(perm_name)
        return perm_names

    @staticmethod
    def _normalize_db_requirement(requirement: object) -> dict[str, object] | None:
        """规范化数据库权限要求.

        Args:
            requirement: 权限要求,可以是字典或字符串.

        Returns:
            规范化后的权限要求字典,如果无法规范化则返回 None.

        """
        if isinstance(requirement, dict):
            return requirement
        if isinstance(requirement, str):
            return {"database": "*", "privileges": [requirement]}
        return None

    @staticmethod
    def _normalize_table_requirement(requirement: object) -> dict[str, object] | None:
        """规范化表权限要求.

        Args:
            requirement: 权限要求,可以是字典或字符串.

        Returns:
            规范化后的权限要求字典,如果无法规范化则返回 None.

        """
        if isinstance(requirement, dict):
            return requirement
        if isinstance(requirement, str):
            return {"database": "*", "table": "*", "privileges": [requirement]}
        return None

    @staticmethod
    def _ensure_list(value: object, *, dict_key: str | None = None) -> list[str]:
        """确保值为列表格式.

        Args:
            value: 待转换的值.

        Returns:
            列表格式的值.

        """
        if value is None:
            return []
        if isinstance(value, list):
            result: list[str] = []
            for item in value:
                if isinstance(item, (str, int, float, bool)):
                    result.append(str(item))
                elif dict_key and isinstance(item, dict):
                    dict_value = item.get(dict_key)
                    if isinstance(dict_value, (str, int, float, bool)):
                        result.append(str(dict_value))
            return result
        if isinstance(value, dict) and dict_key:
            dict_value = value.get(dict_key)
            if isinstance(dict_value, (str, int, float, bool)):
                return [str(dict_value)]
            return []
        if isinstance(value, (str, int, float, bool)):
            return [str(value)]
        return []
