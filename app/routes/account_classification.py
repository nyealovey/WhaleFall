
"""
鲸落 - 账户分类管理路由
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
from app.constants.colors import ThemeColors
from app.utils.decorators import (
    create_required,
    delete_required,
    update_required,
    view_required,
)
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
account_classification_bp = Blueprint("account_classification", __name__)


@account_classification_bp.route("/")
@login_required
@view_required
def index() -> str:
    """账户分类管理首页"""
    # 传递颜色选项到模板
    color_options = ThemeColors.COLOR_MAP
    return render_template("accounts/account_classification.html", color_options=color_options)


@account_classification_bp.route("/rules-page")
@login_required
@view_required
def rules() -> str:
    """规则管理页面"""
    return render_template("account_classification/rules.html")


@account_classification_bp.route("/api/colors")
@login_required
@view_required
def get_color_options() -> "Response":
    """获取可用颜色选项"""
    try:
        return jsonify({
            "success": True,
            "data": {
                "colors": ThemeColors.COLOR_MAP,
                "choices": ThemeColors.get_color_choices()
            }
        })
    except Exception as e:
        log_error(f"获取颜色选项失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/classifications")
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
                    "color": classification.color_value,  # 返回实际颜色值
                    "color_key": classification.color,    # 保留颜色键名
                    "icon_name": classification.icon_name,
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


@account_classification_bp.route("/api/classifications", methods=["POST"])
@login_required
@create_required
def create_classification() -> "Response":
    """创建账户分类"""
    try:
        data = request.get_json()
        
        # 验证颜色
        color_key = data.get("color", "info")
        if not ThemeColors.is_valid_color(color_key):
            return jsonify({
                "success": False, 
                "error": f"无效的颜色选择: {color_key}"
            }), 400

        classification = AccountClassification(
            name=data["name"],
            description=data.get("description", ""),
            risk_level=data.get("risk_level", "medium"),
            color=color_key,  # 存储颜色键名
            icon_name=data.get("icon_name", "fa-tag"),
            priority=data.get("priority", 0),
            is_system=False,
        )

        db.session.add(classification)
        db.session.commit()

        return jsonify({
            "success": True,
            "classification": classification.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        log_error(f"创建账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/classifications/<int:classification_id>")
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
                    "color": classification.color_value,  # 返回实际颜色值
                    "color_key": classification.color,    # 保留颜色键名用于编辑
                    "icon_name": classification.icon_name,
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


@account_classification_bp.route("/api/classifications/<int:classification_id>", methods=["PUT"])
@login_required
@update_required
def update_classification(classification_id: int) -> "Response":
    """更新账户分类"""
    try:
        classification = AccountClassification.query.get_or_404(classification_id)
        data = request.get_json()
        
        # 验证颜色
        color_key = data.get("color", "info")
        if not ThemeColors.is_valid_color(color_key):
            return jsonify({
                "success": False, 
                "error": f"无效的颜色选择: {color_key}"
            }), 400

        classification.name = data["name"]
        classification.description = data.get("description", "")
        classification.risk_level = data.get("risk_level", "medium")
        classification.color = color_key  # 存储颜色键名
        classification.icon_name = data.get("icon_name", "fa-tag")
        classification.priority = data.get("priority", 0)

        db.session.commit()

        return jsonify({
            "success": True,
            "classification": classification.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        log_error(f"更新账户分类失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/classifications/<int:classification_id>", methods=["DELETE"])
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


@account_classification_bp.route("/api/rules/filter")
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


@account_classification_bp.route("/api/rules")
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


@account_classification_bp.route("/api/rules", methods=["POST"])
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

        # 清除分类缓存，确保新规则能被正确获取
        try:
            from app.services.account_classification_service import AccountClassificationService
            service = AccountClassificationService()
            service.invalidate_cache()
            log_info("规则创建后已清除分类缓存", module="account_classification", rule_id=rule.id, user_id=current_user.id)
        except Exception as cache_error:
            log_error(f"清除分类缓存失败: {cache_error}", module="account_classification", rule_id=rule.id)

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"创建分类规则失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["GET"])
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


@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["PUT"])
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

        # 清除分类缓存，确保规则更新后重新从数据库获取
        try:
            from app.services.account_classification_service import AccountClassificationService
            service = AccountClassificationService()
            service.invalidate_cache()
            log_info("规则更新后已清除分类缓存", module="account_classification", rule_id=rule_id, user_id=current_user.id)
        except Exception as cache_error:
            log_error(f"清除分类缓存失败: {cache_error}", module="account_classification", rule_id=rule_id)

        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        log_error(f"更新分类规则失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/rules/<int:rule_id>/matched-accounts", methods=["GET"])
@login_required
@view_required
def get_matched_accounts(rule_id: int) -> "Response":
    """获取规则匹配的账户（从数据库获取，支持分页）"""
    try:
        rule = ClassificationRule.query.get_or_404(rule_id)

        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        
        # 限制每页最大数量
        per_page = min(per_page, 100)

        # 从数据库获取已分配的账户，而不是实时计算
        from app.models.current_account_sync_data import CurrentAccountSyncData
        from app.models.instance import Instance
        from app.models.account_classification import AccountClassificationAssignment

        # 构建基础查询：通过分配表获取该分类下的所有活跃账户
        query = (
            db.session.query(CurrentAccountSyncData, Instance)
            .join(Instance, CurrentAccountSyncData.instance_id == Instance.id)
            .join(AccountClassificationAssignment, 
                  AccountClassificationAssignment.account_id == CurrentAccountSyncData.id)
            .filter(
                AccountClassificationAssignment.classification_id == rule.classification_id,
                AccountClassificationAssignment.is_active == True,
                Instance.db_type == rule.db_type,
                CurrentAccountSyncData.is_deleted.is_(False),
                Instance.is_active == True,
                Instance.deleted_at.is_(None)
            )
        )

        # 应用搜索过滤
        if search:
            search_lower = f"%{search.lower()}%"
            query = query.filter(
                db.or_(
                    CurrentAccountSyncData.username.ilike(search_lower),
                    Instance.name.ilike(search_lower),
                    Instance.host.ilike(search_lower)
                )
            )

        # 获取总数（用于分页）
        total = query.count()

        # 应用分页
        offset = (page - 1) * per_page
        results = query.offset(offset).limit(per_page).all()

        # 构建返回数据
        matched_accounts = []
        for account, instance in results:
            # 获取账户的所有分类信息
            account_classifications = []
            account_assignments = (
                AccountClassificationAssignment.query
                .filter_by(account_id=account.id, is_active=True)
                .join(AccountClassification, AccountClassificationAssignment.classification_id == AccountClassification.id)
                .all()
            )
            
            for assignment in account_assignments:
                account_classifications.append({
                    "id": assignment.classification.id,
                    "name": assignment.classification.name,
                    "color": assignment.classification.color,
                })

            matched_accounts.append({
                "id": account.id,
                "username": account.username,
                "display_name": account.username,  # 使用用户名作为显示名称
                "instance_name": instance.name,
                "instance_host": instance.host,
                "instance_environment": instance.environment or "unknown",
                "db_type": rule.db_type,
                "is_locked": account.is_locked_display,
                "classifications": account_classifications,
            })

        # 计算分页信息
        total_pages = (total + per_page - 1) // per_page

        return jsonify({
            "success": True, 
            "accounts": matched_accounts, 
            "rule_name": rule.rule_name,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        })

    except Exception as e:
        log_error(f"获取匹配账户失败: {e}", module="account_classification")
        return jsonify({"success": False, "error": str(e)})


@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["DELETE"])
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


@account_classification_bp.route("/api/auto-classify", methods=["POST"])
@login_required
@update_required
def auto_classify() -> "Response":
    """自动分类账户 - 使用优化后的服务"""
    try:
        data = request.get_json()
        instance_id = data.get("instance_id")
        use_optimized = data.get("use_optimized", True)  # 默认使用优化版本

        log_info(
            "开始自动分类账户",
            module="account_classification",
            instance_id=instance_id,
            use_optimized=use_optimized,
        )

        # 使用优化后的服务
        service = AccountClassificationService()
        result = service.auto_classify_accounts_optimized(
            instance_id=instance_id,
            created_by=current_user.id if current_user.is_authenticated else None,
        )

        if result.get("success"):
            log_info(
                f"自动分类完成: {result.get('message', '分类成功')}",
                module="account_classification",
                instance_id=instance_id,
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


@account_classification_bp.route("/api/assignments")
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


@account_classification_bp.route("/api/assignments/<int:assignment_id>", methods=["DELETE"])
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


@account_classification_bp.route("/api/permissions/<db_type>")
@login_required
@view_required
def get_permissions(db_type: str) -> "Response":
    """获取数据库权限列表"""
    try:
        permissions = _get_db_permissions(db_type)

        return jsonify({"success": True, "permissions": permissions})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})














def _get_db_permissions(db_type: str) -> dict:
    """获取数据库权限列表"""
    from app.models.permission_config import PermissionConfig

    # 从数据库获取权限配置
    return PermissionConfig.get_permissions_by_db_type(db_type)
