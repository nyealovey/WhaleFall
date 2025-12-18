"""Oracle 规则分类器.

实现 Oracle 数据库的账户分类规则评估逻辑,支持角色、系统权限和对象权限的匹配.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

from app.utils.structlog_config import log_error

from .base import CLASSIFIER_EVALUATION_EXCEPTIONS, BaseRuleClassifier

if TYPE_CHECKING:
    from app.models.account_permission import AccountPermission
    from app.types import RuleExpression


class OracleRuleClassifier(BaseRuleClassifier):
    """Oracle 规则分类器.

    实现 Oracle 数据库的账户分类规则评估,支持以下规则类型:
    - roles: 角色匹配
    - system_privileges: 系统权限匹配
    - object_privileges: 对象权限匹配

    Attributes:
        db_type: 数据库类型标识符,固定为 'oracle'.

    Example:
        >>> classifier = OracleRuleClassifier()
        >>> rule = {'roles': ['DBA'], 'operator': 'OR'}
        >>> classifier.evaluate(account, rule)
        True

    """

    db_type = "oracle"

    def evaluate(self, account: AccountPermission, rule_expression: RuleExpression) -> bool:
        """评估账户是否满足 Oracle 规则表达式.

        Args:
            account: 账户权限对象.
            rule_expression: 规则表达式字典,支持以下字段:
                - operator: 逻辑运算符('AND' 或 'OR'),默认为 'OR'
                - roles: 角色列表
                - system_privileges: 系统权限列表
                - object_privileges: 对象权限列表

        Returns:
            如果账户满足规则返回 True,否则返回 False.

        Example:
            >>> rule = {
            ...     'system_privileges': ['CREATE SESSION', 'CREATE TABLE'],
            ...     'operator': 'AND'
            ... }
            >>> classifier.evaluate(account, rule)
            True

        """
        try:
            permissions = account.get_permissions_by_db_type() or {}
            operator = self._resolve_operator(rule_expression)
            match_results = [
                self._match_roles(permissions, rule_expression),
                self._match_system_privileges(permissions, rule_expression, operator),
                self._match_object_privileges(permissions, rule_expression, operator),
                self._match_tablespace_privileges(permissions, rule_expression, operator),
            ]
            return self._combine_results(match_results, operator)
        except CLASSIFIER_EVALUATION_EXCEPTIONS as exc:
            log_error("评估Oracle规则失败", module="account_classification", error=str(exc))
            return False

    @staticmethod
    def _resolve_operator(rule_expression: RuleExpression) -> str:
        """解析逻辑运算符."""
        operator = str(rule_expression.get("operator", "OR")).upper()
        return operator if operator in {"AND", "OR"} else "OR"

    @staticmethod
    def _combine_results(results: list[bool], operator: str) -> bool:
        """根据 operator 汇总布尔结果.

        Args:
            results: 各子条件的匹配结果.
            operator: 'AND' 或 'OR',决定组合逻辑.

        Returns:
            bool: 当结果列表为空时视为 True,否则按运算符聚合.

        """
        if not results:
            return True
        if operator == "AND":
            return all(results)
        return any(results)

    @staticmethod
    def _normalize_tablespace_privileges(source: object) -> list[dict[str, Any]]:
        """支持 dict/list 两种结构的表空间权限.

        Args:
            source: 可能为 dict、list 或其它类型的权限载体.

        Returns:
            list[dict[str, Any]]: 标准化后的表空间权限列表.

        """
        normalized: list[dict[str, Any]] = []
        if isinstance(source, dict):
            normalized.extend(
                {
                    "tablespace_name": tablespace_name,
                    "privilege": privilege,
                }
                for tablespace_name, privileges in source.items()
                for privilege in (privileges if isinstance(privileges, list) else [privileges])
            )
        elif isinstance(source, list):
            normalized = [item for item in source if isinstance(item, dict)]
        return normalized

    @staticmethod
    def _ensure_list(value: object | None) -> list[Any]:
        """确保值为列表."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]

    def _match_roles(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
    ) -> bool:
        """校验角色匹配."""
        required_roles = self._ensure_list(rule_expression.get("roles"))
        if not required_roles:
            return True
        actual_roles = permissions.get("oracle_roles") or []
        role_names = {
            role.get("role") if isinstance(role, Mapping) else role for role in self._ensure_list(actual_roles)
        }
        return all(role in role_names for role in required_roles)

    def _match_system_privileges(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        """校验系统权限."""
        required_privs = self._ensure_list(rule_expression.get("system_privileges"))
        if not required_privs:
            return True
        system_privileges = permissions.get("oracle_system_privileges") or []
        system_priv_names = {
            priv.get("privilege") if isinstance(priv, Mapping) else priv
            for priv in self._ensure_list(system_privileges)
        }
        if operator == "AND":
            return all(priv in system_priv_names for priv in required_privs)
        return any(priv in system_priv_names for priv in required_privs)

    def _match_object_privileges(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        """校验对象权限."""
        required_object_privs = cast(
            "Sequence[Mapping[str, str]] | None",
            rule_expression.get("object_privileges"),
        ) or []
        if not required_object_privs:
            return True
        object_privileges = self._ensure_list(permissions.get("object_privileges"))
        if operator == "AND":
            return all(
                self._object_requirement_satisfied(requirement, object_privileges)
                for requirement in required_object_privs
            )
        return any(
            self._object_requirement_satisfied(requirement, object_privileges)
            for requirement in required_object_privs
        )

    @staticmethod
    def _object_requirement_satisfied(
        requirement: Mapping[str, str],
        object_privileges: Sequence[object],
    ) -> bool:
        """检查单个对象权限要求是否满足."""
        required_priv = requirement.get("privilege")
        required_object = requirement.get("object_name")
        for privilege in object_privileges:
            priv_name = privilege.get("privilege") if isinstance(privilege, Mapping) else privilege
            object_name = privilege.get("object_name") if isinstance(privilege, Mapping) else None
            priv_ok = required_priv in (priv_name, "*")
            obj_ok = required_object in (object_name, "*")
            if priv_ok and obj_ok:
                return True
        return False

    def _match_tablespace_privileges(
        self,
        permissions: dict[str, object],
        rule_expression: RuleExpression,
        operator: str,
    ) -> bool:
        """校验表空间权限."""
        required_tablespace = cast(
            "Sequence[Mapping[str, str]] | None",
            rule_expression.get("tablespace_privileges"),
        ) or []
        if not required_tablespace:
            return True
        tablespace_privileges = self._normalize_tablespace_privileges(
            permissions.get("oracle_tablespace_privileges") or {},
        )
        if operator == "AND":
            return all(
                self._tablespace_requirement_satisfied(requirement, tablespace_privileges)
                for requirement in required_tablespace
            )
        return any(
            self._tablespace_requirement_satisfied(requirement, tablespace_privileges)
            for requirement in required_tablespace
        )

    @staticmethod
    def _tablespace_requirement_satisfied(
        requirement: Mapping[str, str],
        tablespace_privileges: Sequence[dict[str, Any]],
    ) -> bool:
        """判断表空间权限是否满足."""
        required_priv = requirement.get("privilege")
        required_table = requirement.get("tablespace_name")
        for privilege in tablespace_privileges:
            priv_name = privilege.get("privilege")
            tablespace_name = privilege.get("tablespace_name")
            priv_ok = required_priv in (priv_name, "*")
            ts_ok = required_table in (tablespace_name, "*")
            if priv_ok and ts_ok:
                return True
        return False
