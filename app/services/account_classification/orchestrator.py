"""账户分类编排器.."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from app.utils.structlog_config import log_error, log_info

from .cache import ClassificationCache
from .classifiers import ClassifierFactory
from .repositories import ClassificationRepository

if TYPE_CHECKING:
    from app.models.account_classification import ClassificationRule
    from app.models.account_permission import AccountPermission


class AccountClassificationService:
    """账户分类编排服务..

    协调规则加载、账户分组与分类执行的核心服务.
    负责自动分类账户、管理分类规则和缓存.

    Attributes:
        repository: 分类数据仓库.
        cache: 分类缓存管理器.
        classifier_factory: 分类器工厂.

    """

    def __init__(
        self,
        repository: ClassificationRepository | None = None,
        cache_backend: ClassificationCache | None = None,
        classifier_factory: ClassifierFactory | None = None,
    ) -> None:
        self.repository = repository or ClassificationRepository()
        self.cache = cache_backend or ClassificationCache()
        self.classifier_factory = classifier_factory or ClassifierFactory()

    # ------------------------------------------------------------------ API
    def auto_classify_accounts(
        self, instance_id: int | None = None, created_by: int | None = None,
    ) -> dict[str, Any]:
        """执行优化版账户自动分类流程..

        Args:
            instance_id: 限定的实例 ID,None 时表示全量处理.
            created_by: 触发任务的用户 ID.

        Returns:
            dict[str, Any]: 包含 success、message 及统计结果的字典.

        """
        start_time = time.time()
        try:
            rules = self._get_rules_sorted_by_priority()
            if not rules:
                return {"success": False, "error": "没有可用的分类规则"}

            accounts = self.repository.fetch_accounts(instance_id)
            if not accounts:
                return {"success": False, "error": "没有需要分类的账户"}

            self.repository.cleanup_all_assignments()

            log_info(
                "开始账户分类",
                module="account_classification",
                total_rules=len(rules),
                total_accounts=len(accounts),
                instance_id=instance_id,
                created_by=created_by,
            )

            result = self._classify_accounts_by_db_type(accounts, rules)
            duration = time.time() - start_time
            self._log_performance_stats(duration, len(accounts), len(rules), result)

            log_info(
                "账户分类完成",
                module="account_classification",
                classification_details=result,
            )

            return {"success": True, "message": "自动分类完成", **result}
        except Exception as exc:
            log_error("优化后的自动分类失败", module="account_classification", error=str(exc))
            return {"success": False, "error": f"自动分类失败: {exc}"}

    def invalidate_cache(self) -> bool:
        """清空缓存中的全部分类规则数据..

        Returns:
            bool: 缓存操作成功时为 True.

        """
        try:
            return self.cache.invalidate_all()
        except Exception as exc:
            log_error("清除分类缓存失败", module="account_classification", error=str(exc))
            return False

    def invalidate_db_type_cache(self, db_type: str) -> bool:
        """按数据库类型清理缓存..

        Args:
            db_type: 待清理的数据库类型标识.

        Returns:
            bool: 成功删除对应缓存时为 True.

        """
        try:
            return self.cache.invalidate_db_type(db_type)
        except Exception as exc:
            log_error("清除数据库类型缓存失败", module="account_classification", db_type=db_type, error=str(exc))
            return False

    # ----------------------------------------------------------- Internals
    def _get_rules_sorted_by_priority(self) -> list[ClassificationRule]:
        """按优先级获取分类规则列表..

        Returns:
            list[ClassificationRule]: 已排序的规则集合,包含缓存命中优先级.

        """
        cached_rules = self.cache.get_rules()
        if cached_rules:
            rules = self.repository.hydrate_rules(cached_rules)
            if rules:
                log_info(
                    "从缓存加载分类规则",
                    module="account_classification",
                    count=len(rules),
                )
                return rules

        rules = self.repository.fetch_active_rules()
        if rules:
            log_info("从数据库加载分类规则", module="account_classification", count=len(rules))
            serialized = self.repository.serialize_rules(rules)
            self.cache.set_rules(serialized)
        return rules

    @staticmethod
    def _group_accounts_by_db_type(accounts: list[AccountPermission]) -> dict[str, list[AccountPermission]]:
        """按数据库类型分组账户..

        Args:
            accounts: 待分类的账户列表.

        Returns:
            dict[str, list[AccountPermission]]: key 为 db_type 的账户映射.

        """
        grouped: dict[str, list[AccountPermission]] = {}
        for account in accounts:
            db_type = account.instance.db_type.lower()
            grouped.setdefault(db_type, []).append(account)
        grouped = dict(sorted(grouped.items()))
        log_info(
            "账户按数据库类型分组完成",
            module="account_classification",
            db_types=list(grouped.keys()),
            total_groups=len(grouped),
            accounts_per_group={db: len(items) for db, items in grouped.items()},
        )
        return grouped

    def _group_rules_by_db_type(self, rules: list[ClassificationRule]) -> dict[str, list[ClassificationRule]]:
        """按数据库类型分组分类规则..

        Args:
            rules: 需要分组的规则列表.

        Returns:
            dict[str, list[ClassificationRule]]: 分组后的规则映射.

        """
        grouped: dict[str, list[ClassificationRule]] = {}
        for rule in rules:
            db_type = (rule.db_type or "").lower()
            grouped.setdefault(db_type, []).append(rule)

        for db_type, db_rules in grouped.items():
            rule_names = [rule.rule_name for rule in db_rules]
            log_info(
                "数据库类型规则分组",
                module="account_classification",
                db_type=db_type,
                rule_names=rule_names,
                rule_count=len(db_rules),
            )
            serialized = self.repository.serialize_rules(db_rules)
            self.cache.set_rules_by_db_type(db_type, serialized)

        log_info(
            "规则按数据库类型分组完成",
            module="account_classification",
            db_types=list(grouped.keys()),
            total_groups=len(grouped),
            rules_per_group={db: len(items) for db, items in grouped.items()},
        )
        return grouped

    def _classify_accounts_by_db_type(
        self,
        accounts: list[AccountPermission],
        rules: list[ClassificationRule],
    ) -> dict[str, Any]:
        """基于数据库类型执行分类..

        Args:
            accounts: 全量待分类账户列表.
            rules: 全量分类规则.

        Returns:
            dict[str, Any]: 聚合的分类结果与各类型统计.

        """
        accounts_by_db_type = self._group_accounts_by_db_type(accounts)
        rules_by_db_type = self._group_rules_by_db_type(rules)

        total_classifications_added = 0
        total_matches = 0
        failed_count = 0
        all_errors: list[str] = []
        db_type_results: dict[str, Any] = {}

        for db_type, db_accounts in accounts_by_db_type.items():
            try:
                db_rules = rules_by_db_type.get(db_type, [])
                if not db_rules:
                    db_type_results[db_type] = {
                        "accounts": len(db_accounts),
                        "rules": 0,
                        "classifications_added": 0,
                        "matches": 0,
                        "errors": [],
                    }
                    continue

                result = self._classify_single_db_type(db_accounts, db_rules, db_type)
                total_classifications_added += result["total_classifications_added"]
                total_matches += result["total_matches"]
                failed_count += result["failed_count"]
                all_errors.extend(result["errors"])
                db_type_results[db_type] = result
            except Exception as exc:
                error_msg = f"数据库类型 {db_type} 分类失败: {exc}"
                log_error(error_msg, module="account_classification")
                all_errors.append(error_msg)
                failed_count += len(db_accounts)
                db_type_results[db_type] = {
                    "accounts": len(db_accounts),
                    "rules": len(rules_by_db_type.get(db_type, [])),
                    "classifications_added": 0,
                    "matches": 0,
                    "errors": [error_msg],
                }

        return {
            "total_accounts": len(accounts),
            "total_rules": len(rules),
            "classified_accounts": len({acc.id for acc in accounts}),
            "total_classifications_added": total_classifications_added,
            "total_matches": total_matches,
            "failed_count": failed_count,
            "errors": all_errors,
            "db_type_results": db_type_results,
        }

    def _classify_single_db_type(
        self,
        accounts: list[AccountPermission],
        rules: list[ClassificationRule],
        db_type: str,
    ) -> dict[str, Any]:
        """对单一数据库类型执行分类..

        Args:
            accounts: 指定类型的账户列表.
            rules: 需要评估的规则集合.
            db_type: 当前处理的数据库类型.

        Returns:
            dict[str, Any]: 包含分类统计、匹配数量与错误列表的结果.

        """
        total_classifications_added = 0
        total_matches = 0
        failed_count = 0
        errors: list[str] = []

        for rule in rules:
            try:
                matched_accounts = self._find_accounts_matching_rule(rule, accounts, db_type)
                if matched_accounts:
                    added_count = self.repository.upsert_assignments(
                        matched_accounts,
                        rule.classification_id,
                        rule_id=rule.id,
                    )
                    total_classifications_added += added_count
                    total_matches += len(matched_accounts)

                log_info(
                    "规则处理完成",
                    module="account_classification",
                    rule_id=rule.id,
                    db_type=db_type,
                    matched_accounts=len(matched_accounts),
                )
            except Exception as exc:
                error_msg = f"规则 {rule.rule_name} 处理失败: {exc}"
                log_error(error_msg, module="account_classification", rule_id=rule.id, db_type=db_type)
                errors.append(error_msg)
                failed_count += len(accounts)

        return {
            "total_accounts": len(accounts),
            "total_rules": len(rules),
            "total_classifications_added": total_classifications_added,
            "total_matches": total_matches,
            "failed_count": failed_count,
            "errors": errors,
        }

    def _find_accounts_matching_rule(
        self,
        rule: ClassificationRule,
        accounts: list[AccountPermission],
        db_type: str,
    ) -> list[AccountPermission]:
        """筛选匹配指定规则的账户..

        Args:
            rule: 待评估的分类规则.
            accounts: 候选账户列表.
            db_type: 目标数据库类型.

        Returns:
            list[AccountPermission]: 满足规则的账户列表.

        """
        filtered_accounts = [acc for acc in accounts if acc.instance.db_type.lower() == db_type]
        if not filtered_accounts:
            return []

        matched_accounts: list[AccountPermission] = []
        for account in filtered_accounts:
            if self._evaluate_rule(account, rule):
                matched_accounts.append(account)
        return matched_accounts

    def _evaluate_rule(self, account: AccountPermission, rule: ClassificationRule) -> bool:
        """执行规则评估..

        Args:
            account: 目标账户权限对象.
            rule: 分类规则实体.

        Returns:
            bool: 账户满足规则返回 True,否则 False.

        """
        classifier = self.classifier_factory.get(rule.db_type)
        if not classifier:
            return False
        rule_expression = rule.get_rule_expression()
        if not rule_expression:
            return False
        return classifier.evaluate(account, rule_expression)

    @staticmethod
    def _log_performance_stats(duration: float, total_accounts: int, total_rules: int, result: dict[str, Any]) -> None:
        """输出性能统计日志..

        Args:
            duration: 分类耗时(秒).
            total_accounts: 参与分类的账户数量.
            total_rules: 本次评估的规则数量.
            result: 分类结果聚合字典.

        Returns:
            None: 仅记录日志.

        """
        accounts_per_second = total_accounts / duration if duration > 0 else 0
        log_info(
            "账户分类性能统计",
            module="account_classification",
            duration=f"{duration:.2f}秒",
            total_accounts=total_accounts,
            total_rules=total_rules,
            accounts_per_second=f"{accounts_per_second:.2f}",
            total_classifications_added=result.get("total_classifications_added", 0),
            total_matches=result.get("total_matches", 0),
            failed_count=result.get("failed_count", 0),
        )
