"""Modal layering contract tests."""

from __future__ import annotations

import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def _css_block(content: str, selector: str) -> str:
    pattern = re.compile(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", re.S)
    match = pattern.search(content)
    assert match is not None, f"缺少 {selector} CSS 块"
    return match.group("body")


def test_modal_layering_contract_keeps_app_main_out_of_stacking_context() -> None:
    content = _read_text("app/static/css/global.css")

    app_shell_block = _css_block(content, ".app-shell")
    app_main_block = _css_block(content, ".app-main")

    assert "isolation: isolate;" in app_shell_block
    assert "z-index:" not in app_main_block
