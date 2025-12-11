
"""Accounts 域:账户分类管理路由."""
import json
from itertools import groupby

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app import db
from app.constants import HttpStatus
from app.constants.colors import ThemeColors
from app.errors import ValidationError
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.models.permission_config import PermissionConfig
from app.services.account_classification.auto_classify_service import (
    AutoClassifyError,
    AutoClassifyService,
)
from app.services.form_service.classification_rule_service import ClassificationRuleFormService
from app.services.form_service.classification_service import ClassificationFormService
from app.services.statistics import account_statistics_service
from app.utils.decorators import (
    create_required,
    delete_required,
    require_csrf,
    update_required,
    view_required,
)
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.views.classification_forms import (
    AccountClassificationFormView,
    ClassificationRuleFormView,
)

# 创建蓝图
accounts_classifications_bp = Blueprint(
    "accounts_classifications",
    __name__,
    url_prefix="/accounts/classifications",
)
_classification_service = ClassificationFormService()
_classification_rule_service = ClassificationRuleFormService()
_auto_classify_service = AutoClassifyService()


@accounts_classifications_bp.route("/")
@login_required
@view_required
def index() -> str:
    """账户分类管理首页.

    Returns:
        渲染的账户分类管理页面.

    """
    # 传递颜色选项到模板
    color_options = ThemeColors.COLOR_MAP
    return render_template("accounts/account-classification/index.html", color_options=color_options)


@accounts_classifications_bp.route("/api/colors")
@login_required
@view_required
def get_color_options() -> tuple[Response, int]:
    """获取可用颜色选项.

    Returns:
        tuple[Response, int]: 统一成功 JSON 与 HTTP 状态码.

    """
    def _execute() -> tuple[Response, int]:
        data = {
            "colors": ThemeColors.COLOR_MAP,
            "choices": ThemeColors.get_color_choices(),
        }
        return jsonify_unified_success(data=data, message="颜色选项获取成功")

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="get_color_options",
        public_error="获取颜色选项失败",
        context={"color_count": len(ThemeColors.COLOR_MAP)},
    )


@accounts_classifications_bp.route("/api/classifications")
@login_required
@view_required
def get_classifications() -> tuple[Response, int]:
    """获取所有账户分类.

    按优先级和创建时间排序,包含规则数量统计.

    Returns:
        (JSON 响应, HTTP 状态码),包含分类列表.

    """
    def _execute() -> tuple[Response, int]:
        classifications = (
            AccountClassification.query.filter_by(is_active=True)
            .order_by(
                AccountClassification.priority.desc(),
                AccountClassification.created_at.desc(),
            )
            .all()
        )

        result: list[dict[str, object]] = [
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
                "rules_count": ClassificationRule.query.filter_by(
                    classification_id=classification.id,
                    is_active=True,
                ).count(),
                "created_at": classification.created_at.isoformat() if classification.created_at else None,
                "updated_at": classification.updated_at.isoformat() if classification.updated_at else None,
            }
            for classification in classifications
        ]

        return jsonify_unified_success(data={"classifications": result}, message="账户分类获取成功")

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="get_classifications",
        public_error="获取账户分类失败",
    )


@accounts_classifications_bp.route("/api/classifications", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_classification() -> tuple[Response, int]:
    """创建账户分类.

    Returns:
        (JSON 响应, HTTP 状态码).

    Raises:
        ValidationError: 当表单验证失败时抛出.

    """
    payload = request.get_json() or {}
    result = _classification_service.upsert(payload)
    if not result.success or not result.data:
        raise ValidationError(result.message or "创建账户分类失败")
    classification = result.data

    return jsonify_unified_success(
        data={"classification": classification.to_dict()},
        message="账户分类创建成功",
        status=HttpStatus.CREATED,
    )


@accounts_classifications_bp.route("/api/classifications/<int:classification_id>")
@login_required
@view_required
def get_classification(classification_id: int) -> tuple[Response, int]:
    """获取单个账户分类.

    Args:
        classification_id: 分类主键 ID.

    Returns:
        tuple[Response, int]: 包含分类详情的 JSON 以及状态码.

    """
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


@accounts_classifications_bp.route("/api/classifications/<int:classification_id>", methods=["PUT"])
@login_required
@update_required
@require_csrf
def update_classification(classification_id: int) -> tuple[Response, int]:
    """更新账户分类.

    Args:
        classification_id: 分类主键 ID.

    Returns:
        tuple[Response, int]: 更新后的分类 JSON 与状态码.

    Raises:
        ValidationError: 表单验证失败时抛出.

    """
    classification = AccountClassification.query.get_or_404(classification_id)
    payload = request.get_json() or {}
    result = _classification_service.upsert(payload, classification)
    if not result.success or not result.data:
        raise ValidationError(result.message or "更新账户分类失败")
    classification = result.data

    return jsonify_unified_success(
        data={"classification": classification.to_dict()},
        message="账户分类更新成功",
    )


@accounts_classifications_bp.route("/api/classifications/<int:classification_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def delete_classification(classification_id: int) -> tuple[Response, int]:
    """删除账户分类.

    系统分类不能删除.

    Args:
        classification_id: 分类 ID.

    Returns:
        (JSON 响应, HTTP 状态码).

    Raises:
        ValidationError: 当尝试删除系统分类时抛出.
        NotFoundError: 当分类不存在时抛出.

    """
    classification = AccountClassification.query.get_or_404(classification_id)

    def _execute() -> tuple[Response, int]:
        if classification.is_system:
            msg = "系统分类不能删除"
            raise ValidationError(msg)

        rule_count = ClassificationRule.query.filter_by(classification_id=classification_id).count()
        assignment_count = (
            AccountClassificationAssignment.query.filter_by(classification_id=classification_id, is_active=True).count()
        )
        if rule_count or assignment_count:
            return jsonify_unified_error_message(
                "分类仍在使用,请先迁移关联规则/账户后再删除",
                status_code=HttpStatus.CONFLICT,
                message_key="CLASSIFICATION_IN_USE",
                extra={
                    "rule_count": rule_count,
                    "assignment_count": assignment_count,
                },
            )

        with db.session.begin():
            db.session.delete(classification)

        log_info(
            "删除账户分类成功",
            module="accounts_classifications",
            classification_id=classification_id,
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(message="账户分类删除成功")

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="delete_classification",
        public_error="删除账户分类失败",
        context={"classification_id": classification_id},
    )


@accounts_classifications_bp.route("/api/rules/filter")
@login_required
@view_required
def get_rules() -> tuple[Response, int]:
    """获取分类规则.

    支持按分类 ID 和数据库类型筛选.

    Returns:
        (JSON 响应, HTTP 状态码),包含规则列表.

    Query Parameters:
        classification_id: 分类 ID 筛选,可选.
        db_type: 数据库类型筛选,可选.

    """
    classification_id = request.args.get("classification_id", type=int)
    db_type = request.args.get("db_type")

    def _execute() -> tuple[Response, int]:
        query = ClassificationRule.query.filter_by(is_active=True)

        if classification_id:
            query = query.filter_by(classification_id=classification_id)

        if db_type:
            query = query.filter_by(db_type=db_type)

        rules = query.order_by(ClassificationRule.created_at.desc()).all()

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

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="get_rules",
        public_error="获取分类规则失败",
        context={
            "classification_id": classification_id,
            "db_type": db_type,
        },
    )


@accounts_classifications_bp.route("/api/rules")
@login_required
@view_required
def list_rules() -> tuple[Response, int]:
    """获取所有规则列表(按数据库类型分组).

    Returns:
        tuple[Response, int]: 包含 `rules_by_db_type` 的 JSON 与状态码.

    """
    def _execute() -> tuple[Response, int]:
        rules = (
            ClassificationRule.query.filter_by(is_active=True)
            .order_by(ClassificationRule.created_at.desc())
            .all()
        )

        result = [
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
            for rule in rules
        ]

        sorted_rules = sorted(result, key=lambda item: item.get("db_type") or "unknown")
        rules_by_db_type: dict[str, list[dict[str, object]]] = {
            db_type: list(group)
            for db_type, group in groupby(
                sorted_rules,
                key=lambda item: item.get("db_type") or "unknown",
            )
        }

        return jsonify_unified_success(
            data={"rules_by_db_type": rules_by_db_type},
            message="分类规则列表获取成功",
        )

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="list_rules",
        public_error="获取规则列表失败",
    )


@accounts_classifications_bp.route("/api/rules/stats")
@login_required
@view_required
def get_rule_stats() -> tuple[Response, int]:
    """获取规则命中统计.

    Returns:
        tuple[Response, int]: 规则命中统计数据及状态码.

    Raises:
        ValidationError: `rule_ids` 参数格式错误时抛出.

    """
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
            msg = "rule_ids 参数必须为整数ID,使用逗号分隔"
            raise ValidationError(msg) from exc

    def _execute() -> tuple[Response, int]:
        stats_map = account_statistics_service.fetch_rule_match_stats(rule_ids)
        stats_payload = [
            {"rule_id": rule_id, "matched_accounts_count": count}
            for rule_id, count in stats_map.items()
        ]
        return jsonify_unified_success(
            data={"rule_stats": stats_payload},
            message="规则命中统计获取成功",
        )

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="get_rule_stats",
        public_error="获取规则命中统计失败",
        context={"rule_ids": rule_ids},
    )


@accounts_classifications_bp.route("/api/rules", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_rule() -> tuple[Response, int]:
    """创建分类规则.

    Returns:
        (JSON 响应, HTTP 状态码).

    Raises:
        ValidationError: 当表单验证失败时抛出.

    """
    payload = request.get_json() or {}
    result = _classification_rule_service.upsert(payload)
    if not result.success or not result.data:
        raise ValidationError(result.message or "创建分类规则失败")
    rule = result.data

    return jsonify_unified_success(
        data={"rule_id": rule.id},
        message="分类规则创建成功",
        status=HttpStatus.CREATED,
    )


@accounts_classifications_bp.route("/api/rules/<int:rule_id>", methods=["GET"])
@login_required
@view_required
def get_rule(rule_id: int) -> tuple[Response, int]:
    """获取单个规则详情.

    Args:
        rule_id: 规则 ID.

    Returns:
        tuple[Response, int]: 包含规则详情的 JSON 与状态码.

    """
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


@accounts_classifications_bp.route("/api/rules/<int:rule_id>", methods=["PUT"])
@login_required
@update_required
@require_csrf
def update_rule(rule_id: int) -> tuple[Response, int]:
    """更新分类规则.

    Args:
        rule_id: 待更新的规则 ID.

    Returns:
        tuple[Response, int]: 操作结果 JSON 与状态码.

    Raises:
        ValidationError: 表单验证失败时抛出.

    """
    rule = ClassificationRule.query.get_or_404(rule_id)
    payload = request.get_json() or {}
    result = _classification_rule_service.upsert(payload, rule)
    if not result.success or not result.data:
        raise ValidationError(result.message or "更新分类规则失败")

    return jsonify_unified_success(message="分类规则更新成功")

@accounts_classifications_bp.route("/api/rules/<int:rule_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def delete_rule(rule_id: int) -> tuple[Response, int]:
    """删除分类规则.

    Args:
        rule_id: 规则主键 ID.

    Returns:
        tuple[Response, int]: 操作结果 JSON 与状态码.

    """
    rule = ClassificationRule.query.get_or_404(rule_id)

    def _execute() -> tuple[Response, int]:
        with db.session.begin():
            db.session.delete(rule)

        log_info(
            "删除分类规则成功",
            module="accounts_classifications",
            rule_id=rule_id,
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(message="分类规则删除成功")

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="delete_rule",
        public_error="删除分类规则失败",
        context={"rule_id": rule_id},
    )


@accounts_classifications_bp.route("/api/auto-classify", methods=["POST"])
@login_required
@update_required
@require_csrf
def auto_classify() -> tuple[Response, int]:
    """自动分类账户 - 使用优化后的服务.

    根据分类规则自动为账户分配分类.

    Returns:
        (JSON 响应, HTTP 状态码),包含分类结果统计.

    Raises:
        AutoClassifyError: 当自动分类失败时抛出.

    """
    payload_snapshot = request.get_json(silent=True) or {}

    def _execute() -> tuple[Response, int]:
        created_by = current_user.id if current_user.is_authenticated else None
        result = _auto_classify_service.auto_classify(
            instance_id=payload_snapshot.get("instance_id"),
            created_by=created_by,
            use_optimized=payload_snapshot.get("use_optimized"),
        )
        payload = result.to_payload()
        return jsonify_unified_success(data=payload, message=payload["message"])

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="auto_classify",
        public_error="自动分类失败",
        context={key: payload_snapshot.get(key) for key in ("instance_id", "use_optimized")},
        expected_exceptions=(AutoClassifyError,),
    )


@accounts_classifications_bp.route("/api/assignments")
@login_required
@view_required
def get_assignments() -> tuple[Response, int]:
    """获取账户分类分配列表.

    Returns:
        tuple[Response, int]: 包含分配记录数组的 JSON 与状态码.

    """
    def _execute() -> tuple[Response, int]:
        assignments = (
            db.session.query(AccountClassificationAssignment, AccountClassification)
            .join(
                AccountClassification,
                AccountClassificationAssignment.classification_id == AccountClassification.id,
            )
            .filter(AccountClassificationAssignment.is_active.is_(True))
            .all()
        )

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

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="get_assignments",
        public_error="获取账户分类分配失败",
    )


@accounts_classifications_bp.route("/api/assignments/<int:assignment_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def remove_assignment(assignment_id: int) -> tuple[Response, int]:
    """移除账户分类分配.

    Args:
        assignment_id: 分配记录 ID.

    Returns:
        tuple[Response, int]: 操作结果 JSON 与状态码.

    """
    assignment = AccountClassificationAssignment.query.get_or_404(assignment_id)

    def _execute() -> tuple[Response, int]:
        assignment.is_active = False
        with db.session.begin():
            db.session.add(assignment)

        log_info(
            "移除账户分类分配成功",
            module="accounts_classifications",
            assignment_id=assignment_id,
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(message="账户分类分配移除成功")

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="remove_assignment",
        public_error="移除分配失败",
        context={"assignment_id": assignment_id},
    )


@accounts_classifications_bp.route("/api/permissions/<db_type>")
@login_required
@view_required
def get_permissions(db_type: str) -> tuple[Response, int]:
    """获取数据库权限列表.

    Args:
        db_type: 数据库类型标识.

    Returns:
        tuple[Response, int]: 权限配置 JSON 与状态码.

    """
    def _execute() -> tuple[Response, int]:
        permissions = _get_db_permissions(db_type)
        return jsonify_unified_success(data={"permissions": permissions}, message="数据库权限获取成功")

    return safe_route_call(
        _execute,
        module="accounts_classifications",
        action="get_permissions",
        public_error="获取数据库权限失败",
        context={"db_type": db_type},
    )














_classification_create_view = AccountClassificationFormView.as_view("classification_create_form")
_classification_create_view = login_required(create_required(require_csrf(_classification_create_view)))

accounts_classifications_bp.add_url_rule(
    "/classifications/create",
    view_func=_classification_create_view,
    methods=["GET", "POST"],
    defaults={"resource_id": None},
)

_classification_edit_view = AccountClassificationFormView.as_view("classification_edit_form")
_classification_edit_view = login_required(update_required(require_csrf(_classification_edit_view)))

accounts_classifications_bp.add_url_rule(
    "/classifications/<int:resource_id>/edit",
    view_func=_classification_edit_view,
    methods=["GET", "POST"],
)

_rule_create_view = ClassificationRuleFormView.as_view("classification_rule_create_form")
_rule_create_view = login_required(create_required(require_csrf(_rule_create_view)))

accounts_classifications_bp.add_url_rule(
    "/rules/create",
    view_func=_rule_create_view,
    methods=["GET", "POST"],
    defaults={"resource_id": None},
)

_rule_edit_view = ClassificationRuleFormView.as_view("classification_rule_edit_form")
_rule_edit_view = login_required(update_required(require_csrf(_rule_edit_view)))

accounts_classifications_bp.add_url_rule(
    "/rules/<int:resource_id>/edit",
    view_func=_rule_edit_view,
    methods=["GET", "POST"],
)


def _get_db_permissions(db_type: str) -> dict:
    """获取数据库权限列表.

    Args:
        db_type: 数据库类型.

    Returns:
        权限配置字典.

    """
    # 从数据库获取权限配置
    return PermissionConfig.get_permissions_by_db_type(db_type)
