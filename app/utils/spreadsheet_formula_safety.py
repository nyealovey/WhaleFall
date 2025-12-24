"""鲸落 - CSV 导出安全工具.

用于防护 Spreadsheet Formula Injection (CSV 注入) 风险.
当单元格内容以 `= + - @` 等字符开头时,电子表格软件可能将其解析为公式并执行.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

SPREADSHEET_FORMULA_PREFIXES: Final[tuple[str, ...]] = ("=", "+", "-", "@")


def sanitize_csv_cell(value: object) -> object:
    """对 CSV 单元格值进行最小化清洗,避免被解析为公式.

    Args:
        value: 单元格原始值.

    Returns:
        清洗后的值.当输入为字符串且可能触发公式解析时,会在原始值前追加 `'` 前缀.

    """
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    if not value:
        return value

    stripped = value.lstrip()
    if stripped and stripped[0] in SPREADSHEET_FORMULA_PREFIXES:
        return f"'{value}"
    return value


def sanitize_csv_row(values: Iterable[object]) -> list[object]:
    """批量清洗 CSV 行数据.

    Args:
        values: 行数据序列.

    Returns:
        清洗后的行数据列表.

    """
    return [sanitize_csv_cell(value) for value in values]
