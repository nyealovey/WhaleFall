"""实例导出 Service.

职责:
- 组织 repository 调用并输出导出文件内容/文件名
- 不做 Query 细节、不返回 Response、不 commit
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from app.repositories.instances_repository import InstancesRepository
from app.utils.spreadsheet_formula_safety import sanitize_csv_row
from app.utils.time_utils import time_utils


@dataclass(frozen=True, slots=True)
class CsvExportResult:
    filename: str
    content: str
    mimetype: str = "text/csv; charset=utf-8"


class InstancesExportService:
    """实例导出读取服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        self._repository = repository or InstancesRepository()

    def export_instances_csv(self, *, search: str, db_type: str) -> CsvExportResult:
        instances = self._repository.list_instances_for_export(search=search, db_type=db_type)
        tags_map = self._repository.fetch_tags_map([instance.id for instance in instances])

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
            tags_display = ", ".join(
                [
                    tag.display_name or tag.name
                    for tag in tags_map.get(instance.id, [])
                    if (tag.display_name or tag.name)
                ],
            ).strip(", ")

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
                        "启用" if instance.is_active else "停用",
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
        return CsvExportResult(filename=filename, content=output.getvalue())
