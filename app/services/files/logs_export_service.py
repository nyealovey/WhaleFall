"""统一日志导出 Service.

职责:
- 解析查询参数并委托 repository 读取数据
- 不做 Query 细节、不返回 Response、不 commit
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from app.errors import ValidationError
from app.models.unified_log import LogLevel, UnifiedLog
from app.repositories.unified_logs_repository import UnifiedLogsRepository


class LogsExportService:
    """日志导出读取服务."""

    def __init__(self, repository: UnifiedLogsRepository | None = None) -> None:
        self._repository = repository or UnifiedLogsRepository()

    def list_logs(self, params: Mapping[str, str]) -> list[UnifiedLog]:
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
