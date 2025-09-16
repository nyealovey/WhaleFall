"""
泰摸鱼吧 - 优化后的账户分类管理服务
支持全量重新分类、按规则逐个处理、多分类支持
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Set

from app.utils.time_utils import time_utils

from app import db
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance
from app.services.classification_batch_service import ClassificationBatchService
from app.utils.structlog_config import log_error, log_info, log_warning


class OptimizedAccountClassificationService:
    """优化后的账户分类管理服务"""

    def __init__(self) -> None:
        """初始化优化后的账户分类服务"""
        self.batch_id = None

    def auto_classify_accounts_optimized(
        self,
        instance_id: int = None,
        batch_type: str = "manual",
        created_by: int = None,
    ) -> Dict[str, Any]:
        """
        优化后的自动分类账户 - 全量重新分类
        
        Args:
            instance_id: 实例ID，None表示所有实例
            batch_type: 批次类型
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

            # 3. 创建批次记录
            self.batch_id = ClassificationBatchService.create_batch(
                batch_type=batch_type,
                created_by=created_by,
                total_rules=len(rules),
                active_rules=len(rules),
            )

            log_info(
                "开始优化后的自动分类",
                module="account_classification",
                batch_id=self.batch_id,
                total_rules=len(rules),
                total_accounts=len(accounts),
                instance_id=instance_id,
            )

            # 4. 全量重新分类
            result = self._full_reclassify_accounts(accounts, rules)

            # 5. 完成批次
            ClassificationBatchService.complete_batch(
                self.batch_id,
                status="completed",
                batch_details=result,
            )

            # 6. 性能监控
            duration = time.time() - start_time
            self._log_performance_stats(duration, len(accounts), len(rules), result)

            return {
                "success": True,
                "message": "自动分类完成",
                "batch_id": self.batch_id,
                **result,
            }

        except Exception as e:
            if self.batch_id:
                ClassificationBatchService.complete_batch(
                    self.batch_id, status="failed", error_message=str(e)
                )
            log_error(f"优化后的自动分类失败: {e}", module="account_classification")
            return {"success": False, "error": f"自动分类失败: {str(e)}"}

    def _get_rules_sorted_by_priority(self) -> List[ClassificationRule]:
        """获取按优先级排序的规则"""
        try:
            rules = (
                ClassificationRule.query.filter_by(is_active=True)
                .join(AccountClassification)
                .order_by(
                    AccountClassification.priority.desc(),
                    ClassificationRule.created_at.asc(),
                )
                .all()
            )
            return rules
        except Exception as e:
            log_error(f"获取规则失败: {e}", module="account_classification")
            return []

    def _get_accounts_to_classify(self, instance_id: int = None) -> List[CurrentAccountSyncData]:
        """获取需要分类的账户"""
        try:
            query = (
                CurrentAccountSyncData.query.join(Instance)
                .filter(
                    Instance.is_active == True,
                    Instance.deleted_at.is_(None),
                    CurrentAccountSyncData.is_deleted == False,
                )
            )
            
            if instance_id:
                query = query.filter(CurrentAccountSyncData.instance_id == instance_id)

            return query.all()
        except Exception as e:
            log_error(f"获取账户失败: {e}", module="account_classification")
            return []

    def _full_reclassify_accounts(
        self, accounts: List[CurrentAccountSyncData], rules: List[ClassificationRule]
    ) -> Dict[str, Any]:
        """全量重新分类账户"""
        try:
            # 1. 清除所有现有分类分配
            self._clear_all_classifications(accounts)

            # 2. 按规则逐个处理
            total_classifications_added = 0
            total_matches = 0
            failed_count = 0
            errors = []

            for rule in rules:
                try:
                    # 获取匹配该规则的账户
                    matched_accounts = self._find_accounts_matching_rule(rule, accounts)
                    
                    if matched_accounts:
                        # 批量添加分类
                        added_count = self._add_classification_to_accounts_batch(
                            matched_accounts, rule.classification_id
                        )
                        
                        total_classifications_added += added_count
                        total_matches += len(matched_accounts)
                        
                        log_info(
                            f"规则 {rule.rule_name} 处理完成",
                            module="account_classification",
                            rule_id=rule.id,
                            matched_accounts=len(matched_accounts),
                            added_classifications=added_count,
                            batch_id=self.batch_id,
                        )

                except Exception as e:
                    failed_count += 1
                    error_msg = f"规则 {rule.rule_name} 处理失败: {str(e)}"
                    errors.append(error_msg)
                    log_error(
                        error_msg,
                        module="account_classification",
                        rule_id=rule.id,
                        batch_id=self.batch_id,
                    )

            # 3. 更新账户的最后分类时间
            self._update_accounts_classification_time(accounts)

            return {
                "total_accounts": len(accounts),
                "total_rules": len(rules),
                "classified_accounts": len(set(acc.id for acc in accounts)),
                "total_classifications_added": total_classifications_added,
                "total_matches": total_matches,
                "failed_count": failed_count,
                "errors": errors,
            }

        except Exception as e:
            log_error(f"全量重新分类失败: {e}", module="account_classification")
            raise

    def _clear_all_classifications(self, accounts: List[CurrentAccountSyncData]) -> None:
        """清除所有现有分类分配"""
        try:
            account_ids = [account.id for account in accounts]
            
            # 批量更新，将现有分类分配标记为非活跃
            AccountClassificationAssignment.query.filter(
                AccountClassificationAssignment.account_id.in_(account_ids),
                AccountClassificationAssignment.is_active == True,
            ).update(
                {
                    "is_active": False,
                    "updated_at": time_utils.now(),
                },
                synchronize_session=False,
            )
            
            db.session.commit()
            
            log_info(
                f"已清除 {len(account_ids)} 个账户的现有分类",
                module="account_classification",
                batch_id=self.batch_id,
            )

        except Exception as e:
            log_error(f"清除分类失败: {e}", module="account_classification")
            db.session.rollback()
            raise

    def _find_accounts_matching_rule(
        self, rule: ClassificationRule, accounts: List[CurrentAccountSyncData]
    ) -> List[CurrentAccountSyncData]:
        """查找匹配规则的账户"""
        matched_accounts = []
        
        for account in accounts:
            # 检查数据库类型是否匹配
            if account.instance.db_type != rule.db_type:
                continue
                
            # 评估规则
            if self._evaluate_rule(account, rule):
                matched_accounts.append(account)
        
        return matched_accounts

    def evaluate_rule(self, rule: ClassificationRule, account: CurrentAccountSyncData) -> bool:
        """评估规则是否匹配账户（公共方法）"""
        return self._evaluate_rule(account, rule)

    def _evaluate_rule(self, account: CurrentAccountSyncData, rule: ClassificationRule) -> bool:
        """评估规则是否匹配账户"""
        try:
            rule_expression = rule.get_rule_expression()
            if not rule_expression:
                return self._evaluate_legacy_rule(account, rule)

            # 根据规则类型进行不同的匹配逻辑
            if rule_expression.get("type") == "mysql_permissions":
                return self._evaluate_mysql_rule(account, rule_expression)
            elif rule_expression.get("type") == "sqlserver_permissions":
                return self._evaluate_sqlserver_rule(account, rule_expression)
            elif rule_expression.get("type") == "postgresql_permissions":
                return self._evaluate_postgresql_rule(account, rule_expression)
            elif rule_expression.get("type") == "oracle_permissions":
                return self._evaluate_oracle_rule(account, rule_expression)
            
            return False

        except Exception as e:
            log_error(f"评估规则失败: {e}", module="account_classification")
            return False

    def _evaluate_mysql_rule(self, account: CurrentAccountSyncData, rule_expression: Dict) -> bool:
        """评估MySQL规则"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            operator = rule_expression.get("operator", "OR").upper()

            # 检查全局权限
            required_global = rule_expression.get("global_privileges", [])
            if required_global:
                actual_global = permissions.get("global_privileges", [])
                if isinstance(actual_global, list):
                    actual_global_set = set(actual_global)
                else:
                    actual_global_set = set([p["privilege"] for p in actual_global if p.get("granted", False)])

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
                if isinstance(actual_global, list):
                    actual_global_set = set(actual_global)
                else:
                    actual_global_set = set([p["privilege"] for p in actual_global if p.get("granted", False)])

                if any(perm in actual_global_set for perm in exclude_global):
                    return False

            return True

        except Exception as e:
            log_error(f"评估MySQL规则失败: {e}", module="account_classification")
            return False

    def _evaluate_sqlserver_rule(self, account: CurrentAccountSyncData, rule_expression: Dict) -> bool:
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

            # 根据操作符决定匹配逻辑
            if not match_results:
                return True

            if operator == "AND":
                return all(match_results)
            else:
                return any(match_results)

        except Exception as e:
            log_error(f"评估SQL Server规则失败: {e}", module="account_classification")
            return False

    def _evaluate_postgresql_rule(self, account: CurrentAccountSyncData, rule_expression: Dict) -> bool:
        """评估PostgreSQL规则"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            # 检查角色属性权限
            required_role_attrs = rule_expression.get("role_attributes", [])
            for required_attr in required_role_attrs:
                role_attrs = permissions.get("role_attributes", {})
                if not role_attrs.get(required_attr, False):
                    return False

            return True

        except Exception as e:
            log_error(f"评估PostgreSQL规则失败: {e}", module="account_classification")
            return False

    def _evaluate_oracle_rule(self, account: CurrentAccountSyncData, rule_expression: Dict) -> bool:
        """评估Oracle规则"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            # 检查角色
            required_roles = rule_expression.get("roles", [])
            if required_roles:
                account_roles = permissions.get("oracle_roles", [])
                for required_role in required_roles:
                    if required_role not in account_roles:
                        return False

            # 检查系统权限
            required_system_perms = rule_expression.get("system_privileges", [])
            if required_system_perms:
                account_system_perms = permissions.get("system_privileges", [])
                for required_perm in required_system_perms:
                    if required_perm not in account_system_perms:
                        return False

            return True

        except Exception as e:
            log_error(f"评估Oracle规则失败: {e}", module="account_classification")
            return False

    def _evaluate_legacy_rule(self, account: CurrentAccountSyncData, rule: ClassificationRule) -> bool:
        """评估旧格式规则（字符串格式）"""
        try:
            permissions = account.get_permissions_by_db_type()
            if not permissions:
                return False

            rule_expression = rule.rule_expression

            if rule.db_type == "sqlserver":
                if rule_expression == "server_roles.sysadmin":
                    server_roles = permissions.get("server_roles", [])
                    return isinstance(server_roles, list) and "sysadmin" in server_roles

            elif rule.db_type == "mysql":
                if rule_expression == "global_privileges.SUPER":
                    global_privileges = permissions.get("global_privileges", [])
                    return isinstance(global_privileges, list) and "SUPER" in global_privileges

            elif rule.db_type == "postgresql":
                if rule_expression == "role_attributes.CREATEROLE":
                    role_attributes = permissions.get("role_attributes", [])
                    return isinstance(role_attributes, list) and "CREATEROLE" in role_attributes

            elif rule.db_type == "oracle":
                if rule_expression == "system_privileges.GRANT ANY PRIVILEGE":
                    system_privileges = permissions.get("system_privileges", [])
                    return isinstance(system_privileges, list) and "GRANT ANY PRIVILEGE" in system_privileges

            return False

        except Exception as e:
            log_error(f"评估旧格式规则失败: {e}", module="account_classification")
            return False

    def _add_classification_to_accounts_batch(
        self, matched_accounts: List[CurrentAccountSyncData], classification_id: int
    ) -> int:
        """批量添加分类到账户"""
        try:
            if not matched_accounts:
                return 0

            # 获取账户ID列表
            account_ids = [account.id for account in matched_accounts]

            # 查询已存在的分类分配（包括所有批次）
            existing_assignments = db.session.query(AccountClassificationAssignment.account_id).filter(
                AccountClassificationAssignment.account_id.in_(account_ids),
                AccountClassificationAssignment.classification_id == classification_id,
                AccountClassificationAssignment.is_active == True,
            ).all()

            existing_account_ids = {assignment.account_id for assignment in existing_assignments}

            # 准备新的分类分配
            new_assignments = []
            for account in matched_accounts:
                if account.id not in existing_account_ids:
                    new_assignments.append({
                        "account_id": account.id,
                        "classification_id": classification_id,
                        "assigned_by": None,
                        "assignment_type": "auto",
                        "notes": None,
                        "batch_id": self.batch_id,
                        "is_active": True,
                        "created_at": time_utils.now(),
                        "updated_at": time_utils.now(),
                    })

            # 批量插入
            if new_assignments:
                db.session.bulk_insert_mappings(AccountClassificationAssignment, new_assignments)
                db.session.commit()
                
                log_info(
                    f"批量添加分类完成",
                    module="account_classification",
                    classification_id=classification_id,
                    added_count=len(new_assignments),
                    batch_id=self.batch_id,
                )

            return len(new_assignments)

        except Exception as e:
            log_error(f"批量添加分类失败: {e}", module="account_classification")
            db.session.rollback()
            return 0

    def _update_accounts_classification_time(self, accounts: List[CurrentAccountSyncData]) -> None:
        """更新账户的最后分类时间"""
        # 注意：不再更新last_classified_at和last_classification_batch_id字段
        # 这些字段在数据库模型中不存在，已移除相关更新操作
        pass

    def _log_performance_stats(
        self, duration: float, total_accounts: int, total_rules: int, result: Dict[str, Any]
    ) -> None:
        """记录性能统计"""
        accounts_per_second = total_accounts / duration if duration > 0 else 0
        
        log_info(
            "优化后的自动分类性能统计",
            module="account_classification",
            batch_id=self.batch_id,
            duration=f"{duration:.2f}秒",
            total_accounts=total_accounts,
            total_rules=total_rules,
            accounts_per_second=f"{accounts_per_second:.2f}",
            total_classifications_added=result.get("total_classifications_added", 0),
            total_matches=result.get("total_matches", 0),
            failed_count=result.get("failed_count", 0),
        )

    def classify_account(
        self,
        account_id: int,
        classification_id: int,
        assignment_type: str = "manual",
        assigned_by: int = None,
        notes: str = None,
        batch_id: str = None,
        skip_log: bool = False,
    ) -> Dict[str, Any]:
        """为账户分配分类"""
        try:
            account = CurrentAccountSyncData.query.get(account_id)
            if not account:
                return {"success": False, "error": "账户不存在"}

            classification = AccountClassification.query.get(classification_id)
            if not classification:
                return {"success": False, "error": "分类不存在"}

            # 检查是否已有该账户和分类的组合记录（包括非活跃的）
            existing_assignment = AccountClassificationAssignment.query.filter_by(
                account_id=account_id, classification_id=classification_id
            ).first()

            if existing_assignment:
                # 如果记录存在但非活跃，重新激活它
                if not existing_assignment.is_active:
                    existing_assignment.is_active = True
                    existing_assignment.assigned_by = assigned_by
                    existing_assignment.assignment_type = assignment_type
                    existing_assignment.notes = notes
                    existing_assignment.batch_id = batch_id
                    existing_assignment.updated_at = time_utils.now()
                    db.session.commit()
                    return {"success": True, "message": "账户分类分配已重新激活"}
                else:
                    return {"success": False, "error": "账户已分配该分类"}
            else:
                # 创建新的分配记录
                assignment = AccountClassificationAssignment(
                    account_id=account_id,
                    classification_id=classification_id,
                    assigned_by=assigned_by,
                    assignment_type=assignment_type,
                    notes=notes,
                    batch_id=batch_id,
                )
                db.session.add(assignment)
                db.session.commit()

                if not skip_log:
                    log_info(
                        "分配账户分类",
                        module="account_classification",
                        account_id=account_id,
                        classification_id=classification_id,
                        assignment_type=assignment_type,
                        assigned_by=assigned_by,
                    )

                return {"success": True, "message": "账户分类分配成功"}

        except Exception as e:
            db.session.rollback()
            log_error(f"分配账户分类失败: {str(e)}", module="account_classification")
            return {"success": False, "error": f"分配账户分类失败: {str(e)}"}

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
                CurrentAccountSyncData.query
                .join(Instance, CurrentAccountSyncData.instance_id == Instance.id)
                .filter(
                    Instance.is_active == True,
                    CurrentAccountSyncData.is_deleted == False,
                    Instance.deleted_at.is_(None),
                    Instance.db_type == rule.db_type,  # 只匹配相同数据库类型
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
optimized_account_classification_service = OptimizedAccountClassificationService()
