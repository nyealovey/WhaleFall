"""Accounts namespace (Phase 2 核心域迁移 - Ledgers)."""

from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.constants.sync_constants import SyncOperationType
from app.errors import NotFoundError, SystemError, ValidationError
from app.models.instance import Instance
from app.routes.accounts.restx_models import (
    ACCOUNT_LEDGER_ITEM_FIELDS,
    ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS,
    ACCOUNT_STATISTICS_FIELDS,
)
from app.services.accounts.accounts_statistics_read_service import AccountsStatisticsReadService
from app.services.accounts_sync import accounts_sync_service
from app.services.ledgers.accounts_ledger_list_service import AccountsLedgerListService
from app.services.ledgers.accounts_ledger_permissions_service import AccountsLedgerPermissionsService
from app.tasks.accounts_sync_tasks import sync_accounts as sync_accounts_task
from app.types.accounts_ledgers import AccountFilters
from app.utils.decorators import require_csrf
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_error_message
from app.utils.route_safety import log_with_context
from app.utils.structlog_config import log_info, log_warning

ns = Namespace("accounts", description="账户管理")

ErrorEnvelope = get_error_envelope_model(ns)

TagModel = ns.model(
    "AccountTag",
    {
        "name": fields.String(),
        "display_name": fields.String(),
        "color": fields.String(),
    },
)

ClassificationModel = ns.model(
    "AccountClassification",
    {
        "name": fields.String(),
        "color": fields.String(),
    },
)

AccountLedgerItemModel = ns.model(
    "AccountLedgerItem",
    {
        "id": fields.Integer(),
        "username": fields.String(),
        "instance_name": fields.String(),
        "instance_host": fields.String(),
        "db_type": fields.String(),
        "is_locked": fields.Boolean(),
        "is_superuser": fields.Boolean(),
        "is_active": fields.Boolean(),
        "is_deleted": fields.Boolean(),
        "tags": fields.List(fields.Nested(TagModel)),
        "classifications": fields.List(fields.Nested(ClassificationModel)),
    },
)

AccountLedgersListData = ns.model(
    "AccountLedgersListData",
    {
        "items": fields.List(fields.Nested(AccountLedgerItemModel)),
        "total": fields.Integer(),
        "page": fields.Integer(),
        "pages": fields.Integer(),
        "limit": fields.Integer(),
    },
)

AccountLedgersListSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountLedgersListSuccessEnvelope",
    AccountLedgersListData,
)

AccountLedgerPermissionsData = ns.model(
    "AccountLedgerPermissionsData",
    {
        "permissions": fields.Raw,
        "account": fields.Raw,
    },
)

AccountLedgerPermissionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountLedgerPermissionsSuccessEnvelope",
    AccountLedgerPermissionsData,
)

AccountStatisticsStatsModel = ns.model(
    "AccountStatisticsStats",
    {
        "total_accounts": fields.Integer(),
        "active_accounts": fields.Integer(),
        "locked_accounts": fields.Integer(),
        "normal_accounts": fields.Integer(),
        "deleted_accounts": fields.Integer(),
        "database_instances": fields.Integer(),
        "total_instances": fields.Integer(),
        "active_instances": fields.Integer(),
        "disabled_instances": fields.Integer(),
        "normal_instances": fields.Integer(),
        "deleted_instances": fields.Integer(),
        "db_type_stats": fields.Raw(),
        "classification_stats": fields.Raw(),
    },
)

AccountStatisticsData = ns.model(
    "AccountStatisticsData",
    {
        "stats": fields.Nested(AccountStatisticsStatsModel),
    },
)

AccountStatisticsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsSuccessEnvelope",
    AccountStatisticsData,
)

AccountStatisticsSummaryData = ns.model(
    "AccountStatisticsSummaryData",
    {
        "total_accounts": fields.Integer(),
        "active_accounts": fields.Integer(),
        "locked_accounts": fields.Integer(),
        "normal_accounts": fields.Integer(),
        "deleted_accounts": fields.Integer(),
        "total_instances": fields.Integer(),
        "active_instances": fields.Integer(),
        "disabled_instances": fields.Integer(),
        "normal_instances": fields.Integer(),
        "deleted_instances": fields.Integer(),
    },
)

AccountStatisticsSummarySuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsSummarySuccessEnvelope",
    AccountStatisticsSummaryData,
)

AccountStatisticsDbTypesSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsDbTypesSuccessEnvelope",
)

AccountStatisticsClassificationsSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountStatisticsClassificationsSuccessEnvelope",
)


AccountSyncPayload = ns.model(
    "AccountSyncPayload",
    {
        "instance_id": fields.Integer(required=True, description="实例 ID"),
    },
)

AccountSyncResultData = ns.model(
    "AccountSyncResultData",
    {
        "result": fields.Raw(required=True),
    },
)

AccountSyncResultSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountSyncResultSuccessEnvelope",
    AccountSyncResultData,
)

AccountSyncAllData = ns.model(
    "AccountSyncAllData",
    {
        "manual_job_id": fields.String(required=True),
    },
)

AccountSyncAllSuccessEnvelope = make_success_envelope_model(
    ns,
    "AccountSyncAllSuccessEnvelope",
    AccountSyncAllData,
)

BACKGROUND_SYNC_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ValidationError,
    SystemError,
    SQLAlchemyError,
    RuntimeError,
)


def _ensure_active_instances() -> int:
    active_count = Instance.query.filter_by(is_active=True).count()
    if active_count == 0:
        msg = "没有找到活跃的数据库实例"
        log_warning(msg, module="accounts_sync", user_id=current_user.id)
        raise ValidationError(msg)
    return int(active_count)


def _launch_background_sync(created_by: int | None) -> threading.Thread:
    def _run_sync_task(captured_created_by: int | None) -> None:
        try:
            sync_accounts_task(manual_run=True, created_by=captured_created_by)
        except BACKGROUND_SYNC_EXCEPTIONS as exc:  # pragma: no cover
            log_with_context(
                "error",
                "后台批量账户同步失败",
                module="accounts_sync",
                action="sync_all_accounts_background",
                context={"created_by": captured_created_by},
                extra={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
            )

    thread = threading.Thread(
        target=_run_sync_task,
        args=(created_by,),
        name="sync_accounts_manual_batch",
        daemon=True,
    )
    thread.start()
    return thread


def _get_instance(instance_id: int) -> Instance:
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        raise NotFoundError("实例不存在")
    return instance


def _normalize_sync_result(result: Mapping[str, Any] | None, *, context: str) -> tuple[bool, dict[str, Any]]:
    if not result:
        return False, {"status": "failed", "message": f"{context}返回为空"}

    normalized = dict(result)
    is_success = bool(normalized.pop("success", True))
    message = normalized.get("message")
    if not message:
        message = f"{context}{'成功' if is_success else '失败'}"

    normalized["status"] = "completed" if is_success else "failed"
    normalized["message"] = message
    normalized["success"] = is_success
    return is_success, normalized


def _log_sync_failure(instance: Instance, *, message: str) -> None:
    log_with_context(
        "error",
        "实例账户同步失败",
        module="accounts_sync",
        action="sync_instance_accounts",
        context={
            "user_id": getattr(current_user, "id", None),
            "instance_id": instance.id,
            "instance_name": instance.name,
            "db_type": instance.db_type,
            "host": instance.host,
        },
        extra={"error_message": message},
    )


def _parse_sync_payload() -> dict[str, object]:
    if request.is_json:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}
    return {}


def _parse_account_filters(*, allow_query_db_type: bool = True) -> AccountFilters:
    args = request.args
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=200,
        module="accounts_ledgers",
        action="list_accounts_data",
    )
    search = (args.get("search") or "").strip()
    instance_id = args.get("instance_id", type=int)
    is_locked = args.get("is_locked")
    is_superuser = args.get("is_superuser")
    plugin = (args.get("plugin", "") or "").strip()
    tags = [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]
    classification_param = (args.get("classification", "") or "").strip()
    classification_filter = classification_param if classification_param not in {"", "all"} else ""
    raw_db_type = args.get("db_type") if allow_query_db_type else None
    normalized_db_type = raw_db_type if raw_db_type not in {None, "", "all"} else None

    return AccountFilters(
        page=page,
        limit=limit,
        search=search,
        instance_id=instance_id,
        is_locked=is_locked,
        is_superuser=is_superuser,
        plugin=plugin,
        tags=tags,
        classification=classification_param,
        classification_filter=classification_filter,
        db_type=normalized_db_type,
    )


@ns.route("/ledgers")
class AccountsLedgersResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgersListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        filters = _parse_account_filters(allow_query_db_type=True)
        sort_field = request.args.get("sort", "username")
        sort_order = (request.args.get("order", "asc") or "asc").lower()

        def _execute():
            result = AccountsLedgerListService().list_accounts(filters, sort_field=sort_field, sort_order=sort_order)
            items = marshal(result.items, ACCOUNT_LEDGER_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                    "limit": result.limit,
                },
                message="获取账户列表成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_ledgers",
            action="list_accounts_data",
            public_error="获取账户列表失败",
            context={
                "search": filters.search,
                "db_type": filters.db_type,
                "instance_id": filters.instance_id,
                "is_locked": filters.is_locked,
                "is_superuser": filters.is_superuser,
                "tags_count": len(filters.tags),
                "classification": filters.classification_filter,
                "page": filters.page,
                "page_size": filters.limit,
                "sort": sort_field,
                "order": sort_order,
            },
        )


@ns.route("/ledgers/<int:account_id>/permissions")
class AccountsLedgersPermissionsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountLedgerPermissionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, account_id: int):
        def _execute():
            result = AccountsLedgerPermissionsService().get_permissions(account_id)
            payload = marshal(result, ACCOUNT_LEDGER_PERMISSIONS_RESPONSE_FIELDS, skip_none=True)
            return self.success(
                data=payload,
                message="获取账户权限成功",
            )

        return self.safe_call(
            _execute,
            module="accounts_ledgers",
            action="get_account_permissions",
            public_error="获取账户权限失败",
            context={"account_id": account_id},
        )


@ns.route("/statistics")
class AccountsStatisticsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            result = AccountsStatisticsReadService().build_statistics()
            stats_payload = marshal(result, ACCOUNT_STATISTICS_FIELDS)
            return self.success(data={"stats": stats_payload}, message="获取账户统计信息成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics",
            public_error="获取账户统计信息失败",
        )


@ns.route("/statistics/summary")
class AccountsStatisticsSummaryResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsSummarySuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        instance_id = request.args.get("instance_id", type=int)
        db_type = request.args.get("db_type", type=str)

        def _execute():
            summary = AccountsStatisticsReadService().fetch_summary(instance_id=instance_id, db_type=db_type)
            return self.success(data=summary, message="获取账户统计汇总成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics_summary",
            public_error="获取账户统计汇总失败",
            context={"instance_id": instance_id, "db_type": db_type},
        )


@ns.route("/statistics/db-types")
class AccountsStatisticsByDbTypeResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsDbTypesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            stats = AccountsStatisticsReadService().fetch_db_type_stats()
            return self.success(data=stats, message="获取数据库类型统计成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics_by_db_type",
            public_error="获取数据库类型统计失败",
        )


@ns.route("/statistics/classifications")
class AccountsStatisticsByClassificationResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", AccountStatisticsClassificationsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            stats = AccountsStatisticsReadService().fetch_classification_stats()
            return self.success(data=stats, message="获取账户分类统计成功")

        return self.safe_call(
            _execute,
            module="accounts_statistics",
            action="get_account_statistics_by_classification",
            public_error="获取账户分类统计失败",
        )


@ns.route("/actions/sync-all")
class AccountsSyncAllActionResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("update")]

    @ns.response(200, "OK", AccountSyncAllSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        created_by = getattr(current_user, "id", None)

        def _execute():
            log_info("触发批量账户同步", module="accounts_sync", user_id=current_user.id)
            active_instance_count = _ensure_active_instances()
            thread = _launch_background_sync(created_by)
            log_info(
                "批量账户同步任务已在后台启动",
                module="accounts_sync",
                user_id=current_user.id,
                active_instance_count=active_instance_count,
                thread_name=thread.name,
            )
            return self.success(
                data={"manual_job_id": thread.name},
                message="批量账户同步任务已在后台启动,请稍后在会话中心查看进度.",
            )

        return self.safe_call(
            _execute,
            module="accounts_sync",
            action="sync_all_accounts",
            public_error="批量同步任务触发失败,请稍后重试",
            context={"scope": "all_instances"},
        )


@ns.route("/actions/sync")
class AccountsSyncInstanceActionResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("update")]

    @ns.expect(AccountSyncPayload, validate=False)
    @ns.response(200, "OK", AccountSyncResultSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        payload = _parse_sync_payload()
        instance_id_raw = payload.get("instance_id")
        if instance_id_raw is None:
            raise ValidationError("缺少实例ID")
        if not isinstance(instance_id_raw, (int, str)):
            raise ValidationError("实例ID必须为整数")
        try:
            instance_id = int(instance_id_raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError("实例ID必须为整数") from exc

        def _execute():
            instance = _get_instance(instance_id)
            log_info(
                "开始同步实例账户",
                module="accounts_sync",
                user_id=current_user.id,
                instance_id=instance.id,
                instance_name=instance.name,
                db_type=instance.db_type,
                host=instance.host,
            )

            raw_result = accounts_sync_service.sync_accounts(instance, sync_type=SyncOperationType.MANUAL_SINGLE.value)
            is_success, normalized = _normalize_sync_result(raw_result, context=f"实例 {instance.name} 账户同步")

            if is_success:
                instance.sync_count = (instance.sync_count or 0) + 1
                log_info(
                    "实例账户同步成功",
                    module="accounts_sync",
                    user_id=current_user.id,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    synced_count=normalized.get("synced_count", 0),
                )
                return self.success(data={"result": normalized}, message=cast(str, normalized["message"]))

            failure_message = cast(str, normalized.get("message") or "账户同步失败")
            _log_sync_failure(instance, message=failure_message)
            response, status = jsonify_unified_error_message(
                failure_message,
                extra={"result": normalized, "instance_id": instance.id},
            )
            return response, status

        return self.safe_call(
            _execute,
            module="accounts_sync",
            action="sync_instance_accounts",
            public_error="账户同步失败,请重试",
            context={"instance_id": instance_id},
        )
