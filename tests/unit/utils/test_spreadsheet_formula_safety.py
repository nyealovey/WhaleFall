"""CSV 导出公式注入防护工具的单元测试."""

import pytest

from app.utils.spreadsheet_formula_safety import sanitize_csv_cell, sanitize_csv_row


@pytest.mark.unit
def test_sanitize_csv_cell_returns_empty_string_for_none() -> None:
    """验证 None 会被转换为空字符串."""
    assert sanitize_csv_cell(None) == ""


@pytest.mark.unit
def test_sanitize_csv_cell_prefixes_risky_values() -> None:
    """验证危险前缀会被统一添加 `'` 前缀."""
    cases: list[tuple[str, str]] = [
        ("=1+1", "'=1+1"),
        ("+SUM(1,2)", "'+SUM(1,2)"),
        ("-1+2", "'-1+2"),
        ("@cmd", "'@cmd"),
        ('  =HYPERLINK("http://example.com")', '\'  =HYPERLINK("http://example.com")'),
        ("\t=cmd()", "'\t=cmd()"),
    ]
    for raw, expected in cases:
        assert sanitize_csv_cell(raw) == expected


@pytest.mark.unit
def test_sanitize_csv_cell_keeps_safe_values() -> None:
    """验证普通字符串与非字符串不会被修改."""
    assert sanitize_csv_cell("normal") == "normal"
    assert sanitize_csv_cell(123) == 123


@pytest.mark.unit
def test_sanitize_csv_row_sanitizes_each_cell() -> None:
    """验证 sanitize_csv_row 会逐个清洗行数据."""
    row = sanitize_csv_row(["=1+1", "normal", 1, None])
    assert row == ["'=1+1", "normal", 1, ""]
