"""文件导入导出路由
统一处理全局的导出/上传相关接口.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

from flask import Blueprint, Response, request
from flask_login import login_required
from sqlalchemy import desc

from app import db
from app.constants import DatabaseType, HttpHeaders
from app.constants.import_templates import (
    INSTANCE_IMPORT_TEMPLATE_HEADERS,
    INSTANCE_IMPORT_TEMPLATE_SAMPLE,
)
from app.errors import SystemError, ValidationError
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.tag import Tag
from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.decorators import view_required
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils

# 创建蓝图
files_bp = Blueprint("files", __name__)


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
    try:
        db_type = request.args.get("db_type", type=str)
        search = request.args.get("search", "").strip()
        instance_id = request.args.get("instance_id", type=int)
        is_locked = request.args.get("is_locked")
        is_superuser = request.args.get("is_superuser")
        tags = [tag for tag in request.args.getlist("tags") if tag.strip()]

        from app.models.instance_account import InstanceAccount

        # 构建查询
        query = AccountPermission.query.join(InstanceAccount, AccountPermission.instance_account)
        query = query.filter(InstanceAccount.is_active.is_(True))

        if db_type and db_type != "all":
            query = query.filter(AccountPermission.db_type == db_type)

        if instance_id:
            query = query.filter(AccountPermission.instance_id == instance_id)

        if search:
            query = query.join(Instance, AccountPermission.instance_id == Instance.id)
            query = query.filter(
                db.or_(
                    AccountPermission.username.contains(search),
                    Instance.name.contains(search),
                    Instance.host.contains(search),
                ),
            )

        if is_locked is not None:
            if is_locked == "true":
                query = query.filter(AccountPermission.is_locked.is_(True))
            elif is_locked == "false":
                query = query.filter(AccountPermission.is_locked.is_(False))

        if is_superuser is not None:
            query = query.filter(AccountPermission.is_superuser == (is_superuser == "true"))

        if tags:
            try:
                query = query.join(Instance).join(Instance.tags).filter(Tag.name.in_(tags))
            except Exception as exc:
                log_error(
                    "导出账户时标签过滤失败",
                    module="files",
                    error=str(exc),
                )

        query = query.order_by(AccountPermission.username.asc())
        accounts = query.all()

        from app.models.account_classification import AccountClassificationAssignment

        classifications: dict[int, list[str]] = {}
        if accounts:
            account_ids = [account.id for account in accounts]
            assignments = AccountClassificationAssignment.query.filter(
                AccountClassificationAssignment.account_id.in_(account_ids),
                AccountClassificationAssignment.is_active.is_(True),
            ).all()

            for assignment in assignments:
                classifications.setdefault(assignment.account_id, []).append(assignment.classification.name)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["名称", "实例名称", "IP地址", "标签", "数据库类型", "分类", "锁定状态"])

        for account in accounts:
            instance = Instance.query.get(account.instance_id) if account.instance_id else None

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
                tags_display = ", ".join([tag.display_name for tag in instance.tags.all()])

            writer.writerow(
                [
                    username_display,
                    instance.name if instance else "",
                    instance.host if instance else "",
                    tags_display,
                    instance.db_type.upper() if instance else "",
                    classification_str,
                    lock_status,
                ],
            )

        output.seek(0)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"accounts_export_{timestamp}.csv"

        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        log_error("导出账户失败", module="files", error=str(exc))
        msg = "导出账户失败"
        raise SystemError(msg) from exc


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
    try:
        search = request.args.get("search", "", type=str)
        db_type = request.args.get("db_type", "", type=str)

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
                tags_display = ", ".join([tag.display_name for tag in instance.tags.all()])

            writer.writerow(
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
            )

        output.seek(0)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"instances_export_{timestamp}.csv"

        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        log_error("导出实例失败", module="files", error=str(exc))
        msg = "导出实例失败"
        raise SystemError(msg) from exc


@files_bp.route("/api/database-ledger-export")
@login_required
@view_required(permission="database_ledger.view")
def export_database_ledger() -> Response:
    """导出数据库台账列表为 CSV."""
    from app.services.ledgers.database_ledger_service import DatabaseLedgerService

    try:
        search = request.args.get("search", "", type=str).strip()
        db_type = request.args.get("db_type", "all", type=str)
        tags = [tag.strip() for tag in request.args.getlist("tags") if tag.strip()]
        if not tags:
            raw_tags = request.args.get("tags", "")
            if raw_tags:
                tags = [item.strip() for item in raw_tags.split(",") if item.strip()]

        service = DatabaseLedgerService()
        rows = service.iterate_all(search=search, db_type=db_type, tags=tags)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["数据库名称", "实例名称", "主机", "数据库类型", "标签", "最新容量", "最后采集时间", "同步状态"])

        for row in rows:
            instance = row.get("instance") or {}
            capacity = row.get("capacity") or {}
            status = row.get("sync_status") or {}
            tag_labels = ", ".join(
                (
                    tag.get("display_name")
                    or tag.get("name")
                    or ""
                )
                for tag in (row.get("tags") or [])
            ).strip(", ")
            writer.writerow(
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
            )

        output.seek(0)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"database_ledger_{timestamp}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        log_error("导出数据库台账失败", module="files", error=str(exc))
        msg = "导出数据库台账失败"
        raise SystemError(msg) from exc


@files_bp.route("/api/log-export", methods=["GET"])
@login_required
def export_logs() -> Response:
    """导出日志 API.

    支持 JSON 和 CSV 两种格式,可按级别、模块和时间范围筛选.

    Returns:
        JSON 或 CSV 文件响应.

    Raises:
        ValidationError: 当参数格式无效时抛出.
        SystemError: 当导出失败时抛出.

    Query Parameters:
        format: 导出格式('json' 或 'csv'),默认 'json'.
        level: 日志级别筛选,可选.
        module: 模块名称筛选,可选.
        start_time: 开始时间(ISO 8601 格式),可选.
        end_time: 结束时间(ISO 8601 格式),可选.
        limit: 最大导出数量,默认 1000.

    """
    try:
        format_type = request.args.get("format", "json")
        level = request.args.get("level")
        module = request.args.get("module")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        limit = int(request.args.get("limit", 1000))

        query = UnifiedLog.query

        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                query = query.filter(UnifiedLog.timestamp >= start_dt)
            except ValueError as exc:
                msg = "start_time 格式无效"
                raise ValidationError(msg) from exc

        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
                query = query.filter(UnifiedLog.timestamp <= end_dt)
            except ValueError as exc:
                msg = "end_time 格式无效"
                raise ValidationError(msg) from exc

        if level:
            try:
                log_level = LogLevel(level.upper())
                query = query.filter(UnifiedLog.level == log_level)
            except ValueError as exc:
                msg = "日志级别参数无效"
                raise ValidationError(msg) from exc

        if module:
            query = query.filter(UnifiedLog.module.like(f"%{module}%"))

        query = query.order_by(desc(UnifiedLog.timestamp)).limit(limit)
        logs = query.all()

        if format_type == "json":
            logs_data: list[dict[str, Any]] = []
            for log in logs:
                logs_data.append(
                    {
                        "id": log.id,
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                        "level": log.level.value if log.level else None,
                        "module": log.module,
                        "message": log.message,
                        "traceback": log.traceback,
                        "context": log.context,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    },
                )

            payload = {"logs": logs_data, "exported_at": time_utils.now().isoformat()}
            response = Response(
                json.dumps(payload, ensure_ascii=False, indent=2),
                mimetype="application/json; charset=utf-8",
            )
            response.headers["Content-Disposition"] = "attachment; filename=logs_export.json"
            return response

        if format_type == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "时间戳", "级别", "模块", "消息", "堆栈追踪", "上下文", "创建时间"])

            for log in logs:
                timestamp_str = time_utils.format_china_time(log.timestamp) if log.timestamp else ""
                created_at_str = time_utils.format_china_time(log.created_at) if log.created_at else ""

                context_str = ""
                if log.context and isinstance(log.context, dict):
                    context_parts = []
                    for key, value in log.context.items():
                        if (
                            value is not None
                            and value != ""
                            and key
                            not in ["request_id", "user_id", "url", "method", "ip_address", "user_agent"]
                        ):
                            context_parts.append(f"{key}: {value}")
                    context_str = "; ".join(context_parts)

                writer.writerow(
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
                )

            timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
            filename = f"logs_export_{timestamp}.csv"
            return Response(
                output.getvalue(),
                mimetype="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    HttpHeaders.CONTENT_TYPE: "text/csv; charset=utf-8",
                },
            )

        msg = "不支持的导出格式"
        raise ValidationError(msg)

    except Exception as exc:
        log_error(
            "导出日志失败",
            module="files",
            error=str(exc),
            format_type=request.args.get("format"),
            module_filter=request.args.get("module"),
            level=request.args.get("level"),
        )
        msg = "导出日志失败"
        raise SystemError(msg) from exc


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
    try:
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
    except Exception as exc:
        log_error("下载实例模板失败", module="files", error=str(exc))
        msg = "下载模板失败"
        raise SystemError(msg) from exc
