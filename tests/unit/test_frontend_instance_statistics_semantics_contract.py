"""实例统计页总数/现存数口径契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instances_statistics_template_uses_total_for_cards_and_current_for_distributions() -> None:
    content = _read_text("app/templates/instances/statistics.html")

    required_fragments = (
        "{% set total_instances = stats.total_instances or 0 %}",
        "{% set current_instances = stats.current_instances or 0 %}",
        "{% set active_rate = (active_instances / total_instances * 100) if total_instances else 0 %}",
        "{% set deleted_rate = (deleted_instances / total_instances * 100) if total_instances else 0 %}",
        "{% set top_db_type_share = (top_db_type.count / current_instances * 100) if top_db_type and current_instances else 0 %}",
        "{% set percent = (stat.count / current_instances * 100) if current_instances > 0 else 0 %}",
        "title=\"Top 类型现存占比\"",
        "aria-label=\"Top 类型现存占比\"",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_instances_statistics_frontend_uses_current_instances_for_top_share_and_store_defaults() -> None:
    stats_js = _read_text("app/static/js/modules/views/instances/statistics.js")
    store_js = _read_text("app/static/js/modules/stores/instance_store.js")

    stats_fragments = (
        "const total = Number(stats?.total_instances ?? 0) || 0;",
        "const current = Number(stats?.current_instances ?? 0) || 0;",
        "formatPercent(total > 0 ? active / total : 0",
        "formatPercent(total > 0 ? deleted / total : 0",
        "formatPercent(current > 0 ? topCount / current : 0",
    )
    for fragment in stats_fragments:
        assert fragment in stats_js

    assert "current_instances: 0," in store_js
