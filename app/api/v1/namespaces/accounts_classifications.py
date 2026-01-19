"""Accounts classifications namespace (Phase 3 全量迁移)."""

from __future__ import annotations

from itertools import groupby
from typing import Any, ClassVar, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.accounts import (
    ACCOUNT_CLASSIFICATION_ASSIGNMENT_ITEM_FIELDS,
    ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS,
    ACCOUNT_CLASSIFICATION_PERMISSIONS_RESPONSE_FIELDS,
    ACCOUNT_CLASSIFICATION_RULE_FILTER_ITEM_FIELDS,
    ACCOUNT_CLASSIFICATION_RULE_ITEM_FIELDS,
)
from app.core.constants import HttpStatus
from app.core.constants.colors import ThemeColors
from app.core.exceptions import ConflictError, ValidationError
from app.services.account_classification.auto_classify_service import (
    AutoClassifyError,
    AutoClassifyService,
)
from app.services.accounts.account_classification_expression_validation_service import (
    AccountClassificationExpressionValidationService,
)
from app.services.accounts.account_classifications_read_service import AccountClassificationsReadService
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService
from app.utils.decorators import require_csrf
from app.utils.theme_color_utils import get_theme_color_choices

ns = Namespace("accounts_classifications", description="账户分类管理")

ErrorEnvelope = get_error_envelope_model(ns)

AccountClassificationWritePayload = ns.model(
    "AccountClassificationWritePayload",
    {
        # 兼容旧前端：name 视为展示名；若未提供 code，则默认 code=name
        "name": fields.String(required=False, description="分类展示名(兼容字段)"),
        "code": fields.String(required=False, description="分类标识(code)，创建后不可修改"),
        "display_name": fields.String(required=False, description="分类展示名"),
        "description": fields.String(required=False, description="分类描述"),
        "risk_level": fields.String(required=False, description="风险等级"),
        "color": fields.String(required=False, description="颜色 key"),
        "icon_name": fields.String(required=False, description="图标名称"),
        "priority": fields.Integer(required=False, description="优先级(0-100)"),
    },
)

AccountClassificationRuleWritePayload = ns.model(
    "AccountClassificationRuleWritePayload",
    {
        "rule_name": fields.String(required=True, description="规则名称"),
        "classification_id": fields.Integer(required=True, description="分类 ID"),
        "db_type": fields.String(required=True, description="数据库类型"),
        "operator": fields.String(required=True, description="匹配逻辑"),
        "rule_expression": fields.Raw(required=False, description="规则表达式(对象或字符串)"),
        "is_active": fields.Boolean(required=False, description="是否启用"),
    },
)

AccountClassificationRuleExpressionValidatePayload = ns.model(
    "AccountClassificationRuleExpressionValidatePayload",
    {
        "rule_expression": fields.Raw(required=True, description="DSL v4 规则表达式(对象或字符串)"),
    },
)

AccountClassificationAutoClassifyPayload = ns.model(
    "AccountClassificationAutoClassifyPayload",
    {
        "instance_id": fields.Raw(required=False, description="实例 ID(可选)"),
    },
)

AccountClassificationItemModel = ns.model("AccountClassificationListItem", ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS)
AccountClassificationRuleItemModel = ns.model("AccountClassificationRuleItem", ACCOUNT_CLASSIFICATION_RULE_ITEM_FIELDS)
AccountClassificationRuleFilterItemModel = ns.model(
    "AccountClassificationRuleFilterItem",
    ACCOUNT_CLASSIFICATION_RULE_FILTER_ITEM_FIELDS,
)
AccountClassificationAssignmentItemModel = ns.model(
    "AccountClassificationAssignmentItem",
    ACCOUNT_CLASSIFICATION_ASSIGNMENT_ITEM_FIELDS,
)
AccountClassificationPermissionsData = ns.model(
    "AccountClassificationPermissionsData",
    ACCOUNT_CLASSIFICATION_PERMISSIONS_RESPONSE_FIELDS,
)

AccountClassificationColorsData = ns.model(
    "AccountClassificationColorsData",
    {
        "colors": fields.Raw(required=True),
        "choices": fields.List(fields.Raw, required=True),
    },
)
AccountClassificationColorsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationColorsSuccessEnvelope",
    AccountClassificationColorsData,
)

AccountClassificationsListData = ns.model(
    "AccountClassificationsListData",
    {
        "classifications": fields.List(fields.Nested(AccountClassificationItemModel)),
    },
)
AccountClassificationsListSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationsListSuccessEnvelope",
    AccountClassificationsListData,
)

AccountClassificationDetailData = ns.model(
    "AccountClassificationDetailData",
    {
        "classification": fields.Raw(required=True),
    },
)
AccountClassificationDetailSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationDetailSuccessEnvelope",
    AccountClassificationDetailData,
)

AccountClassificationAssignmentsData = ns.model(
    "AccountClassificationAssignmentsData",
    {
        "assignments": fields.List(fields.Nested(AccountClassificationAssignmentItemModel)),
    },
)
AccountClassificationAssignmentsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationAssignmentsSuccessEnvelope",
    AccountClassificationAssignmentsData,
)

AccountClassificationRulesByDbTypeData = ns.model(
    "AccountClassificationRulesByDbTypeData",
    {
        "rules_by_db_type": fields.Raw(required=True),
    },
)
AccountClassificationRulesByDbTypeSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRulesByDbTypeSuccessEnvelope",
    AccountClassificationRulesByDbTypeData,
)

AccountClassificationRulesFilterData = ns.model(
    "AccountClassificationRulesFilterData",
    {
        "rules": fields.List(fields.Nested(AccountClassificationRuleFilterItemModel)),
    },
)
AccountClassificationRulesFilterSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRulesFilterSuccessEnvelope",
    AccountClassificationRulesFilterData,
)

_account_classification_rules_filter_query_parser = new_parser()
_account_classification_rules_filter_query_parser.add_argument("classification_id", type=int, location="args")
_account_classification_rules_filter_query_parser.add_argument("db_type", type=str, location="args")

AccountClassificationRuleDetailData = ns.model(
    "AccountClassificationRuleDetailData",
    {
        "rule": fields.Raw(required=True),
    },
)
AccountClassificationRuleDetailSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRuleDetailSuccessEnvelope",
    AccountClassificationRuleDetailData,
)

AccountClassificationRuleCreateData = ns.model(
    "AccountClassificationRuleCreateData",
    {
        "rule_id": fields.Integer(required=True),
    },
)
AccountClassificationRuleCreateSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRuleCreateSuccessEnvelope",
    AccountClassificationRuleCreateData,
)

AccountClassificationRuleExpressionValidateData = ns.model(
    "AccountClassificationRuleExpressionValidateData",
    {"rule_expression": fields.Raw(required=True)},
)
AccountClassificationRuleExpressionValidateSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRuleExpressionValidateSuccessEnvelope",
    AccountClassificationRuleExpressionValidateData,
)

AccountClassificationPermissionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationPermissionsSuccessEnvelope",
    AccountClassificationPermissionsData,
)

AccountClassificationAutoClassifyData = ns.model(
    "AccountClassificationAutoClassifyData",
    {
        "classified_accounts": fields.Integer(required=True),
        "total_classifications_added": fields.Integer(required=True),
        "failed_count": fields.Integer(required=True),
        "message": fields.String(required=True),
    },
)
AccountClassificationAutoClassifySuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationAutoClassifySuccessEnvelope",
    AccountClassificationAutoClassifyData,
)

_read_service = AccountClassificationsReadService()
_write_service = AccountClassificationsWriteService()
_auto_classify_service = AutoClassifyService()


def _parse_json_payload() -> dict[str, object]:
    if not request.is_json:
        return {}
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _serialize_classification(classification: Any) -> dict[str, object]:
    display_name = getattr(classification, "display_name", None) or classification.name
    return {
        "id": classification.id,
        # 兼容旧前端：name 继续作为展示名输出
        "name": display_name,
        "code": classification.name,
        "display_name": display_name,
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


def _get_classification_usage(classification_id: int) -> tuple[int, int]:
    return _read_service.get_classification_usage(classification_id)


def _classification_deletion_blockers(classification: Any) -> dict[str, int | str] | None:
    if classification.is_system:
        return {"reason": "system", "rule_count": 0, "assignment_count": 0}

    rule_count, assignment_count = _get_classification_usage(classification.id)
    if rule_count or assignment_count:
        return {
            "reason": "in_use",
            "rule_count": rule_count,
            "assignment_count": assignment_count,
        }
    return None


def _serialize_rule(
    rule: Any,
    *,
    parse_expression: bool = False,
) -> dict[str, object]:
    expression_value = rule.get_rule_expression() if parse_expression else rule.rule_expression

    classification = rule.classification if rule else None
    classification_name = None
    if classification is not None:
        classification_name = getattr(classification, "display_name", None) or classification.name

    return {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "classification_id": rule.classification_id,
        "classification_name": classification_name,
        "db_type": rule.db_type,
        "rule_expression": expression_value,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


@ns.route("/colors")
class AccountClassificationColorsResource(BaseResource):
    """账户分类颜色选项资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationColorsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取颜色选项."""

        def _execute():
            data = {
                "colors": ThemeColors.COLOR_MAP,
                "choices": get_theme_color_choices(),
            }
            return self.success(data=data, message="颜色选项获取成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_color_options",
            public_error="获取颜色选项失败",
            context={"color_count": len(ThemeColors.COLOR_MAP)},
        )


@ns.route("")
class AccountClassificationsResource(BaseResource):
    """账户分类列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", AccountClassificationsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """获取账户分类列表."""

        def _execute():
            classifications = _read_service.list_classifications()
            payload = marshal(classifications, ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS)
            return self.success(data={"classifications": payload}, message="账户分类获取成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_classifications",
            public_error="获取账户分类失败",
        )

    @ns.expect(AccountClassificationWritePayload, validate=False)
    @ns.response(201, "Created", AccountClassificationDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("create")
    @require_csrf
    def post(self):
        """创建账户分类."""
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)
        classification_name = payload.get("name")
        if not isinstance(classification_name, str):
            classification_name = None

        def _execute():
            classification = _write_service.create_classification(payload, operator_id=operator_id)
            return self.success(
                data={"classification": _serialize_classification(classification)},
                message="账户分类创建成功",
                status=HttpStatus.CREATED,
            )

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="create_classification",
            public_error="创建账户分类失败",
            context={"classification_name": classification_name},
        )


@ns.route("/<int:classification_id>")
class AccountClassificationDetailResource(BaseResource):
    """账户分类详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", AccountClassificationDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, classification_id: int):
        """获取账户分类详情."""

        def _execute():
            classification = _read_service.get_classification_or_error(classification_id)
            item = _read_service.build_classification_detail(classification)
            payload = marshal(item, ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS)
            return self.success(data={"classification": payload}, message="账户分类获取成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_classification",
            public_error="获取账户分类失败",
            context={"classification_id": classification_id},
        )

    @ns.expect(AccountClassificationWritePayload, validate=False)
    @ns.response(200, "OK", AccountClassificationDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def put(self, classification_id: int):
        """更新账户分类."""
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)

        def _execute():
            classification = _write_service.get_classification_or_error(classification_id)
            updated = _write_service.update_classification(classification, payload, operator_id=operator_id)
            return self.success(
                data={"classification": _serialize_classification(updated)},
                message="账户分类更新成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="update_classification",
            public_error="更新账户分类失败",
            context={"classification_id": classification_id},
        )

    @ns.response(200, "OK", make_success_envelope_model(ns, "AccountClassificationDeleteSuccessEnvelope"))
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, classification_id: int):
        """删除账户分类."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            classification = _write_service.get_classification_or_error(classification_id)
            blockers = _classification_deletion_blockers(classification)
            if blockers:
                if blockers["reason"] == "system":
                    raise ValidationError("系统分类不能删除", message_key="SYSTEM_CLASSIFICATION")
                raise ConflictError(
                    "分类仍在使用,请先迁移关联规则/账户后再删除",
                    message_key="CLASSIFICATION_IN_USE",
                    extra={
                        "rule_count": blockers["rule_count"],
                        "assignment_count": blockers["assignment_count"],
                    },
                )

            _write_service.delete_classification(classification, operator_id=operator_id)
            return self.success(message="账户分类删除成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="delete_classification",
            public_error="删除账户分类失败",
            context={"classification_id": classification_id},
        )


@ns.route("/rules")
class AccountClassificationRulesResource(BaseResource):
    """账户分类规则资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", AccountClassificationRulesByDbTypeSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
        """获取分类规则列表."""

        def _execute():
            rules = _read_service.list_rules()
            serialized = marshal(rules, ACCOUNT_CLASSIFICATION_RULE_ITEM_FIELDS)

            def _rule_db_type(item: dict[str, object]) -> str:
                value = item.get("db_type")
                return cast(str, value) if isinstance(value, str) else "unknown"

            sorted_rules = sorted(serialized, key=_rule_db_type)
            rules_by_db_type: dict[str, list[dict[str, object]]] = {
                db_type: list(group) for db_type, group in groupby(sorted_rules, key=_rule_db_type)
            }

            return self.success(
                data={"rules_by_db_type": rules_by_db_type},
                message="分类规则列表获取成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="list_rules",
            public_error="获取规则列表失败",
        )

    @ns.expect(AccountClassificationRuleWritePayload, validate=False)
    @ns.response(201, "Created", AccountClassificationRuleCreateSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("create")
    @require_csrf
    def post(self):
        """创建分类规则."""
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)
        classification_id_context = payload.get("classification_id")
        if not isinstance(classification_id_context, (int, str)):
            classification_id_context = None
        db_type_context = payload.get("db_type")
        if not isinstance(db_type_context, str):
            db_type_context = None

        def _execute():
            rule = _write_service.create_rule(payload, operator_id=operator_id)
            return self.success(
                data={"rule_id": rule.id},
                message="分类规则创建成功",
                status=HttpStatus.CREATED,
            )

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="create_rule",
            public_error="创建分类规则失败",
            context={
                "classification_id": classification_id_context,
                "db_type": db_type_context,
            },
        )


@ns.route("/rules/filter")
class AccountClassificationRulesFilterResource(BaseResource):
    """分类规则筛选资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationRulesFilterSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_account_classification_rules_filter_query_parser)
    def get(self):
        """筛选分类规则."""
        parsed = _account_classification_rules_filter_query_parser.parse_args()
        classification_id = (
            parsed.get("classification_id") if isinstance(parsed.get("classification_id"), int) else None
        )
        db_type = parsed.get("db_type") if isinstance(parsed.get("db_type"), str) else None

        def _execute():
            rules = _read_service.filter_rules(classification_id=classification_id, db_type=db_type)
            payload = marshal(rules, ACCOUNT_CLASSIFICATION_RULE_FILTER_ITEM_FIELDS)
            return self.success(data={"rules": payload}, message="分类规则获取成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_rules",
            public_error="获取分类规则失败",
            context={
                "classification_id": classification_id,
                "db_type": db_type,
            },
        )


@ns.route("/rules/actions/validate-expression")
class AccountClassificationRuleExpressionValidateResource(BaseResource):
    """分类规则表达式校验资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.expect(AccountClassificationRuleExpressionValidatePayload, validate=False)
    @ns.response(200, "OK", AccountClassificationRuleExpressionValidateSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """校验规则表达式."""
        payload = _parse_json_payload()

        def _execute():
            raw_expression = payload.get("rule_expression")
            parsed = AccountClassificationExpressionValidationService().parse_and_validate(raw_expression)
            return self.success(data={"rule_expression": parsed}, message="规则表达式校验通过")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="validate_rule_expression",
            public_error="校验规则表达式失败",
            expected_exceptions=(ValidationError,),
        )


@ns.route("/rules/<int:rule_id>")
class AccountClassificationRuleDetailResource(BaseResource):
    """分类规则详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", AccountClassificationRuleDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, rule_id: int):
        """获取分类规则详情."""

        def _execute():
            rule = _read_service.get_rule_or_error(rule_id)
            return self.success(
                data={"rule": _serialize_rule(rule, parse_expression=True)},
                message="规则详情获取成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_rule",
            public_error="获取规则详情失败",
            context={"rule_id": rule_id},
        )

    @ns.expect(AccountClassificationRuleWritePayload, validate=False)
    @ns.response(200, "OK", make_success_envelope_model(ns, "AccountClassificationRuleUpdateSuccessEnvelope"))
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def put(self, rule_id: int):
        """更新分类规则."""
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)

        def _execute():
            rule = _write_service.get_rule_or_error(rule_id)
            _write_service.update_rule(rule, payload, operator_id=operator_id)
            return self.success(message="分类规则更新成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="update_rule",
            public_error="更新分类规则失败",
            context={"rule_id": rule_id},
        )

    @ns.response(200, "OK", make_success_envelope_model(ns, "AccountClassificationRuleDeleteSuccessEnvelope"))
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, rule_id: int):
        """删除分类规则."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            rule = _write_service.get_rule_or_error(rule_id)
            _write_service.delete_rule(rule, operator_id=operator_id)
            return self.success(message="分类规则删除成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="delete_rule",
            public_error="删除分类规则失败",
            context={"rule_id": rule_id},
        )


@ns.route("/assignments")
class AccountClassificationAssignmentsResource(BaseResource):
    """账户分类分配资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationAssignmentsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取账户分类分配列表."""

        def _execute():
            assignments = _read_service.list_assignments()
            payload = marshal(assignments, ACCOUNT_CLASSIFICATION_ASSIGNMENT_ITEM_FIELDS)
            return self.success(
                data={"assignments": payload},
                message="账户分类分配获取成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_assignments",
            public_error="获取账户分类分配失败",
        )


@ns.route("/assignments/<int:assignment_id>")
class AccountClassificationAssignmentResource(BaseResource):
    """账户分类分配详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", make_success_envelope_model(ns, "AccountClassificationAssignmentDeleteSuccessEnvelope"))
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, assignment_id: int):
        """移除账户分类分配."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            assignment = _write_service.get_assignment_or_error(assignment_id)
            _write_service.deactivate_assignment(assignment, operator_id=operator_id)
            return self.success(message="账户分类分配移除成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="remove_assignment",
            public_error="移除分配失败",
            context={"assignment_id": assignment_id},
        )


@ns.route("/permissions/<string:db_type>")
class AccountClassificationPermissionsResource(BaseResource):
    """账户分类权限选项资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationPermissionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, db_type: str):
        """获取数据库权限选项."""

        def _execute():
            permissions = _read_service.get_permissions(db_type)
            payload = marshal(
                {"permissions": permissions},
                ACCOUNT_CLASSIFICATION_PERMISSIONS_RESPONSE_FIELDS,
            )
            return self.success(data=payload, message="数据库权限获取成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_permissions",
            public_error="获取数据库权限失败",
            context={"db_type": db_type},
        )


@ns.route("/actions/auto-classify")
class AccountClassificationAutoClassifyActionResource(BaseResource):
    """自动分类动作资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.expect(AccountClassificationAutoClassifyPayload, validate=False)
    @ns.response(200, "OK", AccountClassificationAutoClassifySuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def post(self):
        """执行自动分类."""
        payload_snapshot = _parse_json_payload()
        created_by = current_user.id if current_user.is_authenticated else None
        instance_id_raw = payload_snapshot.get("instance_id")
        instance_id = instance_id_raw if isinstance(instance_id_raw, (int, float, str, bool)) else None

        def _execute():
            result = _auto_classify_service.auto_classify(
                instance_id=instance_id,
                created_by=created_by,
            )
            payload = result.to_payload()
            return self.success(data=payload, message=payload["message"])

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="auto_classify",
            public_error="自动分类失败",
            context={"instance_id": instance_id},
            expected_exceptions=(AutoClassifyError,),
        )
