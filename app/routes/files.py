"""文件导入导出路由.

统一处理全局的导出/上传相关接口.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable

from flask import Blueprint, Response, request
from flask_login import login_required

from app.constants import HttpHeaders
from app.constants.import_templates import (
    INSTANCE_IMPORT_TEMPLATE_HEADERS,
    INSTANCE_IMPORT_TEMPLATE_SAMPLE,
)
from app.errors import ValidationError
from app.models.unified_log import UnifiedLog
from app.services.files.account_export_service import AccountExportService
from app.services.files.instances_export_service import InstancesExportService
from app.services.files.logs_export_service import LogsExportService
from app.services.ledgers.database_ledger_service import DatabaseLedgerService
from app.types.accounts_ledgers import AccountFilters
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.decorators import admin_required, view_required
from app.utils.route_safety import safe_route_call
from app.utils.time_utils import time_utils

# 创建蓝图
files_bp = Blueprint("files", __name__)
_account_export_service = AccountExportService()
_instances_export_service = InstancesExportService()
_logs_export_service = LogsExportService()


def _parse_account_export_filters() -> AccountFilters:
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
    return AccountFilters(
        page=1,
        limit=1,
        search=search,
        instance_id=instance_id,
        is_locked=is_locked,
        is_superuser=is_superuser,
        plugin="",
        tags=tags,
        classification="",
        classification_filter="",
        db_type=normalized_db_type,
    )


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
        result = _account_export_service.export_accounts_csv(filters)
        return Response(
            result.content,
            mimetype=result.mimetype,
            headers={"Content-Disposition": f"attachment; filename={result.filename}"},
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
        result = _instances_export_service.export_instances_csv(search=search, db_type=db_type)
        return Response(
            result.content,
            mimetype=result.mimetype,
            headers={"Content-Disposition": f"attachment; filename={result.filename}"},
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
            instance = row.instance
            capacity = row.capacity
            status = row.sync_status
            tag_labels = ", ".join((tag.display_name or tag.name) for tag in row.tags).strip(", ")
            writer.writerow(
                sanitize_csv_row(
                    [
                        row.database_name or "-",
                        instance.name or "-",
                        instance.host or "-",
                        row.db_type or "-",
                        tag_labels or "-",
                        capacity.label or "未采集",
                        capacity.collected_at or "无",
                        status.label or "未知",
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
        logs = _logs_export_service.list_logs(request.args.to_dict())

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
