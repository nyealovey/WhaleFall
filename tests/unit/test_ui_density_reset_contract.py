from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


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


def test_core_components_are_tuned_for_dense_operations_ui() -> None:
    metric_css = _read_text("app/static/css/components/metric-card.css")
    filter_css = _read_text("app/static/css/components/filters/filter-common.css")
    button_css = _read_text("app/static/css/components/buttons.css")

    assert '.main-content[data-density="dense"] .wf-metric-card' in metric_css
    assert "min-height: var(--metric-card-min-height);" in metric_css
    assert '.main-content[data-density="dense"] .filter-card .card-body' in filter_css
    assert '.main-content[data-density="dense"] .btn-icon' in button_css
    assert "border-radius: var(--border-radius-sm);" in button_css
