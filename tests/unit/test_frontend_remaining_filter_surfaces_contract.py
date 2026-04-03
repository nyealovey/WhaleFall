"""剩余筛选入口统一契约测试."""

from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


@pytest.mark.unit
def test_account_classification_statistics_template_uses_width_presets() -> None:
    content = _read_text("app/templates/accounts/classification_statistics.html")

    required_fragments = (
        "select_filter('账户分类', 'classification_id', 'classification_id', classification_options, selected_classification_id, '全部分类', width_preset='lg')",
        "select_filter('统计周期', 'period_type', 'period_type', period_type_options, selected_period_type, '选择周期', width_preset='sm', allow_empty=False)",
        "select_filter('数据库类型', 'db_type', 'db_type', database_type_options, selected_db_type, '全部类型', width_preset='sm')",
        "select_filter('实例', 'instance_id', 'instance_id', instance_options, selected_instance_id, '所有实例', width_preset='lg', disabled=(not selected_db_type))",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "col-md-2 col-12" not in content


@pytest.mark.unit
def test_instance_detail_filter_bands_use_shared_filter_band_semantics() -> None:
    template_content = _read_text("app/templates/instances/detail.html")
    shared_css = _read_text("app/static/css/components/filters/filter-common.css")
    page_css = _read_text("app/static/css/pages/instances/detail.css")

    required_template_fragments = (
        'class="instance-overview-band__controls filter-band"',
        'class="instance-overview-band__toolbar filter-band__form"',
        'class="form-check form-switch mb-0 instance-overview-band__toggle filter-band__toggle"',
        'class="input-group input-group-sm instance-overview-band__search filter-band__field filter-band__field--lg"',
        'class="instance-overview-band__realtime filter-band__meta"',
    )

    for fragment in required_template_fragments:
        assert fragment in template_content

    for fragment in (
        ".filter-band {",
        ".filter-band__form {",
        ".filter-band__toggle .form-check-label {",
        ".filter-band__field {",
        ".filter-band__field--lg {",
        ".filter-band__meta {",
    ):
        assert fragment in shared_css

    assert ".instance-overview-band__toolbar {" not in page_css
    assert ".instance-overview-band__search {" not in page_css
    assert ".instance-overview-band__realtime {" not in page_css


@pytest.mark.unit
def test_filter_docs_use_width_preset_language() -> None:
    standards_content = _read_text("docs/Obsidian/standards/ui/guide/color.md")
    prompt_content = _read_text("docs/prompts/frontend.md")

    for content in (standards_content, prompt_content):
        assert "width_preset" in content
        assert "col-md-2 col-12" not in content
