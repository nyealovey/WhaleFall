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

    assert "根目录 `DESIGN.md` 是视觉系统单一真源" in ui_readme
    assert "视觉口径以根目录 `DESIGN.md` 为准" in metric_doc
    assert "border/shadow/padding/typography" not in metric_doc
    assert "Semantic Color Contract" in color_doc
    assert "Visual palette and color roles are defined by root `DESIGN.md`." in color_doc
    assert "色彩 2-3-4 规则" not in color_doc


def test_dense_density_tokens_and_global_shell_are_available() -> None:
    variables = _read_text("app/static/css/variables.css")
    global_css = _read_text("app/static/css/global.css")
    table_css = _read_text("app/static/css/components/table.css")
    base_template = _read_text("app/templates/base.html")

    assert "--control-height-dense:" in variables
    assert "--control-padding-y-dense:" in variables
    assert "--control-height-compact:" not in variables
    assert "--control-height-regular:" not in variables
    assert "--page-spacing-dense:" in variables
    assert "--page-spacing-regular:" not in variables
    assert "--metric-card-min-height: 6.25rem;" in variables
    assert "--layout-max-width-wide: 1920px;" in variables
    assert "--gradient-" not in variables
    assert "--shadow-lg:" not in variables
    assert "--shadow-xl:" not in variables
    assert "--border-radius-xl:" not in variables
    assert "--border-radius-xxl:" not in variables
    assert 'font-variant-numeric: tabular-nums;' in global_css
    assert "page_density|default('dense')" in base_template
    assert '.main-content[data-density="compact"]' not in global_css
    assert '.main-content[data-density="compact"]' not in table_css
    assert '[data-density="dense"] .page-section + .page-section' in global_css
    assert '.main-content[data-density="dense"]' not in table_css
    assert ".main-content {" in table_css
    assert "--table-font-size: 11px;" in table_css


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
    regular_density = []
    for path in _iter_base_templates():
        content = path.read_text(encoding="utf-8")
        if "{% set page_density = 'compact' %}" in content:
            compact_density.append(_relative(path))
        if "{% set page_density = 'regular' %}" in content:
            regular_density.append(_relative(path))
        if "{% set page_density = 'dense' %}" not in content:
            missing_density.append(_relative(path))

    assert compact_density == []
    assert regular_density == []
    assert missing_density == []


def test_dense_console_removes_intro_header_copy() -> None:
    base_template = _read_text("app/templates/base.html")
    global_css = _read_text("app/static/css/global.css")
    page_header_macro = ROOT_DIR / "app/templates/components/ui/page_header.html"

    assert not page_header_macro.exists()
    assert "WhaleFall Operations" not in base_template
    assert "数据库资源与同步管理平台" not in base_template
    assert "app-topbar__identity" not in base_template
    assert "components/ui/page_header.html" not in base_template
    assert "app-topbar__identity" not in global_css
    assert "app-topbar__eyebrow" not in global_css
    assert "app-topbar__title" not in global_css
    assert "page-header" not in global_css
    assert "page-header__content" not in global_css
    assert "page-header__icon" not in global_css
    assert "page-header__eyebrow" not in global_css
    assert "page-header__title" not in global_css


def test_web_pages_remove_legacy_direct_page_header_calls() -> None:
    offenders = []
    for path in _iter_base_templates():
        content = path.read_text(encoding="utf-8")
        forbidden_tokens = [
            "components/ui/page_header.html",
            "page_header(",
            "call page_header",
            "page-header",
        ]
        hits = [token for token in forbidden_tokens if token in content]
        if hits:
            offenders.append(f"{_relative(path)}: {', '.join(hits)}")

    assert offenders == []


def test_runtime_css_removes_legacy_visual_tokens() -> None:
    forbidden_tokens = (
        "radial-gradient(",
        "linear-gradient(",
        "--gradient-",
        "var(--gradient",
        "border-radius-xl",
        "border-radius-xxl",
        "shadow-lg",
        "shadow-xl",
    )
    offenders = []
    for path in sorted((ROOT_DIR / "app/static/css").rglob("*.css")):
        if "vendor" in path.parts:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        hits = [token for token in forbidden_tokens if token in content]
        if hits:
            offenders.append(f"{_relative(path)}: {', '.join(hits)}")

    assert offenders == []


def test_global_component_css_is_not_reloaded_by_pages() -> None:
    globally_loaded_component_css = (
        "css/components/chips.css",
        "css/components/buttons.css",
        "css/components/forms.css",
        "css/components/table.css",
        "css/components/charts.css",
        "css/components/modals.css",
        "css/components/crud-modal.css",
        "css/components/metric-card.css",
        "css/components/status-pill.css",
        "css/components/progress.css",
        "css/components/filters/filter-common.css",
    )
    offenders = []

    for path in _iter_base_templates():
        content = path.read_text(encoding="utf-8")
        for css_path in globally_loaded_component_css:
            if css_path in content:
                offenders.append(f"{_relative(path)}: {css_path}")

    assert offenders == []


def test_tag_selector_stylesheet_is_loaded_by_pages_not_component_partial() -> None:
    component_partial = _read_text("app/templates/components/tag_selector.html")
    assert "css/components/tag-selector.css" not in component_partial

    offenders = []
    for path in _iter_base_templates():
        content = path.read_text(encoding="utf-8")
        if "components/tag_selector.html" in content and "css/components/tag-selector.css" not in content:
            offenders.append(_relative(path))

    assert offenders == []


def test_view_scripts_do_not_use_browser_alerts() -> None:
    offenders = []
    forbidden_patterns = ("global.alert(", "window.alert(", "alert(")

    for path in sorted((ROOT_DIR / "app/static/js/modules/views").rglob("*.js")):
        content = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_patterns:
            index = content.find(token)
            if index != -1:
                line = content.count("\n", 0, index) + 1
                offenders.append(f"{_relative(path)}:{line}: {token}")

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
    for path in sorted((ROOT_DIR / "app/static/js/modules/views").rglob("*.js")):
        content = path.read_text(encoding="utf-8", errors="ignore")
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
