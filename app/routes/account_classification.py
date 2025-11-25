
"""
鲸落 - 账户分类管理路由
"""

import json

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app import db
from app.constants import HttpStatus
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.services.account_classification.auto_classify_service import (
    AutoClassifyError,
    AutoClassifyService,
)
from app.services.form_service.classification_form_service import ClassificationFormService
from app.services.form_service.classification_rule_form_service import ClassificationRuleFormService
from app.views.account_classification_form_view import (
    AccountClassificationFormView,
    ClassificationRuleFormView,
)
from app.services.statistics import account_statistics_service
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
_classification_form_service = ClassificationFormService()
_classification_rule_form_service = ClassificationRuleFormService()
_auto_classify_service = AutoClassifyService()


@account_classification_bp.route("/")
@login_required
@view_required
def index() -> str:
    """账户分类管理首页。

    Returns:
        渲染的账户分类管理页面。
    """
    # 传递颜色选项到模板
    color_options = ThemeColors.COLOR_MAP
    return render_template("accounts/account_classification/index.html", color_options=color_options)


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
    """获取所有账户分类。

    按优先级和创建时间排序，包含规则数量统计。

    Returns:
        (JSON 响应, HTTP 状态码)，包含分类列表。

    Raises:
        SystemError: 当获取失败时抛出。
    """
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
    """创建账户分类。

    Returns:
        (JSON 响应, HTTP 状态码)。

    Raises:
        ValidationError: 当表单验证失败时抛出。
    """
    payload = request.get_json() or {}
    result = _classification_form_service.upsert(payload)
    if not result.success or not result.data:
        raise ValidationError(result.message or "创建账户分类失败")
    classification = result.data

    return jsonify_unified_success(
        data={"classification": classification.to_dict()},
        message="账户分类创建成功",
        status=HttpStatus.CREATED,
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
    payload = request.get_json() or {}
    result = _classification_form_service.upsert(payload, classification)
    if not result.success or not result.data:
        raise ValidationError(result.message or "更新账户分类失败")
    classification = result.data

    return jsonify_unified_success(
        data={"classification": classification.to_dict()},
        message="账户分类更新成功",
    )


@account_classification_bp.route("/api/classifications/<int:classification_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def delete_classification(classification_id: int) -> tuple[Response, int]:
    """删除账户分类。

    系统分类不能删除。

    Args:
        classification_id: 分类 ID。

    Returns:
        (JSON 响应, HTTP 状态码)。

    Raises:
        ValidationError: 当尝试删除系统分类时抛出。
        NotFoundError: 当分类不存在时抛出。
        SystemError: 当删除失败时抛出。
    """
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
    """获取分类规则。

    支持按分类 ID 和数据库类型筛选。

    Returns:
        (JSON 响应, HTTP 状态码)，包含规则列表。

    Raises:
        SystemError: 当获取失败时抛出。

    Query Parameters:
        classification_id: 分类 ID 筛选，可选。
        db_type: 数据库类型筛选，可选。
    """
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

    result = []
    for rule in rules:
        result.append(
            {
                "id": rule.id,
                "rule_name": rule.rule_name,
                "classification_id": rule.classification_id,
                "classification_name": rule.classification.name if rule.classification else None,
                "db_type": rule.db_type,
                "rule_expression": rule.rule_expression,
                "is_active": rule.is_active,
                "matched_accounts_count": 0,
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


@account_classification_bp.route("/api/rules/stats")
@login_required
@view_required
def get_rule_stats() -> tuple[Response, int]:
    """获取规则命中统计"""
    rule_ids_param = request.args.get("rule_ids")
    rule_ids: list[int] | None = None

    if rule_ids_param:
        try:
            rule_ids = [
                int(rule_id)
                for rule_id in rule_ids_param.split(",")
                if rule_id.strip()
            ]
        except ValueError as exc:
            raise ValidationError("rule_ids 参数必须为整数ID，使用逗号分隔") from exc

    try:
        stats_map = account_statistics_service.fetch_rule_match_stats(rule_ids)
    except SystemError:
        raise
    except Exception as exc:
        log_error(f"获取规则命中统计失败: {exc}", module="account_classification")
        raise SystemError("获取规则命中统计失败") from exc

    stats_payload = [
        {"rule_id": rule_id, "matched_accounts_count": count}
        for rule_id, count in stats_map.items()
    ]
    return jsonify_unified_success(
        data={"rule_stats": stats_payload},
        message="规则命中统计获取成功",
    )


@account_classification_bp.route("/api/rules", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_rule() -> tuple[Response, int]:
    """创建分类规则。

    Returns:
        (JSON 响应, HTTP 状态码)。

    Raises:
        ValidationError: 当表单验证失败时抛出。
    """
    payload = request.get_json() or {}
    result = _classification_rule_form_service.upsert(payload)
    if not result.success or not result.data:
        raise ValidationError(result.message or "创建分类规则失败")
    rule = result.data

    return jsonify_unified_success(
        data={"rule_id": rule.id},
        message="分类规则创建成功",
        status=HttpStatus.CREATED,
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
    payload = request.get_json() or {}
    result = _classification_rule_form_service.upsert(payload, rule)
    if not result.success or not result.data:
        raise ValidationError(result.message or "更新分类规则失败")

    return jsonify_unified_success(message="分类规则更新成功")

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
    """自动分类账户 - 使用优化后的服务。

    根据分类规则自动为账户分配分类。

    Returns:
        (JSON 响应, HTTP 状态码)，包含分类结果统计。

    Raises:
        SystemError: 当自动分类失败时抛出。
    """
    data = request.get_json(silent=True) or {}
    created_by = current_user.id if current_user.is_authenticated else None

    try:
        result = _auto_classify_service.auto_classify(
            instance_id=data.get("instance_id"),
            created_by=created_by,
            use_optimized=data.get("use_optimized"),
        )
    except AutoClassifyError as exc:
        raise SystemError(str(exc)) from exc

    payload = result.to_payload()

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














# ---------------------------------------------------------------------------
# 表单路由（独立页面）
# ---------------------------------------------------------------------------
_classification_create_view = AccountClassificationFormView.as_view("classification_create_form")
_classification_create_view = login_required(create_required(require_csrf(_classification_create_view)))

account_classification_bp.add_url_rule(
    "/classifications/create",
    view_func=_classification_create_view,
    methods=["GET", "POST"],
    defaults={"resource_id": None},
)

_classification_edit_view = AccountClassificationFormView.as_view("classification_edit_form")
_classification_edit_view = login_required(update_required(require_csrf(_classification_edit_view)))

account_classification_bp.add_url_rule(
    "/classifications/<int:resource_id>/edit",
    view_func=_classification_edit_view,
    methods=["GET", "POST"],
)

_rule_create_view = ClassificationRuleFormView.as_view("classification_rule_create_form")
_rule_create_view = login_required(create_required(require_csrf(_rule_create_view)))

account_classification_bp.add_url_rule(
    "/rules/create",
    view_func=_rule_create_view,
    methods=["GET", "POST"],
    defaults={"resource_id": None},
)

_rule_edit_view = ClassificationRuleFormView.as_view("classification_rule_edit_form")
_rule_edit_view = login_required(update_required(require_csrf(_rule_edit_view)))

account_classification_bp.add_url_rule(
    "/rules/<int:resource_id>/edit",
    view_func=_rule_edit_view,
    methods=["GET", "POST"],
)


def _get_db_permissions(db_type: str) -> dict:
    """获取数据库权限列表。

    Args:
        db_type: 数据库类型。

    Returns:
        权限配置字典。
    """
    from app.models.permission_config import PermissionConfig

    # 从数据库获取权限配置
    return PermissionConfig.get_permissions_by_db_type(db_type)
