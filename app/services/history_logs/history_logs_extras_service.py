"""历史日志附加读接口 Service.

覆盖 LogsPage 的模块选项、统计与详情 API.
"""

from __future__ import annotations

from datetime import timedelta

from app.core.types.history_logs import HistoryLogListItem, HistoryLogStatistics, HistoryLogTopModule
from app.repositories.history_logs_repository import HistoryLogsRepository
from app.utils.time_utils import time_utils


class HistoryLogsExtrasService:
    """日志模块/统计/详情读取服务."""

    def __init__(self, repository: HistoryLogsRepository | None = None) -> None:
        """初始化服务并注入日志仓库."""
        self._repository = repository or HistoryLogsRepository()

    def list_modules(self) -> list[str]:
        """列出日志模块列表."""
        return self._repository.list_modules()

    def get_statistics(self, *, hours: int) -> HistoryLogStatistics:
        """获取日志统计汇总."""
        window_hours = max(1, min(int(hours), 24 * 90))
        start_time = time_utils.now() - timedelta(hours=window_hours)
        total_logs, error_count, level_counts, top_modules = self._repository.fetch_statistics(start_time=start_time)

        top_module_items = [HistoryLogTopModule(module=module, count=count) for module, count in top_modules]
        warning_count = level_counts.get("WARNING", 0)
        info_count = level_counts.get("INFO", 0)
        debug_count = level_counts.get("DEBUG", 0)
        critical_count = level_counts.get("CRITICAL", 0)
        error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0

        return HistoryLogStatistics(
            total_logs=total_logs,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            debug_count=debug_count,
            critical_count=critical_count,
            level_distribution=level_counts,
            top_modules=top_module_items,
            error_rate=error_rate,
        )

    def get_log_detail(self, log_id: int) -> HistoryLogListItem:
        """获取日志详情."""
        log_entry = self._repository.get_log(log_id)
        china_timestamp = time_utils.to_china(log_entry.timestamp) if log_entry.timestamp else None
        timestamp_display = (
            time_utils.format_china_time(china_timestamp, "%Y-%m-%d %H:%M:%S") if china_timestamp else "-"
        )

        return HistoryLogListItem(
            id=log_entry.id,
            timestamp=china_timestamp.isoformat() if china_timestamp else None,
            timestamp_display=timestamp_display,
            level=log_entry.level.value if log_entry.level else None,
            module=log_entry.module,
            message=log_entry.message,
            traceback=log_entry.traceback,
            context=log_entry.context,
        )
