"""Button system contract tests."""

from __future__ import annotations

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8", errors="ignore")


def _iter_files(relative_root: str, suffixes: set[str]) -> list[Path]:
    root = ROOT_DIR / relative_root
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix in suffixes)


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def _css_block(content: str, selector_prefix: str) -> str:
    pattern = re.compile(rf"{re.escape(selector_prefix)}[^\{{]*\{{(?P<body>.*?)\n\}}", re.S)
    match = pattern.search(content)
    assert match is not None, f"找不到 CSS 块: {selector_prefix}"
    return match.group("body")


def test_button_system_defines_shared_roles_and_size_tokens() -> None:
    variables = _read_text("app/static/css/variables.css")
    buttons_css = _read_text("app/static/css/components/buttons.css")
    global_css = _read_text("app/static/css/global.css")
    table_css = _read_text("app/static/css/components/table.css")

    required_tokens = (
        "--button-height-command",
        "--button-height-form",
        "--button-height-table",
        "--button-icon-size-command",
        "--button-icon-size-table",
        "--button-group-gap",
        "--command-to-content-gap",
    )
    for token in required_tokens:
        assert token in variables

    required_button_roles = (
        ".btn-command",
        ".btn-table-action",
        ".btn-segment",
        ".btn-form-action",
        ".btn-quick-action",
        ".command-action-bar",
        ".table-action-bar",
        ".segmented-control",
        ".form-action-row",
    )
    for selector in required_button_roles:
        assert selector in buttons_css

    assert "--command-to-content-gap" in global_css
    assert ".table-action-bar" in table_css
    assert ".btn-table-action" in table_css


def test_primary_buttons_keep_filled_background_across_hover_and_active_states() -> None:
    buttons_css = _read_text("app/static/css/components/buttons.css")
    primary_block = _css_block(buttons_css, ".btn-primary")
    transparent_state_vars = (
        "--bs-btn-bg",
        "--bs-btn-border-color",
        "--bs-btn-hover-bg",
        "--bs-btn-hover-border-color",
        "--bs-btn-active-bg",
        "--bs-btn-active-border-color",
    )

    for state_var in transparent_state_vars:
        declaration = re.search(rf"{re.escape(state_var)}:\s*([^;]+);", primary_block)
        assert declaration is not None, f".btn-primary 缺少 {state_var}"
        assert declaration.group(1).strip() != "transparent", f".btn-primary {state_var} 不能是 transparent"


def test_fixed_height_button_roles_center_content() -> None:
    buttons_css = _read_text("app/static/css/components/buttons.css")
    role_selectors = (
        ".btn-command",
        ".btn-form-action",
        ".btn-table-action",
        ".btn-segment",
    )

    for selector in role_selectors:
        block = _css_block(buttons_css, selector)
        for declaration in (
            "display: inline-flex;",
            "align-items: center;",
            "justify-content: center;",
            "white-space: nowrap;",
            "vertical-align: middle;",
        ):
            assert declaration in block, f"{selector} 缺少 {declaration}"


def test_segmented_active_state_and_scripts_do_not_use_legacy_bootstrap_class_toggles() -> None:
    buttons_css = _read_text("app/static/css/components/buttons.css")
    active_block = _css_block(buttons_css, ".btn-segment.active")
    assert "border-color: var(--accent-primary);" in active_block

    forbidden_tokens = (
        'classList.remove("btn-primary"',
        'classList.add("btn-outline-primary", "border-2", "fw-bold")',
        'classList.toggle("btn-primary"',
        'classList.toggle("btn-outline-primary"',
        'classList.toggle("border-2"',
        'classList.toggle("fw-bold"',
    )
    offenders: list[str] = []

    for path in _iter_files("app/static/js/modules/views", {".js"}):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_tokens:
            index = content.find(token)
            if index != -1:
                offenders.append(
                    f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, index)}: "
                    f"分段按钮状态仍使用旧 Bootstrap class: {token}"
                )

    assert offenders == []


def test_console_command_decks_use_command_action_bar_not_bootstrap_groups() -> None:
    offenders: list[str] = []

    for path in _iter_files("app/templates", {".html"}):
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if "console-command-deck" not in line:
                continue
            block = "\n".join(lines[index : index + 14])
            if "btn-group" in block:
                offenders.append(f"{path.relative_to(ROOT_DIR).as_posix()}:{index + 1}: console-command-deck 包含 btn-group")
            if "<button" in block or "<a " in block:
                if "command-action-bar" not in block:
                    offenders.append(
                        f"{path.relative_to(ROOT_DIR).as_posix()}:{index + 1}: console-command-deck 缺少 command-action-bar"
                    )

    assert offenders == []


def test_grid_row_actions_use_table_action_bar_and_table_button_role() -> None:
    offenders: list[str] = []
    legacy_group_patterns = (
        re.compile(r"<div\s+class=[\"']btn-group(?:\s+btn-group-sm)?[\"'][^>]*role=[\"']group[\"']"),
        re.compile(r"<div\s+class=[\"']btn-group\s+btn-group-sm[\"']"),
    )
    icon_action_tag = re.compile(r"<(?:button|a|span)\b[^>]*\bbtn-icon\b[^>]*>", re.S)

    for path in _iter_files("app/static/js/modules/views", {".js"}):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in legacy_group_patterns:
            for match in pattern.finditer(content):
                offenders.append(
                    f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, match.start())}: "
                    "行内操作仍使用 btn-group"
                )
        for match in icon_action_tag.finditer(content):
            tag = match.group(0)
            if "btn-table-action" not in tag and "ag-status-dashboard__tab" not in tag:
                offenders.append(
                    f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, match.start())}: "
                    "JS 生成的图标按钮缺少 btn-table-action"
                )

    assert offenders == []


def test_dynamic_view_buttons_do_not_use_bootstrap_size_shortcuts() -> None:
    offenders: list[str] = []
    button_with_btn_sm = re.compile(r"<(?:button|a|span)\b[^>]*\bbtn-sm\b[^>]*>", re.S)

    for path in _iter_files("app/static/js/modules/views", {".js"}):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for match in button_with_btn_sm.finditer(content):
            offenders.append(
                f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, match.start())}: "
                "动态按钮仍使用 btn-sm"
            )

    assert offenders == []


def test_icon_only_buttons_have_aria_labels() -> None:
    offenders: list[str] = []
    icon_tag = re.compile(r"<(?:button|a|span)\b[^>]*\bbtn-icon\b[^>]*>", re.S)

    for relative_root, suffixes in (
        ("app/templates", {".html"}),
        ("app/static/js/modules/views", {".js"}),
    ):
        for path in _iter_files(relative_root, suffixes):
            content = path.read_text(encoding="utf-8", errors="ignore")
            for match in icon_tag.finditer(content):
                tag = match.group(0)
                if "aria-label=" not in tag:
                    offenders.append(
                        f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, match.start())}: "
                        "btn-icon 缺少 aria-label"
                    )

    assert offenders == []


def test_segmented_controls_use_segmented_button_contract() -> None:
    offenders: list[str] = []
    chip_group = re.compile(r"<div\b[^>]*\bchip-toggle-group\b[^>]*>", re.S)
    db_type_button = re.compile(r"<button\b[^>]*\bdata-db-type-btn\b[^>]*>", re.S)
    chart_group = re.compile(r"<div\b[^>]*class=[\"'][^\"']*\bbtn-group\b[^\"']*[\"'][^>]*role=[\"']group[\"']", re.S)

    for path in _iter_files("app/templates", {".html"}):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for match in chip_group.finditer(content):
            tag = match.group(0)
            if "segmented-control" not in tag:
                offenders.append(
                    f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, match.start())}: "
                    "chip-toggle-group 缺少 segmented-control"
                )
        for match in db_type_button.finditer(content):
            tag = match.group(0)
            if "btn-segment" not in tag:
                offenders.append(
                    f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, match.start())}: "
                    "data-db-type-btn 缺少 btn-segment"
                )
        for match in chart_group.finditer(content):
            tag = match.group(0)
            if "segmented-control" not in tag and "command-action-bar" not in tag and "table-action-bar" not in tag:
                offenders.append(
                    f"{path.relative_to(ROOT_DIR).as_posix()}:{_line_number(content, match.start())}: "
                    "分段/操作组仍使用裸 btn-group"
                )

    assert offenders == []
