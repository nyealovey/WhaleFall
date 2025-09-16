"""
泰摸鱼吧 - 账户分类管理路由
"""

import json
import time

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.services.account_classification_service import AccountClassificationService
from app.services.optimized_account_classification_service import OptimizedAccountClassificationService
from app.services.classification_batch_service import ClassificationBatchService
from app.utils.decorators import (
    create_required,
    delete_required,
    update_required,
    view_required,
)
from app.utils.structlog_config import log_error, log_info

account_classification_bp = Blueprint("account_classification", __name__, url_prefix="/account-classification")


@account_classification_bp.route("/")
@login_required
@view_required
def index() -> str:
    """账户分类管理首页"""
    return render_template("account_classification/index.html")


@account_classification_bp.route("/batches")
@login_required
@view_required
def batches() -> str:
    """自动分类批次管理页面"""
    return render_template("account_classification/batches.html")


@account_classification_bp.route("/rules-page")
@login_required
@view_required
def rules() -> str:
    """规则管理页面"""
    return render_template("account_classification/rules.html")


@account_classification_bp.route("/classifications")
@login_required
@view_required
def get_classifications() -> "Response":
    """获取所有账户分类"""
    try:
        classifications = (
            AccountClassification.query.filter_by(is_active=True)
            .order_by(
                AccountClassification.priority.desc(),
                AccountClassification.created_at.desc(),
            )
            .all()
        )

        result = []
        for classification in classifications:
            # 计算该分类的规则数量
            rules_count = ClassificationRule.query.filter_by(
                classification_id=classification.id, is_active=True
            ).count()

            result.append(
                {
                    "id": classification.id,
                    "name": classification.name,
                    "description": classification.description,
                    "risk_level": classification.risk_level,
                    "color": classification.color,
                    "priority": classification.priority,
                    "is_system": classification.is_system,
                    "rules_count": rules_count,
                    "created_at": (classification.created_at.isoformat() if classification.created_at else None),
                    "updated_at": (classification.updated_at.isoformat() if classification.updated_at else None),
                }
            )

        return jsonify({"success": True, "classifications": result})

    except Exception as e:
        log_error(f"获取账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/classifications", methods=["POST"])
@login_required
@create_required
def create_classification() -> "Response":
    """创建账户分类"""
    try:
        data = request.get_json()

        classification = AccountClassification(
            name=data["name"],
            description=data.get("description", ""),
            risk_level=data.get("risk_level", "medium"),
            color=data.get("color", "#6c757d"),
            priority=data.get("priority", 0),
            is_system=False,
        )

        db.session.add(classification)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "classification": {
                    "id": classification.id,
                    "name": classification.name,
                    "description": classification.description,
                    "risk_level": classification.risk_level,
                    "color": classification.color,
                    "priority": classification.priority,
                    "is_system": classification.is_system,
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        log_error(f"创建账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/classifications/<int:classification_id>")
@login_required
@view_required
def get_classification(classification_id: int) -> "Response":
    """获取单个账户分类"""
    try:
        classification = AccountClassification.query.get_or_404(classification_id)

        return jsonify(
            {
                "success": True,
                "classification": {
                    "id": classification.id,
                    "name": classification.name,
                    "description": classification.description,
                    "risk_level": classification.risk_level,
                    "color": classification.color,
                    "priority": classification.priority,
                    "is_system": classification.is_system,
                    "created_at": (classification.created_at.isoformat() if classification.created_at else None),
                    "updated_at": (classification.updated_at.isoformat() if classification.updated_at else None),
                },
            }
        )

    except Exception as e:
        log_error(f"获取账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/classifications/<int:classification_id>", methods=["PUT"])
@login_required
@update_required
def update_classification(classification_id: int) -> "Response":
    """更新账户分类"""
    try:
        classification = AccountClassification.query.get_or_404(classification_id)
        data = request.get_json()

        classification.name = data["name"]
        classification.description = data.get("description", "")
        classification.risk_level = data.get("risk_level", "medium")
        classification.color = data.get("color", "#6c757d")
        classification.priority = data.get("priority", 0)

        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"更新账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/classifications/<int:classification_id>", methods=["DELETE"])
@login_required
@delete_required
def delete_classification(classification_id: int) -> "Response":
    """删除账户分类"""
    try:
        classification = AccountClassification.query.get_or_404(classification_id)

        # 系统分类不能删除
        if classification.is_system:
            return jsonify({"success": False, "error": "系统分类不能删除"})

        db.session.delete(classification)
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"删除账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/rules/filter")
@login_required
@view_required
def get_rules() -> "Response":
    """获取分类规则"""
    try:
        classification_id = request.args.get("classification_id", type=int)
        db_type = request.args.get("db_type")

        query = ClassificationRule.query.filter_by(is_active=True)

        if classification_id:
            query = query.filter_by(classification_id=classification_id)

        if db_type:
            query = query.filter_by(db_type=db_type)

        rules = query.order_by(ClassificationRule.created_at.desc()).all()

        result = []
        for rule in rules:
            result.append(
                {
                    "id": rule.id,
                    "rule_name": rule.rule_name,
                    "classification_id": rule.classification_id,
                    "classification_name": (rule.classification.name if rule.classification else None),
                    "db_type": rule.db_type,
                    "rule_expression": rule.rule_expression,
                    "is_active": rule.is_active,
                    "created_at": (rule.created_at.isoformat() if rule.created_at else None),
                    "updated_at": (rule.updated_at.isoformat() if rule.updated_at else None),
                }
            )

        return jsonify({"success": True, "rules": result})

    except Exception as e:
        log_error(f"获取分类规则失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/rules")
@login_required
@view_required
def list_rules() -> "Response":
    """获取所有规则列表（按数据库类型分组）"""
    try:
        # 获取所有规则
        rules = ClassificationRule.query.filter_by(is_active=True).order_by(ClassificationRule.created_at.desc()).all()

        # 获取匹配账户数量
        service = AccountClassificationService()
        result = []
        for rule in rules:
            matched_count = service.get_rule_matched_accounts_count(rule.id)
            result.append(
                {
                    "id": rule.id,
                    "rule_name": rule.rule_name,
                    "classification_id": rule.classification_id,
                    "classification_name": (rule.classification.name if rule.classification else None),
                    "db_type": rule.db_type,
                    "rule_expression": rule.rule_expression,
                    "is_active": rule.is_active,
                    "matched_accounts_count": matched_count,
                    "created_at": (rule.created_at.isoformat() if rule.created_at else None),
                    "updated_at": (rule.updated_at.isoformat() if rule.updated_at else None),
                }
            )

        # 按数据库类型分组
        rules_by_db_type = {}
        for rule in result:
            db_type = rule.get("db_type", "unknown")
            if db_type not in rules_by_db_type:
                rules_by_db_type[db_type] = []
            rules_by_db_type[db_type].append(rule)

        return jsonify({"success": True, "rules_by_db_type": rules_by_db_type})

    except Exception as e:
        log_error(f"获取规则列表失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/rules", methods=["POST"])
@login_required
@create_required
def create_rule() -> "Response":
    """创建分类规则"""
    try:
        data = request.get_json()

        # 将规则表达式对象转换为JSON字符串
        rule_expression_json = json.dumps(data["rule_expression"], ensure_ascii=False)

        rule = ClassificationRule(
            rule_name=data["rule_name"],
            classification_id=data["classification_id"],
            db_type=data["db_type"],
            rule_expression=rule_expression_json,
            is_active=True,
        )

        db.session.add(rule)
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"创建分类规则失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/rules/<int:rule_id>", methods=["GET"])
@login_required
@view_required
def get_rule(rule_id: int) -> "Response":
    """获取单个规则详情"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)

        # 解析规则表达式JSON字符串为对象
        try:
            rule_expression_obj = json.loads(rule.rule_expression) if rule.rule_expression else {}
        except (json.JSONDecodeError, TypeError):
            rule_expression_obj = {}

        rule_dict = {
            "id": rule.id,
            "rule_name": rule.rule_name,
            "classification_id": rule.classification_id,
            "classification_name": (rule.classification.name if rule.classification else None),
            "db_type": rule.db_type,
            "rule_expression": rule_expression_obj,  # 返回解析后的对象
            "is_active": rule.is_active,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }

        return jsonify({"success": True, "rule": rule_dict})

    except Exception as e:
        log_error(f"获取规则详情失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/rules/<int:rule_id>", methods=["PUT"])
@login_required
@update_required
def update_rule(rule_id: int) -> "Response":
    """更新分类规则"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)
        data = request.get_json()

        # 将规则表达式对象转换为JSON字符串
        rule_expression_json = json.dumps(data["rule_expression"], ensure_ascii=False)

        rule.rule_name = data["rule_name"]
        rule.classification_id = data["classification_id"]
        rule.rule_expression = rule_expression_json
        rule.is_active = data.get("is_active", True)

        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"更新分类规则失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/rules/<int:rule_id>/matched-accounts", methods=["GET"])
@login_required
@view_required
def get_matched_accounts(rule_id: int) -> "Response":
    """获取规则匹配的账户"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)

        # 获取匹配的账户
        from app.services.account_classification_service import (
            AccountClassificationService,
        )

        classification_service = AccountClassificationService()

        # 获取所有账户
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.models.instance import Instance

        all_accounts = (
            CurrentAccountSyncData.query.join(Instance, CurrentAccountSyncData.instance_id == Instance.id)
            .filter(
                Instance.db_type == rule.db_type,
                CurrentAccountSyncData.is_deleted == False,
                Instance.is_active == True,
                Instance.deleted_at.is_(None),  # 排除已删除的实例
            )
            .all()
        )

        matched_accounts = []
        seen_accounts = set()  # 用于去重

        for account in all_accounts:
            # 检查账户是否匹配规则
            if classification_service.evaluate_rule(rule, account):
                # 对于MySQL，显示用户名@主机名
                if rule.db_type == "mysql" and account.instance and account.instance.host:
                    display_name = f"{account.username}@{account.instance.host}"
                    # 使用用户名@主机名作为唯一标识
                    unique_key = f"{account.username}@{account.instance.host}"
                else:
                    display_name = account.username
                    # 对于其他数据库类型，使用用户名作为唯一标识
                    unique_key = account.username

                # 避免重复显示
                if unique_key not in seen_accounts:
                    seen_accounts.add(unique_key)

                    # 获取账户的分类信息
                    account_classifications = []
                    if hasattr(account, "classifications") and account.classifications:
                        for classification in account.classifications:
                            account_classifications.append(
                                {
                                    "id": classification.id,
                                    "name": classification.name,
                                    "color": classification.color,
                                }
                            )

                    matched_accounts.append(
                        {
                            "id": account.id,
                            "username": account.username,  # 使用原始用户名
                            "display_name": display_name,  # 显示名称
                            "instance_name": (account.instance.name if account.instance else "未知实例"),
                            "instance_host": (account.instance.host if account.instance else "未知IP"),
                            "instance_environment": (account.instance.environment if account.instance else "unknown"),
                            "db_type": rule.db_type,
                            "is_locked": getattr(account, "is_locked", False),
                            "classifications": account_classifications,
                        }
                    )

        return jsonify({"success": True, "accounts": matched_accounts, "rule_name": rule.rule_name})

    except Exception as e:
        log_error(f"获取匹配账户失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/rules/<int:rule_id>", methods=["DELETE"])
@login_required
@delete_required
def delete_rule(rule_id: int) -> "Response":
    """删除分类规则"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)

        db.session.delete(rule)
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"删除分类规则失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/assign", methods=["POST"])
@login_required
@update_required
def assign_classification() -> "Response":
    """分配账户分类"""
    try:
        data = request.get_json()

        service = AccountClassificationService()
        result = service.classify_account(
            data["account_id"],
            data["classification_id"],
            "manual",
            current_user.id,
            None,  # notes
            None,  # batch_id (手动分配不需要批次ID)
        )

        return jsonify({"success": True, "assignment_id": result})

    except Exception as e:
        log_error(f"分配账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/auto-classify", methods=["POST"])
@login_required
@update_required
def auto_classify() -> "Response":
    """自动分类账户 - 使用优化后的服务"""
    try:
        data = request.get_json()
        instance_id = data.get("instance_id")
        batch_type = data.get("batch_type", "manual")  # 默认为手动操作
        use_optimized = data.get("use_optimized", True)  # 默认使用优化版本

        log_info(
            "开始自动分类账户",
            module="account_classification",
            instance_id=instance_id,
            batch_type=batch_type,
            use_optimized=use_optimized,
        )

        if use_optimized:
            # 使用优化后的服务
            service = OptimizedAccountClassificationService()
            result = service.auto_classify_accounts_optimized(
                instance_id=instance_id,
                batch_type=batch_type,
                created_by=current_user.id if current_user.is_authenticated else None,
            )
        else:
            # 使用原始服务
            service = AccountClassificationService()
            result = service.auto_classify_accounts(
                instance_id=instance_id,
                batch_type=batch_type,
                created_by=current_user.id if current_user.is_authenticated else None,
            )

        if result.get("success"):
            log_info(
                f"自动分类完成: {result.get('message', '分类成功')}",
                module="account_classification",
                instance_id=instance_id,
                batch_id=result.get("batch_id"),
                classified_count=result.get("classified_accounts", 0),
                total_classifications=result.get("total_classifications_added", 0),
                failed_count=result.get("failed_count", 0),
                use_optimized=use_optimized,
            )
        else:
            log_error(
                "自动分类失败",
                module="account_classification",
                instance_id=instance_id,
                batch_id=result.get("batch_id"),
                error=result.get("error", "未知错误"),
                use_optimized=use_optimized,
            )

        # 直接返回服务层的结果
        return jsonify(result)

    except Exception as e:
        log_error(
            "自动分类异常",
            module="account_classification",
            instance_id=instance_id,
            exception=e,
        )
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/auto-classify-optimized", methods=["POST"])
@login_required
@update_required
def auto_classify_optimized() -> "Response":
    """使用优化后的服务进行自动分类"""
    try:
        data = request.get_json()
        instance_id = data.get("instance_id")
        batch_type = data.get("batch_type", "manual")

        log_info(
            "开始优化后的自动分类",
            module="account_classification",
            instance_id=instance_id,
            batch_type=batch_type,
        )

        service = OptimizedAccountClassificationService()
        result = service.auto_classify_accounts_optimized(
            instance_id=instance_id,
            batch_type=batch_type,
            created_by=current_user.id if current_user.is_authenticated else None,
        )

        if result.get("success"):
            log_info(
                f"优化后的自动分类完成: {result.get('message', '分类成功')}",
                module="account_classification",
                instance_id=instance_id,
                batch_id=result.get("batch_id"),
                total_accounts=result.get("total_accounts", 0),
                total_classifications=result.get("total_classifications_added", 0),
                total_matches=result.get("total_matches", 0),
                failed_count=result.get("failed_count", 0),
            )
        else:
            log_error(
                "优化后的自动分类失败",
                module="account_classification",
                instance_id=instance_id,
                batch_id=result.get("batch_id"),
                error=result.get("error", "未知错误"),
            )

        return jsonify(result)

    except Exception as e:
        log_error(
            "优化后的自动分类异常",
            module="account_classification",
            instance_id=instance_id,
            exception=e,
        )
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/auto-classify-comparison", methods=["POST"])
@login_required
@update_required
def auto_classify_comparison() -> "Response":
    """比较原始服务和优化后服务的性能"""
    try:
        data = request.get_json()
        instance_id = data.get("instance_id")
        batch_type = data.get("batch_type", "comparison")

        log_info(
            "开始性能比较测试",
            module="account_classification",
            instance_id=instance_id,
        )

        results = {}

        # 测试原始服务
        try:
            start_time = time.time()
            original_service = AccountClassificationService()
            original_result = original_service.auto_classify_accounts(
                instance_id=instance_id,
                batch_type=f"{batch_type}_original",
                created_by=current_user.id if current_user.is_authenticated else None,
            )
            original_duration = time.time() - start_time
            
            results["original"] = {
                "success": original_result.get("success", False),
                "duration": original_duration,
                "batch_id": original_result.get("batch_id"),
                "classified_count": original_result.get("classified_count", 0),
                "failed_count": original_result.get("failed_count", 0),
            }
        except Exception as e:
            results["original"] = {
                "success": False,
                "error": str(e),
                "duration": 0,
            }

        # 测试优化后的服务
        try:
            start_time = time.time()
            optimized_service = OptimizedAccountClassificationService()
            optimized_result = optimized_service.auto_classify_accounts_optimized(
                instance_id=instance_id,
                batch_type=f"{batch_type}_optimized",
                created_by=current_user.id if current_user.is_authenticated else None,
            )
            optimized_duration = time.time() - start_time
            
            results["optimized"] = {
                "success": optimized_result.get("success", False),
                "duration": optimized_duration,
                "batch_id": optimized_result.get("batch_id"),
                "total_accounts": optimized_result.get("total_accounts", 0),
                "total_classifications": optimized_result.get("total_classifications_added", 0),
                "total_matches": optimized_result.get("total_matches", 0),
                "failed_count": optimized_result.get("failed_count", 0),
            }
        except Exception as e:
            results["optimized"] = {
                "success": False,
                "error": str(e),
                "duration": 0,
            }

        # 计算性能提升
        if results["original"]["success"] and results["optimized"]["success"]:
            original_duration = results["original"]["duration"]
            optimized_duration = results["optimized"]["duration"]
            
            if original_duration > 0:
                improvement = ((original_duration - optimized_duration) / original_duration) * 100
                results["performance_improvement"] = {
                    "time_saved": original_duration - optimized_duration,
                    "improvement_percentage": improvement,
                    "speed_ratio": original_duration / optimized_duration if optimized_duration > 0 else 0,
                }

        log_info(
            "性能比较测试完成",
            module="account_classification",
            instance_id=instance_id,
            results=results,
        )

        return jsonify({
            "success": True,
            "message": "性能比较测试完成",
            "comparison": results,
        })

    except Exception as e:
        log_error(
            "性能比较测试异常",
            module="account_classification",
            instance_id=instance_id,
            exception=e,
        )
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/assignments")
@login_required
@view_required
def get_assignments() -> "Response":
    """获取账户分类分配"""
    try:
        assignments = (
            db.session.query(AccountClassificationAssignment, AccountClassification)
            .join(
                AccountClassification,
                AccountClassificationAssignment.classification_id == AccountClassification.id,
            )
            .filter(AccountClassificationAssignment.is_active)
            .all()
        )

        result = []
        for assignment, classification in assignments:
            result.append(
                {
                    "id": assignment.id,
                    "account_id": assignment.assigned_by,
                    "classification_id": assignment.classification_id,
                    "classification_name": classification.name,
                    "assigned_at": (assignment.assigned_at.isoformat() if assignment.assigned_at else None),
                }
            )

        return jsonify({"success": True, "assignments": result})

    except Exception as e:
        log_error(f"获取账户分类分配失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/assignments/<int:assignment_id>", methods=["DELETE"])
@login_required
@delete_required
def remove_assignment(assignment_id: int) -> "Response":
    """移除账户分类分配"""
    try:
        assignment = AccountClassificationAssignment.query.get_or_404(assignment_id)
        assignment.is_active = False
        db.session.commit()

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"移除账户分类分配失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": f"移除分配失败: {str(e)}"})


@account_classification_bp.route("/permissions/<db_type>")
@login_required
@view_required
def get_permissions(db_type: str) -> "Response":
    """获取数据库权限列表"""
    try:
        permissions = _get_db_permissions(db_type)

        return jsonify({"success": True, "permissions": permissions})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/batches")
@login_required
@view_required
def batches_page() -> "Response":
    """自动分类记录页面"""
    return render_template("account_classification/batches.html")


@account_classification_bp.route("/api/batches")
@login_required
@view_required
def api_get_batches() -> "Response":
    """获取自动分类批次列表"""
    try:
        batch_type = request.args.get("batch_type")
        status = request.args.get("status")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        batches = ClassificationBatchService.get_batches(
            batch_type=batch_type, status=status, limit=limit, offset=offset
        )

        result = [batch.to_dict() for batch in batches]

        return jsonify({"success": True, "batches": result})

    except Exception as e:
        log_error("获取批次列表失败", module="account_classification", error=str(e))
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/batches/<batch_id>")
@login_required
@view_required
def api_get_batch(batch_id: str) -> "Response":
    """获取批次详情"""
    try:
        batch = ClassificationBatchService.get_batch(batch_id)
        if not batch:
            return jsonify({"success": False, "error": "批次不存在"})

        return jsonify({"success": True, "batch": batch.to_dict()})

    except Exception as e:
        log_error(
            "获取批次详情失败",
            module="account_classification",
            batch_id=batch_id,
            error=str(e),
        )
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/batches/<batch_id>/stats")
@login_required
@view_required
def get_batch_stats(batch_id: str) -> "Response":
    """获取批次统计信息"""
    try:
        stats = ClassificationBatchService.get_batch_stats(batch_id)
        if not stats:
            return jsonify({"success": False, "error": "批次不存在"})

        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        log_error(
            "获取批次统计失败",
            module="account_classification",
            batch_id=batch_id,
            error=str(e),
        )
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/batches/<batch_id>/matches")
@login_required
@view_required
def api_get_batch_matches(batch_id: str) -> "Response":
    """获取批次匹配详情"""
    try:
        import json

        from app.models.account_classification import (
            AccountClassification,
            AccountClassificationAssignment,
            ClassificationRule,
        )

        # 获取批次信息
        from app.models.classification_batch import ClassificationBatch
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.models.instance import Instance

        batch = ClassificationBatch.query.filter_by(batch_id=batch_id).first()
        if not batch:
            return jsonify({"success": False, "message": "批次不存在"})

        # 获取该批次的所有匹配记录
        assignments = (
            db.session.query(
                AccountClassificationAssignment,
                CurrentAccountSyncData,
                Instance,
                AccountClassification,
            )
            .join(
                CurrentAccountSyncData,
                AccountClassificationAssignment.account_id == CurrentAccountSyncData.id,
            )
            .join(Instance, CurrentAccountSyncData.instance_id == Instance.id)
            .join(
                AccountClassification,
                AccountClassificationAssignment.classification_id == AccountClassification.id,
            )
            .filter(
                AccountClassificationAssignment.batch_id == batch_id,
                AccountClassificationAssignment.is_active == True,  # 只显示正确匹配的记录
            )
            .all()
        )

        matches = []
        for assignment, account, instance, classification in assignments:
            # 获取该分类中与账户数据库类型匹配的规则
            rule = ClassificationRule.query.filter_by(
                classification_id=classification.id, db_type=instance.db_type, is_active=True
            ).first()
            # 解析账户权限信息 - 优先使用新的优化同步模型
            account_permissions = []

            # 首先尝试从CurrentAccountSyncData获取权限
            sync_data = CurrentAccountSyncData.query.filter_by(
                instance_id=instance.id,
                username=account.username,
                db_type=instance.db_type,
            ).first()

            if sync_data:
                try:
                    permissions_data = sync_data.get_permissions_by_db_type()
                    if isinstance(permissions_data, dict):
                        # 根据数据库类型解析权限
                        if instance.db_type == "mysql":
                            if permissions_data.get("global_privileges"):
                                for perm in permissions_data["global_privileges"]:
                                    account_permissions.append(
                                        {
                                            "category": "global_privileges",
                                            "name": (perm.get("privilege", perm) if isinstance(perm, dict) else perm),
                                            "description": "",
                                            "granted": True,
                                        }
                                    )
                            if permissions_data.get("database_privileges"):
                                for db_perm in permissions_data["database_privileges"]:
                                    if isinstance(db_perm, dict) and "privileges" in db_perm:
                                        for perm in db_perm["privileges"]:
                                            account_permissions.append(
                                                {
                                                    "category": "database_privileges",
                                                    "name": perm,
                                                    "description": f"数据库: {db_perm.get('database', '')}",
                                                    "granted": True,
                                                }
                                            )
                        elif instance.db_type == "postgresql":
                            if permissions_data.get("role_attributes"):
                                for attr in permissions_data["role_attributes"]:
                                    account_permissions.append(
                                        {
                                            "category": "role_attributes",
                                            "name": attr,
                                            "description": "",
                                            "granted": True,
                                        }
                                    )
                            if permissions_data.get("database_privileges"):
                                for db_perm in permissions_data["database_privileges"]:
                                    if isinstance(db_perm, dict) and "privileges" in db_perm:
                                        for perm in db_perm["privileges"]:
                                            account_permissions.append(
                                                {
                                                    "category": "database_privileges",
                                                    "name": perm,
                                                    "description": f"数据库: {db_perm.get('database', '')}",
                                                    "granted": True,
                                                }
                                            )
                        elif instance.db_type == "sqlserver":
                            if permissions_data.get("server_roles"):
                                for role in permissions_data["server_roles"]:
                                    account_permissions.append(
                                        {
                                            "category": "server_roles",
                                            "name": role,
                                            "description": "",
                                            "granted": True,
                                        }
                                    )
                            if permissions_data.get("database_roles"):
                                for db_name, roles in permissions_data["database_roles"].items():
                                    if isinstance(roles, list):
                                        for role in roles:
                                            account_permissions.append(
                                                {
                                                    "category": "database_roles",
                                                    "name": role,
                                                    "description": f"数据库: {db_name}",
                                                    "granted": True,
                                                }
                                            )
                        elif instance.db_type == "oracle":
                            if permissions_data.get("roles"):
                                for role in permissions_data["roles"]:
                                    account_permissions.append(
                                        {
                                            "category": "roles",
                                            "name": role,
                                            "description": "",
                                            "granted": True,
                                        }
                                    )
                            if permissions_data.get("system_privileges"):
                                for perm in permissions_data["system_privileges"]:
                                    account_permissions.append(
                                        {
                                            "category": "system_privileges",
                                            "name": perm,
                                            "description": "",
                                            "granted": True,
                                        }
                                    )
                except (json.JSONDecodeError, TypeError):
                    account_permissions = []

            # 权限数据只从CurrentAccountSyncData获取

            # 解析规则表达式，获取匹配的权限
            matched_permissions = []
            if rule:
                try:
                    # 尝试解析JSON格式的规则表达式
                    rule_expression = json.loads(rule.rule_expression)
                    if isinstance(rule_expression, dict):
                        # 处理新格式的规则表达式
                        if "permissions" in rule_expression:
                            rule_perms = rule_expression["permissions"]
                            if isinstance(rule_perms, list):
                                for perm in rule_perms:
                                    if isinstance(perm, dict) and "name" in perm:
                                        matched_permissions.append(
                                            {
                                                "name": perm["name"],
                                                "description": perm.get("description", ""),
                                                "category": perm.get("category", ""),
                                            }
                                        )
                                    elif isinstance(perm, str):
                                        matched_permissions.append(
                                            {
                                                "name": perm,
                                                "description": "",
                                                "category": "",
                                            }
                                        )
                        # 处理SQL Server特定格式
                        elif rule_expression.get("type") == "sqlserver_permissions":
                            server_roles = rule_expression.get("server_roles", [])
                            for role in server_roles:
                                matched_permissions.append(
                                    {
                                        "name": role,
                                        "description": f"服务器角色: {role}",
                                        "category": "server_roles",
                                    }
                                )
                            server_permissions = rule_expression.get("server_permissions", [])
                            for perm in server_permissions:
                                matched_permissions.append(
                                    {
                                        "name": perm,
                                        "description": f"服务器权限: {perm}",
                                        "category": "server_permissions",
                                    }
                                )
                        # 处理MySQL特定格式
                        elif rule_expression.get("type") == "mysql_permissions":
                            global_privileges = rule_expression.get("global_privileges", [])
                            for perm in global_privileges:
                                matched_permissions.append(
                                    {
                                        "name": perm,
                                        "description": f"全局权限: {perm}",
                                        "category": "global_privileges",
                                    }
                                )
                            database_privileges = rule_expression.get("database_privileges", [])
                            for perm in database_privileges:
                                matched_permissions.append(
                                    {
                                        "name": perm,
                                        "description": f"数据库权限: {perm}",
                                        "category": "database_privileges",
                                    }
                                )
                except (json.JSONDecodeError, TypeError):
                    # 处理旧格式的规则表达式（字符串格式）
                    rule_expression_str = rule.rule_expression
                    if rule_expression_str:
                        # 根据数据库类型和规则表达式解析匹配的权限
                        if instance.db_type == "sqlserver":
                            if rule_expression_str == "server_roles.sysadmin":
                                matched_permissions.append(
                                    {
                                        "name": "sysadmin",
                                        "description": "系统管理员角色",
                                        "category": "server_roles",
                                    }
                                )
                            elif rule_expression_str.startswith("server_permissions."):
                                perm_name = rule_expression_str.split(".", 1)[1]
                                matched_permissions.append(
                                    {
                                        "name": perm_name,
                                        "description": f"服务器权限: {perm_name}",
                                        "category": "server_permissions",
                                    }
                                )
                        elif instance.db_type == "mysql":
                            if rule_expression_str == "global_privileges.SUPER":
                                matched_permissions.append(
                                    {
                                        "name": "SUPER",
                                        "description": "超级用户权限",
                                        "category": "global_privileges",
                                    }
                                )
                        elif instance.db_type == "postgresql":
                            if rule_expression_str == "role_attributes.SUPERUSER":
                                matched_permissions.append(
                                    {
                                        "name": "SUPERUSER",
                                        "description": "超级用户属性",
                                        "category": "role_attributes",
                                    }
                                )
                            elif rule_expression_str == "role_attributes.CREATEROLE":
                                matched_permissions.append(
                                    {
                                        "name": "CREATEROLE",
                                        "description": "创建角色权限",
                                        "category": "role_attributes",
                                    }
                                )
                        elif instance.db_type == "oracle":
                            if rule_expression_str == "system_privileges.GRANT ANY PRIVILEGE":
                                matched_permissions.append(
                                    {
                                        "name": "GRANT ANY PRIVILEGE",
                                        "description": "授权任何权限",
                                        "category": "system_privileges",
                                    }
                                )

            matches.append(
                {
                    "assignment_id": assignment.id,
                    "account_id": account.id,
                    "account_name": account.username,
                    "account_host": account.instance.host if account.instance else None,
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "instance_type": instance.db_type,
                    "classification_id": classification.id,
                    "classification_name": classification.name,
                    "rule_id": rule.id if rule else None,
                    "rule_name": rule.rule_name if rule else "无规则",
                    "rule_description": (rule.rule_expression if rule else "无规则表达式"),
                    "matched_at": (batch.started_at.isoformat() if batch.started_at else None),
                    "confidence": getattr(assignment, "confidence_score", None),
                    "account_permissions": account_permissions,
                    "matched_permissions": matched_permissions,
                }
            )

        return jsonify({"success": True, "matches": matches})

    except Exception as e:
        log_error(
            "获取批次匹配详情失败",
            module="account_classification",
            batch_id=batch_id,
            error=str(e),
        )
        return jsonify({"success": False, "error": str(e)})


def _get_db_permissions(db_type: str) -> dict:
    """获取数据库权限列表"""
    from app.models.permission_config import PermissionConfig

    # 从数据库获取权限配置
    permissions = PermissionConfig.get_permissions_by_db_type(db_type)

    return permissions
