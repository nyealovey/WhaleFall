"""Instances Import Template Service.

职责:
- 生成 Instances 导入模板 CSV 内容/文件名
- 不返回 Response、不 commit
"""

from __future__ import annotations

import csv
import io

from app.core.constants.import_templates import INSTANCE_IMPORT_TEMPLATE_HEADERS, INSTANCE_IMPORT_TEMPLATE_SAMPLE
from app.services.files.instances_export_service import CsvExportResult


class InstancesImportTemplateService:
    """实例导入模板生成服务."""

    def build_template_csv(self) -> CsvExportResult:
        """生成实例导入模板 CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(INSTANCE_IMPORT_TEMPLATE_HEADERS)
        writer.writerow(INSTANCE_IMPORT_TEMPLATE_SAMPLE)
        output.seek(0)

        return CsvExportResult(
            filename="instances_import_template.csv",
            content=output.getvalue(),
        )

