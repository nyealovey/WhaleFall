"""容量统计共享图例紧凑样式契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_capacity_chart_legend_css_supports_dense_scrollable_interactive_layout() -> None:
    content = _read_text("app/static/css/pages/capacity/databases.css")

    required_fragments = (
        ".capacity-chart-panel__legend {",
        "max-height:",
        "overflow-y: auto",
        '.capacity-chart-panel__legend[data-density="compact"] {',
        ".capacity-chart-legend__item {",
        "cursor: pointer",
        ".capacity-chart-legend__item--muted {",
        ".capacity-chart-legend__item:focus-visible {",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_capacity_chart_renderer_marks_dense_legends_and_clickable_items() -> None:
    content = _read_text("app/static/js/modules/views/components/charts/chart-renderer.js")

    required_fragments = (
        "container.dataset.seriesCount = String(datasets.length);",
        'container.dataset.density = datasets.length >= 12 ? "compact" : "default";',
        'item.type = "button";',
        'item.className = "capacity-chart-legend__item";',
        'item.setAttribute("aria-pressed",',
        'item.addEventListener("click",',
        "chart.setDatasetVisibility(index, nextVisible);",
    )

    for fragment in required_fragments:
        assert fragment in content
