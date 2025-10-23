
"""
鲸落 - 账户分类管理路由
"""

import json

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app import db
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.services.account_classification_service import AccountClassificationService
from app.constants.colors import ThemeColors
from app.errors import SystemError, ValidationError
from app.utils.decorators import (
    create_required,
    delete_required,
    require_csrf,
    update_required,
    view_required,
)
from app.utils.response_utils import jsonify_unified_success
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
def get_color_options() -> tuple[Response, int]:
    """获取可用颜色选项"""
    try:
        data = {
            "colors": ThemeColors.COLOR_MAP,
            "choices": ThemeColors.get_color_choices(),
        }
    except Exception as exc:
        log_error(f"获取颜色选项失败: {exc}", module="account_classification")
        raise SystemError("获取颜色选项失败") from exc

    return jsonify_unified_success(data=data, message="颜色选项获取成功")


@account_classification_bp.route("/api/classifications")
@login_required
@view_required
def get_classifications() -> tuple[Response, int]:
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
    except Exception as exc:
        log_error(f"获取账户分类失败: {exc}", module="account_classification")
        raise SystemError("获取账户分类失败") from exc

    result: list[dict[str, object]] = []
    for classification in classifications:
        rules_count = ClassificationRule.query.filter_by(
            classification_id=classification.id, is_active=True
        ).count()

        result.append(
            {
                "id": classification.id,
                "name": classification.name,
                "description": classification.description,
                "risk_level": classification.risk_level,
                "color": classification.color_value,
                "color_key": classification.color,
                "icon_name": classification.icon_name,
                "priority": classification.priority,
                "is_system": classification.is_system,
                "rules_count": rules_count,
                "created_at": classification.created_at.isoformat() if classification.created_at else None,
                "updated_at": classification.updated_at.isoformat() if classification.updated_at else None,
            }
        )

    return jsonify_unified_success(data={"classifications": result}, message="账户分类获取成功")


@account_classification_bp.route("/api/classifications", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_classification() -> tuple[Response, int]:
    """创建账户分类"""
    data = request.get_json() or {}

    color_key = data.get("color", "info")
    if not ThemeColors.is_valid_color(color_key):
        raise ValidationError(f"无效的颜色选择: {color_key}")

    try:
        classification = AccountClassification(
            name=data["name"],
            description=data.get("description", ""),
            risk_level=data.get("risk_level", "medium"),
            color=color_key,
            icon_name=data.get("icon_name", "fa-tag"),
            priority=data.get("priority", 0),
            is_system=False,
        )
        db.session.add(classification)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(f"创建账户分类失败: {exc}", module="account_classification")
        raise SystemError("创建账户分类失败") from exc

    log_info(
        "创建账户分类成功",
        module="account_classification",
        classification_id=classification.id,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(
        data={"classification": classification.to_dict()},
        message="账户分类创建成功",
        status=201,
    )


@account_classification_bp.route("/api/classifications/<int:classification_id>")
@login_required
@view_required
def get_classification(classification_id: int) -> tuple[Response, int]:
    """获取单个账户分类"""
    classification = AccountClassification.query.get_or_404(classification_id)

    payload = {
        "id": classification.id,
        "name": classification.name,
        "description": classification.description,
        "risk_level": classification.risk_level,
        "color": classification.color_value,
        "color_key": classification.color,
        "icon_name": classification.icon_name,
        "priority": classification.priority,
        "is_system": classification.is_system,
        "created_at": classification.created_at.isoformat() if classification.created_at else None,
        "updated_at": classification.updated_at.isoformat() if classification.updated_at else None,
    }

    return jsonify_unified_success(data={"classification": payload}, message="账户分类获取成功")


@account_classification_bp.route("/api/classifications/<int:classification_id>", methods=["PUT"])
@login_required
@update_required
@require_csrf
def update_classification(classification_id: int) -> tuple[Response, int]:
    """更新账户分类"""
    classification = AccountClassification.query.get_or_404(classification_id)
    data = request.get_json() or {}

    color_key = data.get("color", "info")
    if not ThemeColors.is_valid_color(color_key):
        raise ValidationError(f"无效的颜色选择: {color_key}")

    classification.name = data["name"]
    classification.description = data.get("description", "")
    classification.risk_level = data.get("risk_level", "medium")
    classification.color = color_key
    classification.icon_name = data.get("icon_name", "fa-tag")
    classification.priority = data.get("priority", 0)

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(f"更新账户分类失败: {exc}", module="account_classification", classification_id=classification_id)
        raise SystemError("更新账户分类失败") from exc

    log_info(
        "更新账户分类成功",
        module="account_classification",
        classification_id=classification.id,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(
        data={"classification": classification.to_dict()},
        message="账户分类更新成功",
    )


@account_classification_bp.route("/api/classifications/<int:classification_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def delete_classification(classification_id: int) -> tuple[Response, int]:
    """删除账户分类"""
    classification = AccountClassification.query.get_or_404(classification_id)

    if classification.is_system:
        raise ValidationError("系统分类不能删除")

    try:
        db.session.delete(classification)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(f"删除账户分类失败: {exc}", module="account_classification", classification_id=classification_id)
        raise SystemError("删除账户分类失败") from exc

    log_info(
        "删除账户分类成功",
        module="account_classification",
        classification_id=classification_id,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message="账户分类删除成功")


@account_classification_bp.route("/api/rules/filter")
@login_required
@view_required
def get_rules() -> tuple[Response, int]:
    """获取分类规则"""
    classification_id = request.args.get("classification_id", type=int)
    db_type = request.args.get("db_type")

    try:
        query = ClassificationRule.query.filter_by(is_active=True)

        if classification_id:
            query = query.filter_by(classification_id=classification_id)

        if db_type:
            query = query.filter_by(db_type=db_type)

        rules = query.order_by(ClassificationRule.created_at.desc()).all()
    except Exception as exc:
        log_error(f"获取分类规则失败: {exc}", module="account_classification")
        raise SystemError("获取分类规则失败") from exc

    result = [
        {
            "id": rule.id,
            "rule_name": rule.rule_name,
            "classification_id": rule.classification_id,
            "classification_name": rule.classification.name if rule.classification else None,
            "db_type": rule.db_type,
            "rule_expression": rule.rule_expression,
            "is_active": rule.is_active,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }
        for rule in rules
    ]

    return jsonify_unified_success(data={"rules": result}, message="分类规则获取成功")


@account_classification_bp.route("/api/rules")
@login_required
@view_required
def list_rules() -> tuple[Response, int]:
    """获取所有规则列表（按数据库类型分组）"""
    try:
        rules = (
            ClassificationRule.query.filter_by(is_active=True)
            .order_by(ClassificationRule.created_at.desc())
            .all()
        )
    except Exception as exc:
        log_error(f"获取规则列表失败: {exc}", module="account_classification")
        raise SystemError("获取规则列表失败") from exc

    service = AccountClassificationService()
    result = []
    for rule in rules:
        matched_count = service.get_rule_matched_accounts_count(rule.id)
        result.append(
            {
                "id": rule.id,
                "rule_name": rule.rule_name,
                "classification_id": rule.classification_id,
                "classification_name": rule.classification.name if rule.classification else None,
                "db_type": rule.db_type,
                "rule_expression": rule.rule_expression,
                "is_active": rule.is_active,
                "matched_accounts_count": matched_count,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
        )

    rules_by_db_type: dict[str, list[dict[str, object]]] = {}
    for rule in result:
        db_type = rule.get("db_type") or "unknown"
        rules_by_db_type.setdefault(db_type, []).append(rule)

    return jsonify_unified_success(
        data={"rules_by_db_type": rules_by_db_type},
        message="分类规则列表获取成功",
    )


@account_classification_bp.route("/api/rules", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_rule() -> tuple[Response, int]:
    """创建分类规则"""
    data = request.get_json() or {}
    required_fields = ["rule_name", "classification_id", "db_type", "rule_expression"]
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"缺少必填字段: {field}")

    try:
        rule_expression_json = json.dumps(data["rule_expression"], ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError("规则表达式格式错误") from exc

    rule = ClassificationRule(
        rule_name=data["rule_name"],
        classification_id=data["classification_id"],
        db_type=data["db_type"],
        rule_expression=rule_expression_json,
        is_active=True,
    )

    try:
        db.session.add(rule)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(f"创建分类规则失败: {exc}", module="account_classification")
        raise SystemError("创建分类规则失败") from exc

    try:
        service = AccountClassificationService()
        service.invalidate_cache()
        log_info(
            "规则创建后已清除分类缓存",
            module="account_classification",
            rule_id=rule.id,
            operator_id=getattr(current_user, "id", None),
        )
    except Exception as cache_error:
        log_error(
            f"清除分类缓存失败: {cache_error}",
            module="account_classification",
            rule_id=rule.id,
        )

    return jsonify_unified_success(
        data={"rule_id": rule.id},
        message="分类规则创建成功",
        status=201,
    )


@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["GET"])
@login_required
@view_required
def get_rule(rule_id: int) -> tuple[Response, int]:
    """获取单个规则详情"""
    rule = ClassificationRule.query.get_or_404(rule_id)

    try:
        rule_expression_obj = json.loads(rule.rule_expression) if rule.rule_expression else {}
    except (json.JSONDecodeError, TypeError):
        rule_expression_obj = {}

    rule_dict = {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "classification_id": rule.classification_id,
        "classification_name": rule.classification.name if rule.classification else None,
        "db_type": rule.db_type,
        "rule_expression": rule_expression_obj,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }

    return jsonify_unified_success(data={"rule": rule_dict}, message="规则详情获取成功")


@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["PUT"])
@login_required
@update_required
@require_csrf
def update_rule(rule_id: int) -> tuple[Response, int]:
    """更新分类规则"""
    rule = ClassificationRule.query.get_or_404(rule_id)
    data = request.get_json() or {}

    required_fields = ["rule_name", "classification_id", "rule_expression"]
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"缺少必填字段: {field}")

    try:
        rule_expression_json = json.dumps(data["rule_expression"], ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError("规则表达式格式错误") from exc

    rule.rule_name = data["rule_name"]
    rule.classification_id = data["classification_id"]
    rule.rule_expression = rule_expression_json
    rule.db_type = data.get("db_type", rule.db_type)
    rule.is_active = data.get("is_active", True)

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(f"更新分类规则失败: {exc}", module="account_classification", rule_id=rule_id)
        raise SystemError("更新分类规则失败") from exc

    try:
        service = AccountClassificationService()
        service.invalidate_cache()
        log_info(
            "规则更新后已清除分类缓存",
            module="account_classification",
            rule_id=rule_id,
            operator_id=getattr(current_user, "id", None),
        )
    except Exception as cache_error:
        log_error(
            f"清除分类缓存失败: {cache_error}",
            module="account_classification",
            rule_id=rule_id,
        )

    return jsonify_unified_success(message="分类规则更新成功")


@account_classification_bp.route("/api/rules/<int:rule_id>/matched-accounts", methods=["GET"])
@login_required
@view_required
def get_matched_accounts(rule_id: int) -> tuple[Response, int]:
    """获取规则匹配的账户（从数据库获取，支持分页）"""
    rule = ClassificationRule.query.get_or_404(rule_id)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    search = request.args.get("search", "", type=str)

    from app.models.current_account_sync_data import CurrentAccountSyncData
    from app.models.instance import Instance
    from app.models.account_classification import AccountClassificationAssignment

    try:
        query = (
            db.session.query(CurrentAccountSyncData, Instance)
            .join(Instance, CurrentAccountSyncData.instance_id == Instance.id)
            .join(
                AccountClassificationAssignment,
                AccountClassificationAssignment.account_id == CurrentAccountSyncData.id,
            )
            .filter(
                AccountClassificationAssignment.classification_id == rule.classification_id,
                AccountClassificationAssignment.is_active.is_(True),
                Instance.db_type == rule.db_type,
                CurrentAccountSyncData.is_deleted.is_(False),
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
            )
        )

        if search:
            search_lower = f"%{search.lower()}%"
            query = query.filter(
                db.or_(
                    CurrentAccountSyncData.username.ilike(search_lower),
                    Instance.name.ilike(search_lower),
                    Instance.host.ilike(search_lower),
                )
            )

        total = query.count()
        offset = (page - 1) * per_page
        results = query.offset(offset).limit(per_page).all()
    except Exception as exc:
        log_error(f"获取匹配账户失败: {exc}", module="account_classification", rule_id=rule_id)
        raise SystemError("获取匹配账户失败") from exc

    matched_accounts: list[dict[str, object]] = []
    for account, instance in results:
        assignments = (
            AccountClassificationAssignment.query.filter_by(account_id=account.id, is_active=True)
            .join(AccountClassification, AccountClassificationAssignment.classification_id == AccountClassification.id)
            .all()
        )

        account_classifications = [
            {
                "id": assignment.classification.id,
                "name": assignment.classification.name,
                "color": assignment.classification.color,
            }
            for assignment in assignments
        ]

        matched_accounts.append(
            {
                "id": account.id,
                "username": account.username,
                "display_name": account.username,
                "instance_name": instance.name,
                "instance_host": instance.host,
                "instance_environment": instance.environment or "unknown",
                "db_type": rule.db_type,
                "is_locked": account.is_locked_display,
                "classifications": account_classifications,
            }
        )

    total_pages = (total + per_page - 1) // per_page
    pagination = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }

    return jsonify_unified_success(
        data={
            "accounts": matched_accounts,
            "rule_name": rule.rule_name,
            "pagination": pagination,
        },
        message="规则匹配账户获取成功",
    )


@account_classification_bp.route("/api/rules/<int:rule_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def delete_rule(rule_id: int) -> tuple[Response, int]:
    """删除分类规则"""
    rule = ClassificationRule.query.get_or_404(rule_id)

    try:
        db.session.delete(rule)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(f"删除分类规则失败: {exc}", module="account_classification", rule_id=rule_id)
        raise SystemError("删除分类规则失败") from exc

    log_info(
        "删除分类规则成功",
        module="account_classification",
        rule_id=rule_id,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message="分类规则删除成功")


@account_classification_bp.route("/api/auto-classify", methods=["POST"])
@login_required
@update_required
@require_csrf
def auto_classify() -> tuple[Response, int]:
    """自动分类账户 - 使用优化后的服务"""
    data = request.get_json(silent=True) or {}
    instance_id = data.get("instance_id")

    use_optimized = data.get("use_optimized", True)

    log_info(
        "开始自动分类账户",
        module="account_classification",
        instance_id=instance_id,
        use_optimized=use_optimized,
    )

    service = AccountClassificationService()
    try:
        result = service.auto_classify_accounts_optimized(
            instance_id=instance_id,
            created_by=current_user.id if current_user.is_authenticated else None,
        )
    except Exception as exc:
        log_error(
            "自动分类服务调用异常",
            module="account_classification",
            instance_id=instance_id,
            exception=exc,
        )
        raise SystemError("自动分类失败") from exc

    if not result.get("success", False):
        log_error(
            "自动分类失败",
            module="account_classification",
            instance_id=instance_id,
            error=result.get("error", "未知错误"),
            use_optimized=use_optimized,
        )
        raise SystemError(result.get("error", "自动分类失败"))

    log_info(
        "自动分类完成",
        module="account_classification",
        instance_id=instance_id,
        classified_count=result.get("classified_accounts", 0),
        total_classifications=result.get("total_classifications_added", 0),
        failed_count=result.get("failed_count", 0),
        use_optimized=use_optimized,
    )

    payload = {
        "classified_accounts": result.get("classified_accounts", 0),
        "total_classifications_added": result.get("total_classifications_added", 0),
        "failed_count": result.get("failed_count", 0),
        "message": result.get("message", "自动分类成功"),
    }

    return jsonify_unified_success(data=payload, message=payload["message"])


@account_classification_bp.route("/api/assignments")
@login_required
@view_required
def get_assignments() -> tuple[Response, int]:
    """获取账户分类分配"""
    try:
        assignments = (
            db.session.query(AccountClassificationAssignment, AccountClassification)
            .join(
                AccountClassification,
                AccountClassificationAssignment.classification_id == AccountClassification.id,
            )
            .filter(AccountClassificationAssignment.is_active.is_(True))
            .all()
        )
    except Exception as exc:
        log_error(f"获取账户分类分配失败: {exc}", module="account_classification")
        raise SystemError("获取账户分类分配失败") from exc

    result = [
        {
            "id": assignment.id,
            "account_id": assignment.account_id,
            "assigned_by": assignment.assigned_by,
            "classification_id": assignment.classification_id,
            "classification_name": classification.name,
            "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
        }
        for assignment, classification in assignments
    ]

    return jsonify_unified_success(data={"assignments": result}, message="账户分类分配获取成功")


@account_classification_bp.route("/api/assignments/<int:assignment_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def remove_assignment(assignment_id: int) -> tuple[Response, int]:
    """移除账户分类分配"""
    assignment = AccountClassificationAssignment.query.get_or_404(assignment_id)

    try:
        assignment.is_active = False
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(f"移除账户分类分配失败: {exc}", module="account_classification", assignment_id=assignment_id)
        raise SystemError("移除分配失败") from exc

    log_info(
        "移除账户分类分配成功",
        module="account_classification",
        assignment_id=assignment_id,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message="账户分类分配移除成功")


@account_classification_bp.route("/api/permissions/<db_type>")
@login_required
@view_required
def get_permissions(db_type: str) -> tuple[Response, int]:
    """获取数据库权限列表"""
    try:
        permissions = _get_db_permissions(db_type)
    except Exception as exc:
        log_error(f"获取权限配置失败: {exc}", module="account_classification", db_type=db_type)
        raise SystemError("获取数据库权限失败") from exc

    return jsonify_unified_success(data={"permissions": permissions}, message="数据库权限获取成功")














def _get_db_permissions(db_type: str) -> dict:
    """获取数据库权限列表"""
    from app.models.permission_config import PermissionConfig

    # 从数据库获取权限配置
    return PermissionConfig.get_permissions_by_db_type(db_type)
