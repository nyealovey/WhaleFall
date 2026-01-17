"""CSV 导出结果类型.

为 files 域的导出/模板服务提供统一的返回结构,避免重复定义。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CsvExportResult:
    """CSV 导出结果."""

    filename: str
    content: str
    mimetype: str = "text/csv; charset=utf-8"
