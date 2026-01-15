"""账户导出 Service.

职责:
- 组织 repository 调用并输出导出文件内容/文件名
- 不做 Query 细节、不返回 Response、不 commit
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.constants import DatabaseType
from app.core.types.accounts_ledgers import AccountFilters, AccountLedgerMetrics
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.time_utils import time_utils


@dataclass(frozen=True, slots=True)
class CsvExportResult:
    """CSV 导出结果."""

    filename: str
    content: str
    mimetype: str = "text/csv; charset=utf-8"


class AccountExportService:
    """账户导出读取服务."""

    def __init__(self, repository: AccountsLedgerRepository | None = None) -> None:
        """初始化服务并注入台账仓库."""
        self._repository = repository or AccountsLedgerRepository()

    def export_accounts_csv(self, filters: AccountFilters) -> CsvExportResult:
        """导出账户列表为 CSV."""
        accounts, metrics = self._repository.list_all_accounts(filters, sort_field="username", sort_order="asc")
        csv_content = self._render_accounts_csv(accounts, metrics)
        timestamp = time_utils.format_china_time(time_utils.now(), "%Y%m%d_%H%M%S")
        filename = f"accounts_export_{timestamp}.csv"
        return CsvExportResult(filename=filename, content=csv_content)

    @staticmethod
    def _render_accounts_csv(accounts: Sequence[object], metrics: AccountLedgerMetrics) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["名称", "实例名称", "IP地址", "标签", "数据库类型", "分类", "锁定状态"])

        tags_map = metrics.tags_map
        classifications_map = metrics.classifications_map

        for account in accounts:
            instance = getattr(account, "instance", None)
            instance_db_type = getattr(instance, "db_type", None) if instance else None

            account_classifications = classifications_map.get(getattr(account, "id", 0), [])
            classification_names = [item.name for item in account_classifications if getattr(item, "name", None)]
            classification_str = ", ".join(classification_names) if classification_names else "未分类"

            username = getattr(account, "username", "")
            instance_host = getattr(instance, "host", "%") if instance else "%"
            if instance and instance_db_type in {DatabaseType.SQLSERVER, DatabaseType.ORACLE, DatabaseType.POSTGRESQL}:
                username_display = username
            else:
                username_display = f"{username}@{instance_host}"

            is_locked_flag = bool(getattr(account, "is_locked", False))
            lock_status = "已锁定" if is_locked_flag else "正常"

            tags_list = tags_map.get(getattr(account, "instance_id", 0), [])
            tag_labels = [tag.display_name or tag.name for tag in tags_list]
            tags_display = ", ".join([label for label in tag_labels if label]).strip(", ")

            writer.writerow(
                sanitize_csv_row(
                    [
                        username_display,
                        getattr(instance, "name", "") if instance else "",
                        instance_host if instance else "",
                        tags_display,
                        (instance_db_type or "").upper() if instance_db_type else "",
                        classification_str,
                        lock_status,
                    ],
                ),
            )

        output.seek(0)
        return output.getvalue()
