"""历史日志列表 Service.

职责:
- 组织 repository 调用并将 ORM 对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.history_logs_repository import HistoryLogsRepository
from app.core.types.history_logs import HistoryLogListItem, LogSearchFilters
from app.core.types.listing import PaginatedResult
from app.utils.time_utils import time_utils


class HistoryLogsListService:
    """历史日志列表业务编排服务."""

    def __init__(self, repository: HistoryLogsRepository | None = None) -> None:
        """初始化服务并注入日志仓库."""
        self._repository = repository or HistoryLogsRepository()

    def list_logs(self, filters: LogSearchFilters) -> PaginatedResult[HistoryLogListItem]:
        """分页列出历史日志."""
        page_result = self._repository.list_logs(filters)
        items: list[HistoryLogListItem] = []
        for log_entry in page_result.items:
            china_timestamp = time_utils.to_china(log_entry.timestamp) if log_entry.timestamp else None
            timestamp_display = (
                time_utils.format_china_time(china_timestamp, "%Y-%m-%d %H:%M:%S") if china_timestamp else "-"
            )
            items.append(
                HistoryLogListItem(
                    id=log_entry.id,
                    timestamp=china_timestamp.isoformat() if china_timestamp else None,
                    timestamp_display=timestamp_display,
                    level=log_entry.level.value if log_entry.level else None,
                    module=log_entry.module,
                    message=log_entry.message,
                    traceback=log_entry.traceback,
                    context=log_entry.context,
                ),
            )
        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )
