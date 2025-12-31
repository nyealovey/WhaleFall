"""Accounts classifications namespace (Phase 3 全量迁移)."""

from __future__ import annotations

import json
from itertools import groupby
from typing import cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.constants import HttpStatus
from app.constants.colors import ThemeColors
from app.errors import ConflictError, ValidationError
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.routes.accounts.restx_models import (
    ACCOUNT_CLASSIFICATION_ASSIGNMENT_ITEM_FIELDS,
    ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS,
    ACCOUNT_CLASSIFICATION_PERMISSIONS_RESPONSE_FIELDS,
    ACCOUNT_CLASSIFICATION_RULE_FILTER_ITEM_FIELDS,
    ACCOUNT_CLASSIFICATION_RULE_ITEM_FIELDS,
    ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS,
)
from app.services.account_classification.auto_classify_service import (
    AutoClassifyError,
    AutoClassifyService,
)
from app.services.account_classification.dsl_v4 import collect_dsl_v4_validation_errors, is_dsl_v4_expression
from app.services.accounts.account_classifications_read_service import AccountClassificationsReadService
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService
from app.utils.decorators import require_csrf

ns = Namespace("accounts_classifications", description="账户分类管理")

ErrorEnvelope = get_error_envelope_model(ns)

AccountClassificationWritePayload = ns.model(
    "AccountClassificationWritePayload",
    {
        "name": fields.String(required=True, description="分类名称"),
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
        "use_optimized": fields.Raw(required=False, description="是否使用优化流程(可选)"),
    },
)

AccountClassificationItemModel = ns.model("AccountClassificationListItem", ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS)
AccountClassificationRuleItemModel = ns.model("AccountClassificationRuleItem", ACCOUNT_CLASSIFICATION_RULE_ITEM_FIELDS)
AccountClassificationRuleFilterItemModel = ns.model(
    "AccountClassificationRuleFilterItem",
    ACCOUNT_CLASSIFICATION_RULE_FILTER_ITEM_FIELDS,
)
AccountClassificationRuleStatItemModel = ns.model(
    "AccountClassificationRuleStatItem",
    ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS,
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

AccountClassificationRuleStatsData = ns.model(
    "AccountClassificationRuleStatsData",
    {
        "rule_stats": fields.List(fields.Nested(AccountClassificationRuleStatItemModel)),
    },
)
AccountClassificationRuleStatsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountClassificationRuleStatsSuccessEnvelope",
    AccountClassificationRuleStatsData,
)

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


def _serialize_classification(classification: AccountClassification) -> dict[str, object]:
    return {
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


def _get_classification_usage(classification_id: int) -> tuple[int, int]:
    rule_count = ClassificationRule.query.filter_by(classification_id=classification_id).count()
    assignment_count = AccountClassificationAssignment.query.filter_by(
        classification_id=classification_id,
        is_active=True,
    ).count()
    return rule_count, assignment_count


def _classification_deletion_blockers(classification: AccountClassification) -> dict[str, int | str] | None:
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
    rule: ClassificationRule,
    *,
    parse_expression: bool = False,
) -> dict[str, object]:
    expression_value: object
    if parse_expression:
        expression_value = rule.get_rule_expression()
    else:
        expression_value = rule.rule_expression

    return {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "classification_id": rule.classification_id,
        "classification_name": rule.classification.name if rule.classification else None,
        "db_type": rule.db_type,
        "rule_expression": expression_value,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def _parse_rule_ids_param(raw_value: str | None) -> list[int] | None:
    if not raw_value:
        return None
    rule_ids: list[int] = []
    for token in raw_value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        try:
            rule_ids.append(int(stripped))
        except ValueError as exc:
            raise ValidationError("rule_ids 参数必须为整数ID,使用逗号分隔") from exc
    return rule_ids or None


@ns.route("/colors")
class AccountClassificationColorsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationColorsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            data = {
                "colors": ThemeColors.COLOR_MAP,
                "choices": ThemeColors.get_color_choices(),
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", AccountClassificationsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
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
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)

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
            context={"classification_name": payload.get("name")},
        )


@ns.route("/<int:classification_id>")
class AccountClassificationDetailResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", AccountClassificationDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, classification_id: int):
        def _execute():
            classification = AccountClassification.query.get_or_404(classification_id)
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
        classification = AccountClassification.query.get_or_404(classification_id)
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)

        def _execute():
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
        classification = AccountClassification.query.get_or_404(classification_id)
        operator_id = getattr(current_user, "id", None)

        def _execute():
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", AccountClassificationRulesByDbTypeSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self):
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
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)

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
                "classification_id": payload.get("classification_id"),
                "db_type": payload.get("db_type"),
            },
        )


@ns.route("/rules/filter")
class AccountClassificationRulesFilterResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationRulesFilterSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        classification_id = request.args.get("classification_id", type=int)
        db_type = request.args.get("db_type")

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
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.expect(AccountClassificationRuleExpressionValidatePayload, validate=False)
    @ns.response(200, "OK", AccountClassificationRuleExpressionValidateSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        payload = _parse_json_payload()

        def _execute():
            raw_expression = payload.get("rule_expression")
            if raw_expression is None:
                raise ValidationError("缺少 rule_expression 字段")

            parsed: object = raw_expression
            if isinstance(raw_expression, str):
                try:
                    parsed = json.loads(raw_expression)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(f"规则表达式 JSON 解析失败: {exc}") from exc

            if not is_dsl_v4_expression(parsed):
                raise ValidationError("仅支持 DSL v4 表达式(version=4)", message_key="DSL_V4_REQUIRED")

            errors = collect_dsl_v4_validation_errors(parsed)
            if errors:
                raise ValidationError(
                    "DSL v4 表达式校验失败",
                    message_key="INVALID_DSL_EXPRESSION",
                    extra={"errors": errors},
                )
            return self.success(data={"rule_expression": parsed}, message="规则表达式校验通过")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="validate_rule_expression",
            public_error="校验规则表达式失败",
            expected_exceptions=(ValidationError,),
        )


@ns.route("/rules/stats")
class AccountClassificationRulesStatsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationRuleStatsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        rule_ids = _parse_rule_ids_param(request.args.get("rule_ids"))

        def _execute():
            stats = _read_service.get_rule_stats(rule_ids=rule_ids)
            payload = marshal(stats, ACCOUNT_CLASSIFICATION_RULE_STAT_ITEM_FIELDS)
            return self.success(data={"rule_stats": payload}, message="规则命中统计获取成功")

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="get_rule_stats",
            public_error="获取规则命中统计失败",
            context={"rule_ids": rule_ids},
        )


@ns.route("/rules/<int:rule_id>")
class AccountClassificationRuleDetailResource(BaseResource):
    method_decorators = [api_login_required]

    @ns.response(200, "OK", AccountClassificationRuleDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, rule_id: int):
        def _execute():
            rule = ClassificationRule.query.get_or_404(rule_id)
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
        rule = ClassificationRule.query.get_or_404(rule_id)
        payload = _parse_json_payload()
        operator_id = getattr(current_user, "id", None)

        def _execute():
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
        rule = ClassificationRule.query.get_or_404(rule_id)
        operator_id = getattr(current_user, "id", None)

        def _execute():
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
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationAssignmentsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
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
    method_decorators = [api_login_required]

    @ns.response(200, "OK", make_success_envelope_model(ns, "AccountClassificationAssignmentDeleteSuccessEnvelope"))
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, assignment_id: int):
        assignment = AccountClassificationAssignment.query.get_or_404(assignment_id)
        operator_id = getattr(current_user, "id", None)

        def _execute():
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
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountClassificationPermissionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, db_type: str):
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
    method_decorators = [api_login_required]

    @ns.expect(AccountClassificationAutoClassifyPayload, validate=False)
    @ns.response(200, "OK", AccountClassificationAutoClassifySuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def post(self):
        payload_snapshot = _parse_json_payload()
        created_by = current_user.id if current_user.is_authenticated else None

        def _execute():
            result = _auto_classify_service.auto_classify(
                instance_id=payload_snapshot.get("instance_id"),
                created_by=created_by,
                use_optimized=payload_snapshot.get("use_optimized"),
            )
            payload = result.to_payload()
            return self.success(data=payload, message=payload["message"])

        return self.safe_call(
            _execute,
            module="accounts_classifications",
            action="auto_classify",
            public_error="自动分类失败",
            context={key: payload_snapshot.get(key) for key in ("instance_id", "use_optimized")},
            expected_exceptions=(AutoClassifyError,),
        )
