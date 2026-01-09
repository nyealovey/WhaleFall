"""统一日志导出 Service.

职责:
- 解析查询参数并委托 repository 读取数据
- 负责导出文件内容渲染（json/csv）
- 不做 Query 细节、不返回 Response、不 commit
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.errors import ValidationError
from app.models.unified_log import LogLevel, UnifiedLog
from app.repositories.unified_logs_repository import UnifiedLogsRepository
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.time_utils import time_utils


@dataclass(frozen=True, slots=True)
class ExportResult:
    """日志导出结果(文件名 + 内容 + mimetype)."""

    filename: str
    content: str
    mimetype: str


class LogsExportService:
    """日志导出读取服务."""

    def __init__(self, repository: UnifiedLogsRepository | None = None) -> None:
        """初始化服务并注入日志仓库."""
        self._repository = repository or UnifiedLogsRepository()

    def list_logs(self, params: Mapping[str, str]) -> list[UnifiedLog]:
        """按参数查询可导出的日志列表."""
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        level = params.get("level")
        module = params.get("module")
        limit_raw = params.get("limit", "1000")

        start_dt = self._parse_iso_datetime(start_time, field="start_time") if start_time else None
        end_dt = self._parse_iso_datetime(end_time, field="end_time") if end_time else None
        log_level = self._parse_log_level(level) if level else None
        limit = self._parse_limit(limit_raw)

        return self._repository.list_logs_for_export(
            start_time=start_dt,
            end_time=end_dt,
            level=log_level,
            module=module,
            limit=limit,
        )

    def export(self, *, format_type: str, params: Mapping[str, str]) -> ExportResult:
        """导出日志为指定格式.

        Args:
            format_type: 导出格式(json/csv).
            params: 查询参数.

        Returns:
            ExportResult: 导出结果(供路由层生成附件响应).

        """
        logs = self.list_logs(params)

        if format_type == "json":
            return self._serialize_logs_to_json(logs)
        if format_type == "csv":
            return self._serialize_logs_to_csv(logs)

        raise ValidationError("不支持的导出格式")

    @staticmethod
    def _parse_iso_datetime(value: str, *, field: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            msg = f"{field} 格式无效"
            raise ValidationError(msg) from exc

    @staticmethod
    def _parse_log_level(value: str) -> LogLevel:
        try:
            return LogLevel(value.upper())
        except ValueError as exc:
            msg = "日志级别参数无效"
            raise ValidationError(msg) from exc

    @staticmethod
    def _parse_limit(value: str) -> int:
        try:
            limit = int(value)
        except (TypeError, ValueError) as exc:
            msg = "limit 参数无效"
            raise ValidationError(msg) from exc
        if limit <= 0:
            msg = "limit 参数无效"
            raise ValidationError(msg)
        return limit

    @staticmethod
    def _serialize_logs_to_json(logs: list[UnifiedLog]) -> ExportResult:
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
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        return ExportResult(
            filename="logs_export.json",
            content=content,
            mimetype="application/json; charset=utf-8",
        )

    @staticmethod
    def _serialize_logs_to_csv(logs: list[UnifiedLog]) -> ExportResult:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "时间戳", "级别", "模块", "消息", "堆栈追踪", "上下文", "创建时间"])

        ignored_keys = {"request_id", "user_id", "url", "method", "ip_address", "user_agent"}

        for log in logs:
            timestamp_str = time_utils.format_china_time(log.timestamp) if log.timestamp else ""
            created_at_str = time_utils.format_china_time(log.created_at) if log.created_at else ""

            context_str = ""
            if log.context and isinstance(log.context, dict):
                context_parts = [
                    f"{key}: {value}"
                    for key, value in log.context.items()
                    if value not in {None, ""} and key not in ignored_keys
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
        return ExportResult(
            filename="logs_export.csv",
            content=output.getvalue(),
            mimetype="text/csv; charset=utf-8",
        )
