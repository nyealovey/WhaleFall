"""文件导入导出路由.

统一处理全局的导出/上传相关接口.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from typing import TYPE_CHECKING, Any, cast

from flask import Blueprint, Response, request
from flask_login import login_required
from sqlalchemy import desc, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app import db
from app.constants import DatabaseType, HttpHeaders
from app.constants.import_templates import (
    INSTANCE_IMPORT_TEMPLATE_HEADERS,
    INSTANCE_IMPORT_TEMPLATE_SAMPLE,
)
from app.errors import ValidationError
from app.models.account_classification import AccountClassificationAssignment
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.tag import Tag, instance_tags
from app.models.unified_log import LogLevel, UnifiedLog
from app.services.ledgers.database_ledger_service import DatabaseLedgerService
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.decorators import admin_required, view_required
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from app.types import QueryProtocol

    AccountQuery = QueryProtocol[AccountPermission]
    UnifiedLogQuery = QueryProtocol[UnifiedLog]
else:  # pragma: no cover - 仅供类型检查
    AccountQuery = Any
    UnifiedLogQuery = Any

# 创建蓝图
files_bp = Blueprint("files", __name__)


@dataclass(frozen=True)
class AccountExportFilters:
    """账户导出筛选条件."""

    db_type: str | None
    search: str
    instance_id: int | None
    is_locked: str | None
    is_superuser: str | None
    tags: list[str]


def _parse_account_export_filters() -> AccountExportFilters:
    args = request.args
    db_type = args.get("db_type", type=str)
    normalized_db_type = db_type if db_type not in {None, "", "all"} else None
    search = (args.get("search", "") or "").strip()
    instance_id = args.get("instance_id", type=int)
    is_locked = args.get("is_locked")
    is_superuser = args.get("is_superuser")
    tags = [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]
    if not tags:
        raw_tags = (args.get("tags", "") or "").strip()
        if raw_tags:
            tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    return AccountExportFilters(
        db_type=normalized_db_type,
        search=search,
        instance_id=instance_id,
        is_locked=is_locked,
        is_superuser=is_superuser,
        tags=tags,
    )


def _build_account_export_query(filters: AccountExportFilters) -> AccountQuery:
    base_query = AccountPermission.query.join(
        InstanceAccount,
        AccountPermission.instance_account_id == InstanceAccount.id,
    )
    query = cast("AccountQuery", base_query)
    query = query.filter(InstanceAccount.is_active.is_(True))

    if filters.db_type:
        query = query.filter(AccountPermission.db_type == filters.db_type)
    if filters.instance_id:
        query = query.filter(AccountPermission.instance_id == filters.instance_id)
    if filters.search:
        query = query.join(Instance, AccountPermission.instance_id == Instance.id)
        query = query.filter(
            or_(
                AccountPermission.username.contains(filters.search),
                Instance.name.contains(filters.search),
                Instance.host.contains(filters.search),
            ),
        )

    query = _apply_account_lock_filters(query, filters.is_locked, filters.is_superuser)
    query = _apply_account_tag_filter(query, filters.tags)
    return query.order_by(AccountPermission.username.asc())


def _apply_account_lock_filters(
    query: AccountQuery,
    is_locked: str | None,
    is_superuser: str | None,
) -> AccountQuery:
    if is_locked == "true":
        query = query.filter(AccountPermission.is_locked.is_(True))
    elif is_locked == "false":
        query = query.filter(AccountPermission.is_locked.is_(False))

    if is_superuser in {"true", "false"}:
        query = query.filter(AccountPermission.is_superuser == (is_superuser == "true"))
    return query


def _apply_account_tag_filter(query: AccountQuery, tags: list[str]) -> AccountQuery:
    if not tags:
        return query
    try:
        tag_name_column = cast(InstrumentedAttribute[str], Tag.name)
        return (
            query.join(Instance, AccountPermission.instance_id == Instance.id)
            .join(instance_tags, instance_tags.c.instance_id == Instance.id)
            .join(Tag, Tag.id == instance_tags.c.tag_id)
            .filter(tag_name_column.in_(tags))
        )
    except SQLAlchemyError as exc:  # pragma: no cover - 记录异常
        log_with_context(
            "warning",
            "账户导出标签过滤失败",
            module="files",
            action="apply_account_tag_filter",
            context={"tags": tags},
            extra={"error_message": str(exc)},
            include_actor=False,
        )
        return query


def _load_account_classifications(account_ids: list[int]) -> dict[int, list[str]]:
    if not account_ids:
        return {}
    assignments = AccountClassificationAssignment.query.filter(
        AccountClassificationAssignment.account_id.in_(account_ids),
        AccountClassificationAssignment.is_active.is_(True),
    ).all()
    if not assignments:
        return {}
    sorted_assignments = sorted(assignments, key=lambda item: item.account_id)
    return {
        account_id: [assignment.classification.name for assignment in group if assignment.classification]
        for account_id, group in groupby(sorted_assignments, key=lambda item: item.account_id)
    }


def _render_accounts_csv(accounts: Iterable[AccountPermission], classifications: dict[int, list[str]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["名称", "实例名称", "IP地址", "标签", "数据库类型", "分类", "锁定状态"])

    for account in accounts:
        instance = account.instance
        account_classifications = classifications.get(account.id, [])
        classification_str = ", ".join(account_classifications) if account_classifications else "未分类"

        if instance and instance.db_type in ["sqlserver", "oracle", "postgresql"]:
            username_display = account.username
        else:
            username_display = f"{account.username}@{account.instance.host if account.instance else '%'}"

        is_locked_flag = bool(account.is_locked)
        if is_locked_flag:
            lock_status = "已禁用" if instance and instance.db_type == DatabaseType.SQLSERVER else "已锁定"
        else:
            lock_status = "正常"

        tags_display = ""
        if instance and instance.tags:
            tags_iterable = instance.tags.all() if hasattr(instance.tags, "all") else instance.tags
            tags_display = ", ".join(tag.display_name for tag in tags_iterable)

        writer.writerow(
            sanitize_csv_row(
                [
                    username_display,
                    instance.name if instance else "",
                    instance.host if instance else "",
                    tags_display,
                    instance.db_type.upper() if instance else "",
                    classification_str,
                    lock_status,
                ],
            ),
        )

    output.seek(0)
    return output.getvalue()


def _build_log_query(params: Mapping[str, str]) -> UnifiedLogQuery:
    query = cast("UnifiedLogQuery", UnifiedLog.query)
    start_time = params.get("start_time")
    end_time = params.get("end_time")
    level = params.get("level")
    module = params.get("module")
    limit = int(params.get("limit", 1000))

    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
        except ValueError as exc:
            msg = "start_time 格式无效"
            raise ValidationError(msg) from exc
        query = query.filter(UnifiedLog.timestamp >= start_dt)

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
        except ValueError as exc:
            msg = "end_time 格式无效"
            raise ValidationError(msg) from exc
        query = query.filter(UnifiedLog.timestamp <= end_dt)

    if level:
        try:
            log_level = LogLevel(level.upper())
        except ValueError as exc:
            msg = "日志级别参数无效"
            raise ValidationError(msg) from exc
        query = query.filter(UnifiedLog.level == log_level)

    if module:
        query = query.filter(UnifiedLog.module.like(f"%{module}%"))

    return query.order_by(desc(UnifiedLog.timestamp)).limit(limit)


def _serialize_logs_to_json(logs: Iterable[UnifiedLog]) -> Response:
    logs_data = [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "level": log.level.value if log.level else None,
            "module": log.module,
            "message": log.message,
            "traceback": log.traceback,
            "context": log.context,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    payload = {"logs": logs_data, "exported_at": time_utils.now().isoformat()}
    response = Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json; charset=utf-8",
    )
    response.headers["Content-Disposition"] = "attachment; filename=logs_export.json"
    return response


def _serialize_logs_to_csv(logs: Iterable[UnifiedLog]) -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "时间戳", "级别", "模块", "消息", "堆栈追踪", "上下文", "创建时间"])

    for log in logs:
        timestamp_str = time_utils.format_china_time(log.timestamp) if log.timestamp else ""
        created_at_str = time_utils.format_china_time(log.created_at) if log.created_at else ""

        context_str = ""
        if log.context and isinstance(log.context, dict):
            context_parts = [
                f"{key}: {value}"
                for key, value in log.context.items()
                if value not in {None, ""}
                and key not in {"request_id", "user_id", "url", "method", "ip_address", "user_agent"}
            ]
            context_str = "; ".join(context_parts)

        writer.writerow(
            sanitize_csv_row(
                [
                    log.id,
                    timestamp_str,
                    log.level.value if log.level else "",
                    log.module or "",
                    log.message or "",
                    log.traceback or "",
                    context_str,
                    created_at_str,
                ],
            ),
        )

    output.seek(0)
    response = Response(output.getvalue(), mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=logs_export.csv"
    return response


@files_bp.route("/api/account-export")
@login_required
@view_required
def export_accounts() -> Response:
    """导出账户数据为 CSV.

    支持按数据库类型、实例、锁定状态、超级用户和标签筛选.

    Returns:
        CSV 文件响应.

    Raises:
        SystemError: 当导出失败时抛出.

    Query Parameters:
        db_type: 数据库类型筛选,可选.
        search: 搜索关键词,可选.
        instance_id: 实例 ID 筛选,可选.
        is_locked: 锁定状态筛选,可选.
        is_superuser: 超级用户筛选,可选.
        tags: 标签筛选(数组),可选.

    """
    filters = _parse_account_export_filters()

    def _execute() -> Response:
        query = _build_account_export_query(filters)
        accounts = query.all()
        classifications = _load_account_classifications([account.id for account in accounts])
        csv_content = _render_accounts_csv(accounts, classifications)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"accounts_export_{timestamp}.csv"
        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return safe_route_call(
        _execute,
        module="files",
        action="export_accounts",
        public_error="导出账户失败",
        context={
            "db_type": filters.db_type,
            "instance_id": filters.instance_id,
            "tags_count": len(filters.tags),
        },
    )


@files_bp.route("/api/instance-export")
@login_required
@view_required
def export_instances() -> Response:
    """导出实例数据为 CSV.

    支持按搜索关键词和数据库类型筛选.

    Returns:
        CSV 文件响应.

    Raises:
        SystemError: 当导出失败时抛出.

    Query Parameters:
        search: 搜索关键词,可选.
        db_type: 数据库类型筛选,可选.

    """
    search = request.args.get("search", "", type=str)
    db_type = request.args.get("db_type", "", type=str)

    def _execute() -> Response:
        query = Instance.query

        if search:
            query = query.filter(
                db.or_(
                    Instance.name.contains(search),
                    Instance.host.contains(search),
                    Instance.description.contains(search),
                ),
            )

        if db_type:
            query = query.filter(Instance.db_type == db_type)

        instances = query.all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "ID",
                "实例名称",
                "数据库类型",
                "主机地址",
                "端口",
                "数据库名",
                "标签",
                "状态",
                "描述",
                "凭据ID",
                "同步次数",
                "最后连接时间",
                "创建时间",
                "更新时间",
            ],
        )

        for instance in instances:
            tags_display = ""
            if instance.tags:
                tags_display = ", ".join(tag.display_name for tag in instance.tags.all())

            writer.writerow(
                sanitize_csv_row(
                    [
                        instance.id,
                        instance.name,
                        instance.db_type,
                        instance.host,
                        instance.port,
                        instance.database_name or "",
                        tags_display,
                        "启用" if instance.is_active else "禁用",
                        instance.description or "",
                        instance.credential_id or "",
                        instance.sync_count or 0,
                        (time_utils.format_china_time(instance.last_connected) if instance.last_connected else ""),
                        (time_utils.format_china_time(instance.created_at) if instance.created_at else ""),
                        (time_utils.format_china_time(instance.updated_at) if instance.updated_at else ""),
                    ],
                ),
            )

        output.seek(0)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"instances_export_{timestamp}.csv"

        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return safe_route_call(
        _execute,
        module="files",
        action="export_instances",
        public_error="导出实例失败",
        context={"search": search, "db_type": db_type},
    )


@files_bp.route("/api/database-ledger-export")
@login_required
@view_required(permission="database_ledger.view")
def export_database_ledger() -> Response:
    """导出数据库台账列表为 CSV."""
    search = request.args.get("search", "", type=str).strip()
    db_type = request.args.get("db_type", "all", type=str)
    tags = [tag.strip() for tag in request.args.getlist("tags") if tag.strip()]
    if not tags:
        raw_tags = request.args.get("tags", "")
        if raw_tags:
            tags = [item.strip() for item in raw_tags.split(",") if item.strip()]

    def _execute() -> Response:
        service = DatabaseLedgerService()
        rows = service.iterate_all(search=search, db_type=db_type, tags=tags)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "数据库名称",
                "实例名称",
                "主机",
                "数据库类型",
                "标签",
                "最新容量",
                "最后采集时间",
                "同步状态",
            ],
        )

        for row in rows:
            instance = row.get("instance") or {}
            capacity = row.get("capacity") or {}
            status = row.get("sync_status") or {}
            tag_labels = ", ".join((tag.get("display_name") or "") for tag in (row.get("tags") or [])).strip(", ")
            writer.writerow(
                sanitize_csv_row(
                    [
                        row.get("database_name", "-"),
                        instance.get("name", "-"),
                        instance.get("host", "-"),
                        row.get("db_type", "-"),
                        tag_labels or "-",
                        capacity.get("label", "未采集"),
                        capacity.get("collected_at", "无"),
                        status.get("label", "未知"),
                    ],
                ),
            )

        output.seek(0)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"database_ledger_{timestamp}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return safe_route_call(
        _execute,
        module="files",
        action="export_database_ledger",
        public_error="导出数据库台账失败",
        context={
            "search": search,
            "db_type": db_type,
            "tags_count": len(tags),
        },
    )


@files_bp.route("/api/log-export", methods=["GET"])
@admin_required
def export_logs() -> Response:
    """导出日志 API."""
    format_type = request.args.get("format", "json")

    def _execute() -> Response:
        query = _build_log_query(request.args.to_dict())
        logs = query.all()

        if format_type == "json":
            return _serialize_logs_to_json(logs)
        if format_type == "csv":
            return _serialize_logs_to_csv(logs)

        msg = "不支持的导出格式"
        raise ValidationError(msg)

    return safe_route_call(
        _execute,
        module="files",
        action="export_logs",
        public_error="导出日志失败",
        context={"format": format_type},
        expected_exceptions=(ValidationError,),
    )


@files_bp.route("/api/template-download")
@login_required
@view_required
def download_instances_template() -> Response:
    """下载实例批量导入模板.

    Returns:
        CSV 模板文件响应.

    Raises:
        SystemError: 当下载失败时抛出.

    """

    def _execute() -> Response:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(INSTANCE_IMPORT_TEMPLATE_HEADERS)
        writer.writerow(INSTANCE_IMPORT_TEMPLATE_SAMPLE)
        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=instances_import_template.csv",
                HttpHeaders.CONTENT_TYPE: "text/csv; charset=utf-8",
            },
        )

    return safe_route_call(
        _execute,
        module="files",
        action="download_instances_template",
        public_error="下载模板失败",
    )
