"""前端设计系统契约测试.

这些测试不校验像素级视觉，而是锁定本次前端升级必须落地的结构接口：
- 新的字体分层
- 新的设计 token
- 新的全局壳层命名
- 新的公共组件语义
"""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_design_tokens_define_industrial_console_language() -> None:
    content = _read_text("app/static/css/variables.css")

    required_tokens = (
        "--font-family-display",
        "--font-family-body",
        "--font-family-data",
        "--surface-canvas",
        "--surface-elevated",
        "--surface-panel",
        "--surface-panel-raised",
        "--border-subtle",
        "--border-strong",
        "--nav-pill-bg",
        "--nav-pill-active",
        "--signal-orange-500",
    )

    for token in required_tokens:
        assert token in content


def test_fonts_css_exposes_display_body_and_data_families() -> None:
    content = _read_text("app/static/css/fonts.css")

    required_families = (
        "IBM Plex Sans",
        "IBM Plex Sans Condensed",
        "IBM Plex Mono",
    )

    for family in required_families:
        assert f"font-family: '{family}'" in content


def test_fonts_css_drops_legacy_inter_face() -> None:
    content = _read_text("app/static/css/fonts.css")

    assert "font-family: 'Inter'" not in content


def test_base_template_uses_new_app_shell_and_navigation_structure() -> None:
    content = _read_text("app/templates/base.html")

    required_fragments = (
        'class="app-shell"',
        'class="app-layout"',
        'class="app-sidebar"',
        "app-sidebar__brand",
        "app-sidebar__nav",
        'class="app-workspace"',
        'class="app-topbar"',
        'class="app-footer"',
    )

    for fragment in required_fragments:
        assert fragment in content

    assert 'class="app-nav' not in content


def test_shared_components_promote_panel_language() -> None:
    header_content = _read_text("app/templates/components/ui/page_header.html")
    metric_content = _read_text("app/static/css/components/metric-card.css")
    filter_content = _read_text("app/static/css/components/filters/filter-common.css")
    global_content = _read_text("app/static/css/global.css")

    assert "page-header__eyebrow" in header_content
    assert "wf-metric-card__signal" in metric_content
    assert ".filter-card__toolbar" in filter_content
    assert ".page-header-actions .btn-icon" in global_content
    assert ".statistics-panel" in global_content


def test_statistics_panel_primitives_live_in_global_shell() -> None:
    global_content = _read_text("app/static/css/global.css")
    account_stats_content = _read_text("app/static/css/pages/accounts/statistics.css")
    instance_stats_content = _read_text("app/static/css/pages/instances/statistics.css")

    for fragment in (
        ".statistics-panel",
        ".statistics-panel__header",
        ".statistics-progress",
        ".statistics-empty",
    ):
        assert fragment in global_content

    for content in (account_stats_content, instance_stats_content):
        assert ".statistics-panel {" not in content
        assert ".statistics-progress {" not in content
        assert ".statistics-empty {" not in content


def test_account_classification_stats_reuses_shared_statistics_panel_shell() -> None:
    template_content = _read_text("app/templates/accounts/classification_statistics.html")
    page_content = _read_text("app/static/css/pages/accounts/classification_statistics.css")

    assert "statistics-panel acs-panel" in template_content
    assert "statistics-panel__header acs-panel__header" in template_content
    assert ".acs-panel {" not in page_content
    assert ".acs-panel__header {" not in page_content


def test_console_shell_owns_runtime_density_tokens() -> None:
    global_content = _read_text("app/static/css/global.css")
    forms_content = _read_text("app/static/css/components/forms.css")

    assert "--control-height:" in global_content
    assert "--control-padding-y:" in global_content
    assert "--control-padding-x:" in global_content
    assert "--control-height:" not in forms_content
    assert "--control-padding-y:" not in forms_content
    assert "--control-padding-x:" not in forms_content


def test_design_tokens_define_panel_and_metric_semantics() -> None:
    content = _read_text("app/static/css/variables.css")

    required_tokens = (
        "--panel-backdrop",
        "--panel-border-strong",
        "--panel-highlight",
        "--metric-hero-value",
        "--metric-card-min-height",
        "--density-control-height",
    )

    for token in required_tokens:
        assert token in content
