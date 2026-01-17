"""数据库台账导出 Service.

职责:
- 组织台账 service 调用并渲染 CSV 导出内容
- 不返回 Response、不 commit
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from app.core.types.ledgers import DatabaseLedgerItem
from app.services.files.csv_export_result import CsvExportResult
from app.services.ledgers.database_ledger_service import DatabaseLedgerService
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.time_utils import time_utils


class DatabaseLedgerExportService:
    """数据库台账导出服务."""

    def __init__(self, ledger_service: DatabaseLedgerService | None = None) -> None:
        """初始化导出服务.

        Args:
            ledger_service: 可选注入台账 service,默认使用 `DatabaseLedgerService()`.

        """
        self._ledger_service = ledger_service or DatabaseLedgerService()

    def export_database_ledger_csv(
        self,
        *,
        search: str,
        db_type: str,
        instance_id: int | None,
        tags: list[str],
    ) -> CsvExportResult:
        """导出数据库台账为 CSV."""
        rows = self._ledger_service.iterate_all(
            search=search,
            db_type=db_type,
            instance_id=instance_id,
            tags=tags,
        )
        csv_content = self._render_csv(rows)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"database_ledger_{timestamp}.csv"
        return CsvExportResult(filename=filename, content=csv_content)

    @staticmethod
    def _render_csv(rows: Iterable[DatabaseLedgerItem]) -> str:
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
        return output.getvalue()
