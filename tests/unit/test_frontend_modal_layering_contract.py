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


def _optional_css_block(content: str, selector: str) -> str:
    pattern = re.compile(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", re.S)
    match = pattern.search(content)
    return match.group("body") if match else ""


def test_modal_layering_contract_keeps_app_main_out_of_stacking_context() -> None:
    content = _read_text("app/static/css/global.css")

    app_shell_block = _css_block(content, ".app-shell")
    app_main_block = _optional_css_block(content, ".app-main")

    assert "isolation: isolate;" in app_shell_block
    assert "z-index:" not in app_main_block


def test_shared_modal_template_exposes_console_shell_contract() -> None:
    content = _read_text("app/templates/components/ui/modal.html")

    required_fragments = (
        "wf-modal",
        "wf-modal__dialog",
        "wf-modal__content",
        "wf-modal__header",
        "wf-modal__body",
        "wf-modal__footer",
        "data-modal-shell",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_modal_shell_styles_live_in_modal_component_css() -> None:
    global_css = _read_text("app/static/css/global.css")
    modal_css = _read_text("app/static/css/components/modals.css")

    forbidden_global_selectors = (
        ".modal-content",
        ".modal-header",
        ".danger-confirm-modal .modal-content",
        ".danger-confirm-modal .modal-header",
    )
    for selector in forbidden_global_selectors:
        assert selector not in global_css

    required_component_selectors = (
        ".wf-modal .modal-content",
        ".wf-modal .modal-header",
        ".wf-modal .modal-body",
        ".wf-modal .modal-footer",
        ".danger-confirm-modal .modal-content",
        ".danger-confirm-modal .modal-header",
    )
    for selector in required_component_selectors:
        assert selector in modal_css


def test_danger_confirm_modal_uses_component_state_not_inline_display() -> None:
    content = _read_text("app/templates/components/ui/danger_confirm_modal.html")

    assert 'style="display:' not in content
    assert "data-danger-confirm-result" in content
    assert "hidden" in content


def test_views_use_ui_modal_controller_instead_of_direct_bootstrap_modal() -> None:
    offenders: list[str] = []
    forbidden_patterns = (
        re.compile(r"new\s+(?:global\.)?bootstrap(?:Lib)?\.Modal\b"),
        re.compile(r"new\s+bootstrapLib\.Modal\b"),
        re.compile(r"\bbootstrap\.Modal\.getOrCreateInstance\b"),
    )

    for path in sorted((ROOT_DIR / "app/static/js/modules/views").rglob("*.js")):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if any(pattern.search(line) for pattern in forbidden_patterns):
                offenders.append(f"{path.relative_to(ROOT_DIR).as_posix()}:{lineno}: {line.strip()}")

    assert offenders == []
