"""Operations console redesign contracts."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_base_template_uses_left_sidebar_console_shell() -> None:
    content = _read_text("app/templates/base.html")

    required_fragments = (
        'class="app-layout"',
        'class="skip-link"',
        'href="#main-content"',
        'class="app-sidebar"',
        'class="app-sidebar__brand"',
        'class="app-sidebar__section-label"',
        'class="app-topbar"',
        'class="app-content"',
        'id="main-content"',
        "资源管理",
        "账户与权限",
        "实例统计",
        "账户统计",
        "数据库统计",
        "自动化",
    )

    for fragment in required_fragments:
        assert fragment in content, f"base.html 缺少 {fragment}"

    assert "navbar-expand" not in content
    assert 'class="app-nav' not in content
    assert "统计洞察" not in content


def test_global_css_defines_left_sidebar_shell_primitives() -> None:
    content = _read_text("app/static/css/global.css")

    required_fragments = (
        ".skip-link",
        ".app-layout",
        ".app-sidebar",
        ".app-sidebar__brand",
        ".app-sidebar__section-label",
        ".app-sidebar__link",
        ".app-topbar",
        ".app-content",
        ".app-content__inner",
    )

    for fragment in required_fragments:
        assert fragment in content, f"global.css 缺少 {fragment}"


def test_design_tokens_define_low_glare_operations_console_shell() -> None:
    content = _read_text("app/static/css/variables.css")

    required_tokens = (
        "--sidebar-width",
        "--topbar-height",
        "--surface-elevated",
        "--surface-overlay",
        "--focus-ring-color",
        "--wf-surface",
        "--wf-surface-muted",
        "--wf-border-color",
        "--wf-muted-color",
        "--wf-heading-color",
    )

    for token in required_tokens:
        assert token in content, f"variables.css 缺少 {token}"


def test_first_party_css_uses_dynamic_viewport_units() -> None:
    css_files = [
        path
        for path in (ROOT_DIR / "app/static/css").rglob("*.css")
        if "/vendor/" not in path.as_posix()
    ]

    offenders = [
        str(path.relative_to(ROOT_DIR))
        for path in css_files
        if "100vh" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
