"""
鲸落 - 优化后的账户分类管理服务
支持全量重新分类、按规则逐个处理、多分类支持
"""

import time
from typing import Any

from app import db
from app.constants import TaskStatus
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance
from app.services.cache_service import cache_manager
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils


class AccountClassificationService:
    """优化后的账户分类管理服务"""

    def __init__(self) -> None:
        """初始化优化后的账户分类服务"""

    def auto_classify_accounts_optimized(
        self,
        instance_id: int = None,
        created_by: int = None,
    ) -> dict[str, Any]:
        """
        优化后的自动分类账户 - 全量重新分类

        Args:
            instance_id: 实例ID，None表示所有实例
            created_by: 创建者用户ID

        Returns:
            Dict: 分类结果
        """
        start_time = time.time()

        try:
            # 1. 获取所有活跃规则，按优先级排序
            rules = self._get_rules_sorted_by_priority()
            if not rules:
                return {"success": False, "error": "没有可用的分类规则"}

            # 2. 获取需要分类的账户
            accounts = self._get_accounts_to_classify(instance_id)
            if not accounts:
                return {"success": False, "error": "没有需要分类的账户"}

            # 3. 清理所有旧的分配记录，确保数据一致性
            self._cleanup_all_old_assignments()
            log_info(
                "已清理所有旧分配记录，准备重新分类",
                module="account_classification"
            )

            log_info(
                "开始优化后的自动分类",
                module="account_classification",
                total_rules=len(rules),
                total_accounts=len(accounts),
                instance_id=instance_id,
            )

            # 5. 按数据库类型优化分类
            result = self._classify_accounts_by_db_type_optimized(accounts, rules)

            # 5. 分类完成
            log_info(
                "自动分类完成",
                module="account_classification",
                classification_details=result,
            )

            # 6. 性能监控
            duration = time.time() - start_time
            self._log_performance_stats(duration, len(accounts), len(rules), result)

            return {
                "success": True,
                "message": "自动分类完成",
                **result,
            }

        except Exception as e:
            log_error(f"优化后的自动分类失败: {e}", module="account_classification")
            return {"success": False, "error": f"自动分类失败: {str(e)}"}

    def _get_rules_sorted_by_priority(self) -> list[ClassificationRule]:
        """获取按优先级排序的规则（带缓存）"""
        try:
            # 尝试从缓存获取规则
            if cache_manager:
                cached_data = cache_manager.get_classification_rules_cache()
                if cached_data and isinstance(cached_data, dict) and "rules" in cached_data:
                    cached_rules = cached_data["rules"]
                    log_info("从缓存获取分类规则", module="account_classification", count=len(cached_rules))
                    # 将缓存的字典数据转换回ClassificationRule对象
                    return self._rules_from_cache_data(cached_rules)
                elif cached_data and isinstance(cached_data, list):
                    # 兼容旧格式缓存数据
                    log_info("从缓存获取分类规则（旧格式）", module="account_classification", count=len(cached_data))
                    return self._rules_from_cache_data(cached_data)

            # 缓存未命中，从数据库查询
            rules = (
                ClassificationRule.query.filter_by(is_active=True)
                .order_by(ClassificationRule.created_at.asc())
                .all()
            )

            # 记录加载的规则信息
            rule_names = [rule.rule_name for rule in rules]
            log_info(f"从数据库加载分类规则: {rule_names}", module="account_classification", count=len(rules))

            # 将规则存入缓存
            if cache_manager and rules:
                rules_data = self._rules_to_cache_data(rules)
                cache_manager.set_classification_rules_cache(rules_data)
                # 移除详细的缓存日志，减少日志噪音

            return rules
        except Exception as e:
            log_error(f"获取规则失败: {e}", module="account_classification")
            return []

    def _get_accounts_to_classify(self, instance_id: int = None) -> list[CurrentAccountSyncData]:
        """获取需要分类的账户"""
        try:
            from app.models.instance_account import InstanceAccount

            query = (
                CurrentAccountSyncData.query.join(Instance)
                .join(InstanceAccount, CurrentAccountSyncData.instance_account)
                .filter(
                    Instance.is_active.is_(True),
                    Instance.deleted_at.is_(None),
                    InstanceAccount.is_active.is_(True),
                )
            )

            if instance_id:
                query = query.filter(CurrentAccountSyncData.instance_id == instance_id)

            return query.all()
        except Exception as e:
            log_error(f"获取账户失败: {e}", module="account_classification")
            return []

    def _group_accounts_by_db_type(self, accounts: list[CurrentAccountSyncData]) -> dict[str, list[CurrentAccountSyncData]]:
        """按数据库类型分组账户（优化性能，带缓存）"""
        try:
            grouped = {}
            
            # 按数据库类型分组
            for account in accounts:
                db_type = account.instance.db_type.lower()
                if db_type not in grouped:
                    grouped[db_type] = []
                grouped[db_type].append(account)
            
            # 按数据库类型名称排序，确保处理顺序的一致性
            # 这样可以避免因查询顺序不确定导致的跨数据库类型覆盖问题
            grouped = dict(sorted(grouped.items()))
            
            # 缓存分组结果（用于后续优化）
            if cache_manager:
                for db_type, db_accounts in grouped.items():
                    try:
                        # 将账户对象转换为可缓存的字典格式
                        accounts_data = self._accounts_to_cache_data(db_accounts)
                        cache_manager.set_accounts_by_db_type_cache(db_type, accounts_data)
                    except Exception as e:
                        log_error(f"缓存数据库类型账户失败: {db_type}", module="account_classification", error=str(e))
            
            log_info(
                f"账户按数据库类型分组完成",
                module="account_classification",
                db_types=list(grouped.keys()),
                total_groups=len(grouped),
                accounts_per_group={db_type: len(accs) for db_type, accs in grouped.items()}
            )
            
            return grouped
        except Exception as e:
            log_error(f"按数据库类型分组账户失败: {e}", module="account_classification")
            return {}

    def _group_rules_by_db_type(self, rules: list[ClassificationRule]) -> dict[str, list[ClassificationRule]]:
        """按数据库类型分组规则（优化性能，带缓存）"""
        try:
            grouped = {}
            
            # 按数据库类型分组
            for rule in rules:
                db_type = rule.db_type.lower()
                if db_type not in grouped:
                    grouped[db_type] = []
                grouped[db_type].append(rule)
            
            # 缓存分组结果（用于后续优化）
            if cache_manager:
                for db_type, db_rules in grouped.items():
                    try:
                        # 将规则对象转换为可缓存的字典格式
                        rules_data = self._rules_to_cache_data(db_rules)
                        cache_manager.set_classification_rules_by_db_type_cache(db_type, rules_data)
                        # 移除详细的缓存日志，减少日志噪音
                    except Exception as e:
                        log_error(f"缓存数据库类型规则失败: {db_type}", module="account_classification", error=str(e))
            
            # 记录每个数据库类型的规则详情
            for db_type, db_rules in grouped.items():
                rule_names = [rule.rule_name for rule in db_rules]
                log_info(
                    f"数据库类型 {db_type} 规则分组",
                    module="account_classification",
                    rule_names=rule_names,
                    rule_count=len(db_rules)
                )
            
            log_info(
                f"规则按数据库类型分组完成",
                module="account_classification",
                db_types=list(grouped.keys()),
                total_groups=len(grouped),
                rules_per_group={db_type: len(rules) for db_type, rules in grouped.items()}
            )
            
            return grouped
        except Exception as e:
            log_error(f"按数据库类型分组规则失败: {e}", module="account_classification")
            return {}

    def _classify_accounts_by_db_type_optimized(
        self, accounts: list[CurrentAccountSyncData], rules: list[ClassificationRule]
    ) -> dict[str, Any]:
        """按数据库类型优化分类（阶段1优化）"""
        try:
            # 1. 按数据库类型预分组
            accounts_by_db_type = self._group_accounts_by_db_type(accounts)
            rules_by_db_type = self._group_rules_by_db_type(rules)
            
            if not accounts_by_db_type:
                return {
                    "total_accounts": 0,
                    "total_rules": 0,
                    "classified_accounts": 0,
                    "total_classifications_added": 0,
                    "total_matches": 0,
                    "failed_count": 0,
                    "errors": [],
                    "db_type_results": {}
                }
            
            # 2. 分类分配已在主函数中清理，无需重复清理
            
            # 3. 按数据库类型并行处理（当前为串行，后续可优化为并行）
            total_classifications_added = 0
            total_matches = 0
            failed_count = 0
            all_errors = []
            db_type_results = {}
            
            for db_type, db_accounts in accounts_by_db_type.items():
                try:
                    # 记录处理顺序，便于调试跨数据库类型覆盖问题
                    log_info(
                        f"开始处理数据库类型: {db_type}",
                        module="account_classification",
                        account_count=len(db_accounts),
                        processing_order=list(accounts_by_db_type.keys()).index(db_type) + 1,
                        total_db_types=len(accounts_by_db_type)
                    )
                    
                    # 获取该数据库类型的规则
                    db_rules = rules_by_db_type.get(db_type, [])
                    
                    if not db_rules:
                        log_info(
                            f"数据库类型 {db_type} 没有可用规则，跳过",
                            module="account_classification",
                            account_count=len(db_accounts)
                        )
                        db_type_results[db_type] = {
                            "accounts": len(db_accounts),
                            "rules": 0,
                            "classifications_added": 0,
                            "matches": 0,
                            "errors": []
                        }
                        continue
                    
                    # 处理该数据库类型的分类
                    result = self._classify_single_db_type(db_accounts, db_rules, db_type)
                    
                    # 累计结果
                    total_classifications_added += result["total_classifications_added"]
                    total_matches += result["total_matches"]
                    failed_count += result["failed_count"]
                    all_errors.extend(result["errors"])
                    db_type_results[db_type] = result
                    
                    log_info(
                        f"数据库类型 {db_type} 分类完成",
                        module="account_classification",
                        accounts=result["total_accounts"],
                        rules=result["total_rules"],
                        classifications_added=result["total_classifications_added"],
                        matches=result["total_matches"],
                        errors=len(result["errors"]),
                        processing_order=list(accounts_by_db_type.keys()).index(db_type) + 1,
                        total_db_types=len(accounts_by_db_type)
                    )
                    
                except Exception as e:
                    error_msg = f"数据库类型 {db_type} 分类失败: {str(e)}"
                    log_error(error_msg, module="account_classification")
                    all_errors.append(error_msg)
                    failed_count += len(db_accounts)
                    db_type_results[db_type] = {
                        "accounts": len(db_accounts),
                        "rules": len(rules_by_db_type.get(db_type, [])),
                        "classifications_added": 0,
                        "matches": 0,
                        "errors": [error_msg]
                    }
            
            # 4. 分类完成，无需更新分类时间字段
            
            return {
                "total_accounts": len(accounts),
                "total_rules": len(rules),
                "classified_accounts": len({acc.id for acc in accounts}),
                "total_classifications_added": total_classifications_added,
                "total_matches": total_matches,
                "failed_count": failed_count,
                "errors": all_errors,
                "db_type_results": db_type_results
            }
            
        except Exception as e:
            log_error(f"按数据库类型优化分类失败: {e}", module="account_classification")
            raise

    def _classify_single_db_type(
        self, accounts: list[CurrentAccountSyncData], rules: list[ClassificationRule], db_type: str
    ) -> dict[str, Any]:
        """处理单个数据库类型的分类"""
        try:
            total_classifications_added = 0
            total_matches = 0
            failed_count = 0
            errors = []
            
            # 按优先级处理规则
            for rule in rules:
                try:
                    # 只处理匹配数据库类型的账户
                    matched_accounts = self._find_accounts_matching_rule_optimized(rule, accounts, db_type)
                    
                    if matched_accounts:
                        # 批量添加分类
                        added_count = self._add_classification_to_accounts_batch(
                            matched_accounts, rule.classification_id
                        )
                        
                        total_classifications_added += added_count
                        total_matches += len(matched_accounts)
                    
                    # 无论是否匹配到账户，都记录规则处理完成
                    log_info(
                        f"规则 {rule.rule_name} 处理完成",
                        module="account_classification",
                        rule_id=rule.id,
                        db_type=db_type,
                        matched_accounts=len(matched_accounts),
                        added_classifications=added_count if matched_accounts else 0
                    )
                        
                except Exception as e:
                    error_msg = f"规则 {rule.rule_name} 处理失败: {str(e)}"
                    log_error(error_msg, module="account_classification", rule_id=rule.id, db_type=db_type)
                    errors.append(error_msg)
                    failed_count += len(accounts)
            
            return {
                "total_accounts": len(accounts),
                "total_rules": len(rules),
                "total_classifications_added": total_classifications_added,
                "total_matches": total_matches,
                "failed_count": failed_count,
                "errors": errors
            }
            
        except Exception as e:
            log_error(f"处理数据库类型 {db_type} 分类失败: {e}", module="account_classification")
            raise

    def _find_accounts_matching_rule_optimized(
        self, rule: ClassificationRule, accounts: list[CurrentAccountSyncData], db_type: str
    ) -> list[CurrentAccountSyncData]:
        """优化的规则匹配方法（按数据库类型过滤）"""
        try:
            # 预过滤：只处理匹配数据库类型的账户
            filtered_accounts = [acc for acc in accounts if acc.instance.db_type.lower() == db_type]
            
            if not filtered_accounts:
                return []
            
            # 使用现有的规则评估逻辑
            matched_accounts = []
            error_count = 0
            for account in filtered_accounts:
                try:
                    if self._evaluate_rule(account, rule):
                        matched_accounts.append(account)
                except Exception as e:
                    error_count += 1
                    # 只记录错误，不记录每个账户的详细信息
                    continue
            
            # 记录规则级别的汇总信息
            log_info(
                f"评估MySQL规则: {rule.rule_name}",
                module="account_classification",
                rule_id=rule.id,
                db_type=db_type,
                total_accounts=len(filtered_accounts),
                matched_accounts=len(matched_accounts),
                error_count=error_count
            )
            
            return matched_accounts
            
        except Exception as e:
            log_error(f"查找匹配规则账户失败: {e}", module="account_classification")
            return []

    def _evaluate_rule(self, account: CurrentAccountSyncData, rule: ClassificationRule) -> bool:
        """评估规则是否匹配账户（带缓存）"""
        try:
            # 尝试从缓存获取规则评估结果
            if cache_manager:
                cached_result = cache_manager.get_rule_evaluation_cache(rule.id, account.id)
                if cached_result is not None:
                    # 移除详细的缓存日志，减少日志噪音
                    return cached_result

            # 缓存未命中，执行规则评估
            rule_expression = rule.get_rule_expression()
            if not rule_expression:
                result = False
            else:
                # 根据规则类型进行不同的匹配逻辑
                if rule_expression.get("type") == "mysql_permissions":
                    result = self._evaluate_mysql_rule(account, rule_expression)
                elif rule_expression.get("type") == "sqlserver_permissions":
                    result = self._evaluate_sqlserver_rule(account, rule_expression)
                elif rule_expression.get("type") == "postgresql_permissions":
                    result = self._evaluate_postgresql_rule(account, rule_expression)
                elif rule_expression.get("type") == "oracle_permissions":
                    result = self._evaluate_oracle_rule(account, rule_expression)
                else:
                    result = False

            # 将评估结果存入缓存
            if cache_manager:
                cache_manager.set_rule_evaluation_cache(rule.id, account.id, result)
                # 移除详细的缓存日志，减少日志噪音

            return result

        except Exception as e:
            log_error(f"评估规则失败: {e}", module="account_classification")
            return False

    def _evaluate_mysql_rule(self, account: CurrentAccountSyncData, rule_expression: dict) -> bool:
        """评估MySQL规则"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                # 移除详细的账户级别日志，减少日志噪音
                return False

            operator = rule_expression.get("operator", "OR").upper()

            # 移除详细的账户级别日志，减少日志噪音

            # 检查全局权限
            required_global = rule_expression.get("global_privileges", [])
            if required_global:
                actual_global = permissions.get("global_privileges", [])
                if actual_global is None:
                    actual_global_set = set()
                elif isinstance(actual_global, list):
                    # 处理混合格式：字符串和字典的混合列表
                    actual_global_set = set()
                    for perm in actual_global:
                        if isinstance(perm, str):
                            actual_global_set.add(perm)
                        elif isinstance(perm, dict) and perm.get("granted", False):
                            actual_global_set.add(perm["privilege"])
                else:
                    actual_global_set = {p["privilege"] for p in actual_global if p.get("granted", False)}


                if operator == "AND":
                    if not all(perm in actual_global_set for perm in required_global):
                        return False
                else:
                    if not any(perm in actual_global_set for perm in required_global):
                        return False

            # 检查排除权限
            exclude_global = rule_expression.get("exclude_privileges", [])
            if exclude_global:
                actual_global = permissions.get("global_privileges", [])
                if actual_global is None:
                    actual_global_set = set()
                elif isinstance(actual_global, list):
                    # 处理混合格式：字符串和字典的混合列表
                    actual_global_set = set()
                    for perm in actual_global:
                        if isinstance(perm, str):
                            actual_global_set.add(perm)
                        elif isinstance(perm, dict) and perm.get("granted", False):
                            actual_global_set.add(perm["privilege"])
                else:
                    actual_global_set = {p["privilege"] for p in actual_global if p.get("granted", False)}

                if any(perm in actual_global_set for perm in exclude_global):
                    return False

            # 检查数据库权限
            required_database = rule_expression.get("database_privileges", [])
            if required_database:
                actual_database = permissions.get("database_privileges", {})
                if actual_database:
                    # 检查是否在任意数据库中有任一要求的权限
                    database_match = False
                    for db_name, db_perms in actual_database.items():
                        if isinstance(db_perms, list):
                            db_perms_set = set(db_perms)
                        else:
                            db_perms_set = {p["privilege"] for p in db_perms if p.get("granted", False)}
                        
                        if operator == "AND":
                            if all(perm in db_perms_set for perm in required_database):
                                database_match = True
                                break
                        else:
                            if any(perm in db_perms_set for perm in required_database):
                                database_match = True
                                break
                    
                    if not database_match:
                        return False

            return True

        except Exception as e:
            log_error(f"评估MySQL规则失败: {e}", module="account_classification")
            return False

    def _evaluate_sqlserver_rule(self, account: CurrentAccountSyncData, rule_expression: dict) -> bool:
        """评估SQL Server规则"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()
            match_results = []

            # 检查服务器权限
            required_server_perms = rule_expression.get("server_permissions", [])
            if required_server_perms:
                server_perms_data = permissions.get("server_permissions", [])
                if server_perms_data and isinstance(server_perms_data[0], str):
                    actual_server_perms = server_perms_data
                else:
                    actual_server_perms = [
                        p["permission"] if isinstance(p, dict) else p
                        for p in server_perms_data
                        if isinstance(p, dict) and p.get("granted", False)
                    ]

                server_perms_match = all(perm in actual_server_perms for perm in required_server_perms)
                match_results.append(server_perms_match)

            # 检查服务器角色
            required_server_roles = rule_expression.get("server_roles", [])
            if required_server_roles:
                server_roles_data = permissions.get("server_roles", [])
                if server_roles_data and isinstance(server_roles_data[0], str):
                    actual_server_roles = server_roles_data
                else:
                    actual_server_roles = [r["role"] if isinstance(r, dict) else r for r in server_roles_data]

                server_roles_match = all(role in actual_server_roles for role in required_server_roles)
                match_results.append(server_roles_match)

            # 检查数据库角色
            required_database_roles = rule_expression.get("database_roles", [])
            if required_database_roles:
                database_roles_data = permissions.get("database_roles", {})
                if database_roles_data:
                    # 检查是否在任意数据库中有任一要求的角色
                    database_roles_match = False
                    for db_name, roles in database_roles_data.items():
                        if isinstance(roles, list):
                            actual_roles = roles
                        else:
                            actual_roles = [r["role"] if isinstance(r, dict) else r for r in roles]
                        
                        # 检查是否有任一要求的角色
                        if any(role in actual_roles for role in required_database_roles):
                            database_roles_match = True
                            break
                    
                    match_results.append(database_roles_match)

            # 检查数据库权限
            required_database_perms = rule_expression.get("database_privileges", [])
            if required_database_perms:
                database_perms_data = permissions.get("database_permissions", {})
                if database_perms_data:
                    # 检查是否在任意数据库中有任一要求的权限
                    database_perms_match = False
                    for db_name, perms in database_perms_data.items():
                        if isinstance(perms, dict):
                            # 检查数据库级别权限
                            db_perms = perms.get("database", [])
                            if any(perm in db_perms for perm in required_database_perms):
                                database_perms_match = True
                                break
                        elif isinstance(perms, list):
                            if any(perm in perms for perm in required_database_perms):
                                database_perms_match = True
                                break
                    
                    match_results.append(database_perms_match)

            # 根据操作符决定匹配逻辑
            if not match_results:
                return True

            if operator == "AND":
                return all(match_results)
            return any(match_results)

        except Exception as e:
            log_error(f"评估SQL Server规则失败: {e}", module="account_classification")
            return False

    def _evaluate_postgresql_rule(self, account: CurrentAccountSyncData, rule_expression: dict) -> bool:
        """评估PostgreSQL规则"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()
            match_results = []

            # 检查预定义角色
            required_predefined_roles = rule_expression.get("predefined_roles", [])
            if required_predefined_roles:
                actual_predefined_roles = permissions.get("predefined_roles", [])
                if isinstance(actual_predefined_roles, list):
                    predefined_roles_set = set(actual_predefined_roles)
                else:
                    predefined_roles_set = {r["role"] if isinstance(r, dict) else r for r in actual_predefined_roles}
                
                predefined_roles_match = all(role in predefined_roles_set for role in required_predefined_roles)
                match_results.append(predefined_roles_match)

            # 检查角色属性权限
            required_role_attrs = rule_expression.get("role_attributes", [])
            if required_role_attrs:
                role_attrs = permissions.get("role_attributes", {})
                role_attrs_match = all(role_attrs.get(attr, False) for attr in required_role_attrs)
                match_results.append(role_attrs_match)

            # 检查数据库权限
            required_database_perms = rule_expression.get("database_privileges", [])
            if required_database_perms:
                database_perms = permissions.get("database_privileges", {})
                if database_perms:
                    database_perms_match = False
                    for db_name, db_perms in database_perms.items():
                        if isinstance(db_perms, list):
                            db_perms_set = set(db_perms)
                        else:
                            db_perms_set = {p["privilege"] for p in db_perms if p.get("granted", False)}
                        
                        if any(perm in db_perms_set for perm in required_database_perms):
                            database_perms_match = True
                            break
                    
                    match_results.append(database_perms_match)

            # 检查表空间权限
            required_tablespace_perms = rule_expression.get("tablespace_privileges", [])
            if required_tablespace_perms:
                tablespace_perms = permissions.get("tablespace_privileges", {})
                if tablespace_perms:
                    tablespace_perms_match = False
                    for tablespace_name, ts_perms in tablespace_perms.items():
                        if isinstance(ts_perms, list):
                            ts_perms_set = set(ts_perms)
                        else:
                            ts_perms_set = {p["privilege"] for p in ts_perms if p.get("granted", False)}
                        
                        if any(perm in ts_perms_set for perm in required_tablespace_perms):
                            tablespace_perms_match = True
                            break
                    
                    match_results.append(tablespace_perms_match)

            # 根据操作符决定匹配逻辑
            if not match_results:
                return True

            if operator == "AND":
                return all(match_results)
            return any(match_results)

        except Exception as e:
            log_error(f"评估PostgreSQL规则失败: {e}", module="account_classification")
            return False

    def _evaluate_oracle_rule(self, account: CurrentAccountSyncData, rule_expression: dict) -> bool:
        """评估Oracle规则"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()
            match_results = []

            # 检查角色
            required_roles = rule_expression.get("roles", [])
            if required_roles:
                account_roles = permissions.get("oracle_roles", [])
                if isinstance(account_roles, list):
                    roles_set = set(account_roles)
                else:
                    roles_set = {r["role"] if isinstance(r, dict) else r for r in account_roles}
                
                roles_match = all(role in roles_set for role in required_roles)
                match_results.append(roles_match)

            # 检查系统权限
            required_system_perms = rule_expression.get("system_privileges", [])
            if required_system_perms:
                account_system_perms = permissions.get("system_privileges", [])
                if isinstance(account_system_perms, list):
                    system_perms_set = set(account_system_perms)
                else:
                    system_perms_set = {p["privilege"] for p in account_system_perms if p.get("granted", False)}
                
                system_perms_match = all(perm in system_perms_set for perm in required_system_perms)
                match_results.append(system_perms_match)

            # 检查表空间权限
            required_tablespace_perms = rule_expression.get("tablespace_privileges", [])
            if required_tablespace_perms:
                tablespace_perms = permissions.get("tablespace_privileges", {})
                if tablespace_perms:
                    tablespace_perms_match = False
                    for tablespace_name, ts_perms in tablespace_perms.items():
                        if isinstance(ts_perms, list):
                            ts_perms_set = set(ts_perms)
                        else:
                            ts_perms_set = {p["privilege"] for p in ts_perms if p.get("granted", False)}
                        
                        if any(perm in ts_perms_set for perm in required_tablespace_perms):
                            tablespace_perms_match = True
                            break
                    
                    match_results.append(tablespace_perms_match)

            # 检查表空间配额
            required_tablespace_quotas = rule_expression.get("tablespace_quotas", [])
            if required_tablespace_quotas:
                tablespace_quotas = permissions.get("tablespace_quotas", {})
                if tablespace_quotas:
                    tablespace_quotas_match = False
                    for tablespace_name, quota_info in tablespace_quotas.items():
                        if isinstance(quota_info, list):
                            quota_set = set(quota_info)
                        else:
                            quota_set = {q["quota"] if isinstance(q, dict) else q for q in quota_info}
                        
                        if any(quota in quota_set for quota in required_tablespace_quotas):
                            tablespace_quotas_match = True
                            break
                    
                    match_results.append(tablespace_quotas_match)

            # 根据操作符决定匹配逻辑
            if not match_results:
                return True

            if operator == "AND":
                return all(match_results)
            return any(match_results)

        except Exception as e:
            log_error(f"评估Oracle规则失败: {e}", module="account_classification")
            return False


    def _add_classification_to_accounts_batch(
        self, matched_accounts: list[CurrentAccountSyncData], classification_id: int
    ) -> int:
        """批量添加分类到账户 - 只保留最新的分配记录"""
        try:
            if not matched_accounts:
                return 0

            # 获取账户ID列表
            account_ids = [account.id for account in matched_accounts]

            # 1. 先清理**这些账户**的该分类旧分配记录（包括活跃和非活跃的）
            # 关键修改：限制删除范围到当前匹配的账户，避免跨数据库类型覆盖
            deleted_count = (
                db.session.query(AccountClassificationAssignment)
                .filter(
                    AccountClassificationAssignment.classification_id == classification_id,
                    AccountClassificationAssignment.account_id.in_(account_ids)  # 新增：限制到当前账户
                )
                .delete()
            )
            
            if deleted_count > 0:
                log_info(
                    f"清理分类 {classification_id} 的旧分配记录（针对账户）: {deleted_count} 条",
                    module="account_classification",
                    classification_id=classification_id,
                    deleted_count=deleted_count,
                    account_ids=account_ids
                )

            # 2. 准备新的分类分配记录
            new_assignments = []
            for account in matched_accounts:
                new_assignments.append(
                    {
                        "account_id": account.id,
                        "classification_id": classification_id,
                        "assigned_by": None,
                        "assignment_type": "auto",
                        "notes": None,
                        "is_active": True,
                        "created_at": time_utils.now(),
                        "updated_at": time_utils.now(),
                    }
                )

            # 3. 批量插入新的分配记录
            if new_assignments:
                try:
                    db.session.bulk_insert_mappings(AccountClassificationAssignment, new_assignments)
                    db.session.commit()
                    
                    # 验证数据是否真的写入了数据库（限制到当前账户范围）
                    actual_count = (
                        db.session.query(AccountClassificationAssignment)
                        .filter(
                            AccountClassificationAssignment.classification_id == classification_id,
                            AccountClassificationAssignment.account_id.in_(account_ids)  # 限制到当前账户
                        )
                        .count()
                    )

                    log_info(
                        f"为分类 {classification_id} 添加新分配记录: {len(new_assignments)} 条，实际写入: {actual_count} 条",
                        module="account_classification",
                        classification_id=classification_id,
                        added_count=len(new_assignments),
                        actual_count=actual_count,
                        account_ids=account_ids
                    )
                except Exception as e:
                    log_error(
                        f"批量插入分配记录失败: {e}",
                        module="account_classification",
                        classification_id=classification_id,
                        error=str(e)
                    )
                    db.session.rollback()
                    raise

            return len(new_assignments)

        except Exception as e:
            log_error(f"批量添加分类失败: {e}", module="account_classification")
            db.session.rollback()
            return 0

    def _cleanup_all_old_assignments(self) -> None:
        """清理所有旧的分配记录，确保数据一致性"""
        try:
            # 删除所有分配记录
            deleted_count = db.session.query(AccountClassificationAssignment).delete()
            
            if deleted_count > 0:
                log_info(
                    f"清理所有旧分配记录: {deleted_count} 条",
                    module="account_classification",
                    deleted_count=deleted_count
                )
            
            db.session.commit()
            
        except Exception as e:
            log_error(f"清理旧分配记录失败: {e}", module="account_classification")
            db.session.rollback()
            raise


    def _log_performance_stats(
        self, duration: float, total_accounts: int, total_rules: int, result: dict[str, Any]
    ) -> None:
        """记录性能统计"""
        accounts_per_second = total_accounts / duration if duration > 0 else 0

        log_info(
            "优化后的自动分类性能统计",
            module="account_classification",
            duration=f"{duration:.2f}秒",
            total_accounts=total_accounts,
            total_rules=total_rules,
            accounts_per_second=f"{accounts_per_second:.2f}",
            total_classifications_added=result.get("total_classifications_added", 0),
            total_matches=result.get("total_matches", 0),
            failed_count=result.get("failed_count", 0),
        )


    def _rules_to_cache_data(self, rules: list[ClassificationRule]) -> list[dict[str, Any]]:
        """将规则对象转换为缓存数据"""
        try:
            rules_data = []
            for rule in rules:
                rule_data = {
                    "id": rule.id,
                    "rule_name": rule.rule_name,
                    "db_type": rule.db_type,
                    "rule_expression": rule.rule_expression,
                    "is_active": rule.is_active,
                    "classification_id": rule.classification_id,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                    "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                }
                rules_data.append(rule_data)
            return rules_data
        except Exception as e:
            log_error(f"转换规则数据失败: {e}", module="account_classification")
            return []

    def _rules_from_cache_data(self, rules_data: list[dict[str, Any]]) -> list[ClassificationRule]:
        """将缓存数据转换为规则对象"""
        try:
            rules = []
            for rule_data in rules_data:
                # 创建规则对象（简化版本，只包含必要字段）
                rule = ClassificationRule()
                rule.id = rule_data.get("id")
                rule.rule_name = rule_data.get("rule_name")
                rule.db_type = rule_data.get("db_type")
                rule.rule_expression = rule_data.get("rule_expression")
                rule.is_active = rule_data.get("is_active", True)
                rule.classification_id = rule_data.get("classification_id")
                
                # 解析时间字段
                if rule_data.get("created_at"):
                    from app.utils.time_utils import time_utils
                    rule.created_at = time_utils.to_utc(rule_data["created_at"])
                if rule_data.get("updated_at"):
                    rule.updated_at = time_utils.to_utc(rule_data["updated_at"])
                
                rules.append(rule)
            return rules
        except Exception as e:
            log_error(f"从缓存数据创建规则失败: {e}", module="account_classification")
            return []

    def _accounts_to_cache_data(self, accounts: list[CurrentAccountSyncData]) -> list[dict[str, Any]]:
        """将账户对象转换为缓存数据"""
        try:
            accounts_data = []
            for account in accounts:
                account_data = {
                    "id": account.id,
                    "username": account.username,
                    "display_name": account.username,  # 使用username作为display_name
                    "is_locked": account.is_locked_display,  # 使用计算属性
                    "instance_id": account.instance_id,
                    "instance_name": account.instance.name if account.instance else None,
                    "instance_host": account.instance.host if account.instance else None,
                    "db_type": account.instance.db_type if account.instance else None,
                    "permissions": account.get_permissions_by_db_type(),
                    "roles": [],  # CurrentAccountSyncData没有roles字段
                    "sync_time": account.sync_time.isoformat() if account.sync_time else None,
                    "last_sync_time": account.last_sync_time.isoformat() if account.last_sync_time else None,
                    "last_change_time": account.last_change_time.isoformat() if account.last_change_time else None,
                }
                accounts_data.append(account_data)
            return accounts_data
        except Exception as e:
            log_error(f"转换账户数据失败: {e}", module="account_classification")
            return []


    def invalidate_cache(self) -> bool:
        """清除分类相关缓存"""
        try:
            if cache_manager:
                # 清除所有分类缓存
                cache_manager.invalidate_classification_cache()
                # 清除按数据库类型分组的缓存
                cache_manager.invalidate_all_db_type_cache()
                log_info("分类缓存已清除", module="account_classification")
                return True
            return False
        except Exception as e:
            log_error(f"清除分类缓存失败: {e}", module="account_classification")
            return False

    def invalidate_db_type_cache(self, db_type: str) -> bool:
        """清除特定数据库类型的缓存"""
        try:
            if cache_manager:
                cache_manager.invalidate_db_type_cache(db_type)
                log_info(f"数据库类型 {db_type} 缓存已清除", module="account_classification")
                return True
            return False
        except Exception as e:
            log_error(f"清除数据库类型 {db_type} 缓存失败: {e}", module="account_classification")
            return False

    def get_rule_matched_accounts_count(self, rule_id: int) -> int:
        """获取规则匹配的账户数量（重新评估规则）"""
        try:
            from app.models.account_classification import ClassificationRule
            from app.models.current_account_sync_data import CurrentAccountSyncData

            # 获取规则
            rule = ClassificationRule.query.get(rule_id)
            if not rule:
                return 0

            # 获取所有活跃的账户
            accounts = (
                CurrentAccountSyncData.query.join(Instance, CurrentAccountSyncData.instance_id == Instance.id)
                .join(InstanceAccount, CurrentAccountSyncData.instance_account)
                .filter(
                    Instance.is_active.is_(True),
                    Instance.deleted_at.is_(None),
                    InstanceAccount.is_active.is_(True),
                    Instance.db_type == rule.db_type,
                )
                .all()
            )

            # 重新评估规则，统计匹配的账户数量
            matched_count = 0
            for account in accounts:
                if self._evaluate_rule(account, rule):
                    matched_count += 1

            return matched_count

        except Exception as e:
            log_error(f"获取规则匹配账户数量失败: {str(e)}", module="account_classification")
            return 0


# 全局实例
account_classification_service = AccountClassificationService()
