"""账户变更历史（全量页面）read APIs Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.core.types.account_change_logs import (
    AccountChangeLogListItem,
    AccountChangeLogsListFilters,
    AccountChangeLogStatistics,
)
from app.core.types.listing import PaginatedResult
from app.repositories.account_change_logs_repository import AccountChangeLogsRepository
from app.schemas.internal_contracts.account_change_log_diff_v1 import extract_diff_entries
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils


def _strip_username_prefix(message: object, *, username: str) -> str | None:
    """移除摘要中冗余的 `账户 <username>` 前缀(仅用于展示层)."""
    if message is None:
        return None
    text = message if isinstance(message, str) else str(message)
    if not text:
        return None
    prefix = f"账户 {username}"
    if not text.startswith(prefix):
        return text
    trimmed = text[len(prefix) :].lstrip()
    return trimmed or text


class HistoryAccountChangeLogsReadService:
    """账户变更历史读取服务."""

    def __init__(self, repository: AccountChangeLogsRepository | None = None) -> None:
        """初始化服务并注入仓库."""
        self._logger = get_system_logger()
        self._repository = repository or AccountChangeLogsRepository()

    def list_logs(self, filters: AccountChangeLogsListFilters) -> PaginatedResult[AccountChangeLogListItem]:
        """分页列出账户变更日志."""
        page_result = self._repository.list_logs(filters)
        items: list[AccountChangeLogListItem] = []
        for row in page_result.items:
            log_entry, instance_name, account_id = row

            raw_privilege_diff = getattr(log_entry, "privilege_diff", None)
            raw_other_diff = getattr(log_entry, "other_diff", None)

            try:
                privilege_entries = extract_diff_entries(raw_privilege_diff)
                other_entries = extract_diff_entries(raw_other_diff)
            except Exception as exc:
                self._logger.exception(
                    "account_change_log diff payload invalid",
                    module="history_account_change_logs",
                    log_id=getattr(log_entry, "id", None),
                    error=str(exc),
                )
                raise

            change_time_value = getattr(log_entry, "change_time", None)
            change_time_display = time_utils.format_china_time(change_time_value) if change_time_value else "未知"

            items.append(
                AccountChangeLogListItem(
                    id=int(getattr(log_entry, "id", 0) or 0),
                    account_id=(int(account_id) if account_id is not None else None),
                    instance_id=int(getattr(log_entry, "instance_id", 0) or 0),
                    instance_name=(str(instance_name) if instance_name else None),
                    db_type=str(getattr(log_entry, "db_type", "") or ""),
                    username=str(getattr(log_entry, "username", "") or ""),
                    change_type=str(getattr(log_entry, "change_type", "") or ""),
                    status=str(getattr(log_entry, "status", "") or ""),
                    message=_strip_username_prefix(
                        getattr(log_entry, "message", None),
                        username=str(getattr(log_entry, "username", "") or ""),
                    ),
                    change_time=change_time_display,
                    session_id=getattr(log_entry, "session_id", None),
                    privilege_diff_count=len(privilege_entries),
                    other_diff_count=len(other_entries),
                ),
            )

        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )

    def get_log_detail(self, log_id: int) -> dict[str, object]:
        """获取单条变更日志详情."""
        log_entry = self._repository.get_log(log_id)

        raw_privilege_diff = getattr(log_entry, "privilege_diff", None)
        raw_other_diff = getattr(log_entry, "other_diff", None)

        try:
            privilege_entries = extract_diff_entries(raw_privilege_diff)
            other_entries = extract_diff_entries(raw_other_diff)
        except Exception as exc:
            self._logger.exception(
                "account_change_log diff payload invalid",
                module="history_account_change_logs",
                log_id=log_id,
                error=str(exc),
            )
            raise

        change_time_value = getattr(log_entry, "change_time", None)
        change_time_display = time_utils.format_china_time(change_time_value) if change_time_value else "未知"

        payload: dict[str, object] = {
            "id": int(getattr(log_entry, "id", 0) or 0),
            "instance_id": int(getattr(log_entry, "instance_id", 0) or 0),
            "db_type": str(getattr(log_entry, "db_type", "") or ""),
            "username": str(getattr(log_entry, "username", "") or ""),
            "change_type": str(getattr(log_entry, "change_type", "") or ""),
            "change_time": change_time_display,
            "status": str(getattr(log_entry, "status", "") or ""),
            "message": _strip_username_prefix(
                getattr(log_entry, "message", None),
                username=str(getattr(log_entry, "username", "") or ""),
            ),
            "privilege_diff": privilege_entries,
            "other_diff": other_entries,
            "session_id": getattr(log_entry, "session_id", None),
        }
        return {"log": payload}

    def get_statistics(self, *, hours: int | None) -> AccountChangeLogStatistics:
        """获取统计汇总."""
        stats = self._repository.get_statistics(hours=hours)
        return AccountChangeLogStatistics(
            total_changes=stats["total_changes"],
            success_count=stats["success_count"],
            failed_count=stats["failed_count"],
            affected_accounts=stats["affected_accounts"],
        )
