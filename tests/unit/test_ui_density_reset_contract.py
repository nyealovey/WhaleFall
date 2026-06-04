from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "app/templates"


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def _iter_base_templates() -> list[Path]:
    return sorted(
        path
        for path in TEMPLATES_DIR.rglob("*.html")
        if '{% extends "base.html" %}' in path.read_text(encoding="utf-8")
    )


def _relative(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def test_stitch_design_doc_defines_cockpit_dense_exceptions() -> None:
    design_doc = _read_text("DESIGN.md")

    assert "DBA cockpit dense" in design_doc
    assert "Density: 8/10" in design_doc
    assert "Hero sections are not required for this product" in design_doc
    assert "Perpetual motion is banned in the operations console" in design_doc
    assert "Core data structures stay unchanged" in design_doc


def test_legacy_ui_docs_delegate_visual_rules_to_design_doc() -> None:
    ui_readme = _read_text("docs/Obsidian/standards/ui/README.md")
    metric_doc = _read_text("docs/Obsidian/standards/ui/design/metric-card.md")
    color_doc = _read_text("docs/Obsidian/standards/ui/guide/color.md")

    assert "`DESIGN.md` 是视觉系统单一真源" in ui_readme
    assert "视觉口径以根目录 `DESIGN.md` 为准" in metric_doc
    assert "border/shadow/padding/typography" not in metric_doc
    assert "色彩 2-3-4 规则" not in color_doc
    assert "配色口径以根目录 `DESIGN.md` 为准" in color_doc


def test_dense_density_tokens_and_global_shell_are_available() -> None:
    variables = _read_text("app/static/css/variables.css")
    global_css = _read_text("app/static/css/global.css")
    table_css = _read_text("app/static/css/components/table.css")

    assert "--control-height-dense:" in variables
    assert "--control-padding-y-dense:" in variables
    assert "--page-spacing-dense:" in variables
    assert "--metric-card-min-height: 6.25rem;" in variables
    assert "--layout-max-width-wide: 1920px;" in variables
    assert 'font-variant-numeric: tabular-nums;' in global_css
    assert '.main-content[data-density="dense"]' in global_css
    assert '.main-content[data-density="dense"]' in table_css


def test_sample_pages_opt_into_dense_without_changing_data_hooks() -> None:
    dashboard = _read_text("app/templates/dashboard/overview.html")
    risk_center = _read_text("app/templates/risk_center/index.html")
    accounts = _read_text("app/templates/accounts/ledgers.html")

    assert "{% set page_density = 'dense' %}" in dashboard
    assert "{% set page_density = 'dense' %}" in risk_center
    assert "{% set page_density = 'dense' %}" in accounts

    assert "dashboard-cockpit-grid" in dashboard
    assert "data-risk-center-root" in risk_center
    assert "data-db-type-map" in risk_center
    assert "accounts-page-root" in accounts
    assert "accounts-grid-stage" in accounts
    assert "accounts-grid" in accounts


def test_all_web_pages_follow_dense_console_density() -> None:
    missing_density = []
    compact_density = []
    for path in _iter_base_templates():
        content = path.read_text(encoding="utf-8")
        if "{% set page_density = 'compact' %}" in content:
            compact_density.append(_relative(path))
        if "{% set page_density = 'dense' %}" not in content:
            missing_density.append(_relative(path))

    assert compact_density == []
    assert missing_density == []


def test_dense_console_removes_intro_header_copy() -> None:
    base_template = _read_text("app/templates/base.html")
    page_header_macro = _read_text("app/templates/components/ui/page_header.html")
    global_css = _read_text("app/static/css/global.css")

    assert "WhaleFall Operations" not in base_template
    assert "数据库资源与同步管理平台" not in base_template
    assert "app-topbar__identity" not in base_template
    assert "page-header__content" not in page_header_macro
    assert "page-header__eyebrow" not in page_header_macro
    assert "<h1>{{ title }}</h1>" not in page_header_macro
    assert "page-header__actions" in page_header_macro
    assert "app-topbar__identity" not in global_css
    assert "app-topbar__eyebrow" not in global_css
    assert "app-topbar__title" not in global_css
    assert "page-header__content" not in global_css
    assert "page-header__icon" not in global_css
    assert "page-header__eyebrow" not in global_css
    assert "page-header__title" not in global_css


def test_web_pages_remove_legacy_direct_page_header_calls() -> None:
    offenders = []
    for path in _iter_base_templates():
        content = path.read_text(encoding="utf-8")
        if "{{ page_header(" in content:
            offenders.append(_relative(path))

    assert offenders == []


def test_auth_and_about_pages_use_console_surfaces_not_marketing_hero() -> None:
    login_css = _read_text("app/static/css/pages/auth/login.css")
    about_template = _read_text("app/templates/about.html")
    about_css = _read_text("app/static/css/pages/about.css")

    assert "WhaleFall\\A 数据同步平台" not in login_css
    assert "inset: 0 42% 0 0" not in login_css
    assert "about-hero" not in about_template
    assert ".about-hero" not in about_css
    assert 'height="200"' not in about_template


def test_dashboard_risk_alert_board_has_gap_after_metrics() -> None:
    dashboard_css = _read_text("app/static/css/pages/dashboard/overview.css")

    assert ".dashboard-metrics + .risk-alert-board" in dashboard_css
    assert "margin-top: var(--page-spacing-dense);" in dashboard_css


def test_sidebar_navigation_preserves_active_item_visibility_after_reload() -> None:
    base_template = _read_text("app/templates/base.html")
    sidebar_scroll_js = _read_text("app/static/js/modules/ui/sidebar-scroll.js")

    assert 'data-sidebar-scroll-root' in base_template
    assert "js/modules/ui/sidebar-scroll.js" in base_template
    assert base_template.index("js/modules/ui/sidebar-scroll.js") < base_template.index(
        "js/bootstrap/page-loader.js"
    )

    assert "wf.sidebar.scrollTop" in sidebar_scroll_js
    assert "sessionStorage" in sidebar_scroll_js
    assert ".app-sidebar__link.is-active" in sidebar_scroll_js
    assert "getBoundingClientRect" in sidebar_scroll_js
    assert ".scrollTop" in sidebar_scroll_js
    assert "scrollIntoView" not in sidebar_scroll_js


def test_risk_center_uses_data_weighted_bars_without_inline_width() -> None:
    template = _read_text("app/templates/risk_center/index.html")
    script = _read_text("app/static/js/modules/views/risk-center/index.js")

    assert 'style="width:' not in template
    assert 'style="width:' not in script
    assert "data-risk-total" in template
    assert "data-risk-high" in template
    assert "data-risk-medium" in template
    assert "data-risk-low" in template
    assert "data-risk-ok" in template
    assert "applyRiskBarWeights" in script
    assert "dataset.riskHigh" in script


def test_dashboard_resource_bars_use_data_attributes_without_inline_width() -> None:
    template = _read_text("app/templates/dashboard/overview.html")
    script = _read_text("app/static/js/modules/views/dashboard/overview.js")

    assert 'style="width:' not in template
    assert "data-resource-percent" in template
    assert "initResourceBars" in script
    assert "dataset.resourcePercent" in script


def test_progress_bars_use_data_attributes_without_template_inline_width() -> None:
    base_template = _read_text("app/templates/base.html")
    progress_js = _read_text("app/static/js/modules/ui/progress-bars.js")
    templates_with_progress = (
        "app/templates/accounts/statistics.html",
        "app/templates/databases/statistics.html",
        "app/templates/instances/statistics.html",
        "app/templates/tags/bulk/assign.html",
    )

    offenders = []
    for path in TEMPLATES_DIR.rglob("*.html"):
        content = path.read_text(encoding="utf-8")
        if 'style="width:' in content or "style='width:" in content:
            offenders.append(_relative(path))
    assert offenders == []

    assert "js/modules/ui/progress-bars.js" in base_template
    assert base_template.index("js/modules/ui/progress-bars.js") < base_template.index(
        "js/bootstrap/page-loader.js"
    )
    assert "data-progress-percent" in progress_js
    assert "applyProgressBars" in progress_js
    assert ".style.width" in progress_js

    for template_path in templates_with_progress:
        assert "data-progress-percent" in _read_text(template_path)


def test_core_components_are_tuned_for_dense_operations_ui() -> None:
    metric_css = _read_text("app/static/css/components/metric-card.css")
    filter_css = _read_text("app/static/css/components/filters/filter-common.css")
    button_css = _read_text("app/static/css/components/buttons.css")

    assert '.main-content[data-density="dense"] .wf-metric-card' in metric_css
    assert "min-height: var(--metric-card-min-height);" in metric_css
    assert '.main-content[data-density="dense"] .filter-card .card-body' in filter_css
    assert '.main-content[data-density="dense"] .btn-icon' in button_css
    assert "border-radius: var(--border-radius-sm);" in button_css
