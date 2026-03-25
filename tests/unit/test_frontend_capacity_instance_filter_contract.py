"""容量页实例多选筛选契约测试."""

from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


@pytest.mark.unit
def test_capacity_chart_manager_uses_instance_assets_in_multiselect_options() -> None:
    manager_content = _read_text("app/static/js/modules/views/components/charts/manager.js")
    filters_content = _read_text("app/static/js/modules/views/components/charts/filters.js")

    required_manager_fragments = (
        'assetUrl: item?.asset_url || ""',
        "getOptionMeta: (item) => ({",
        "dbType: item?.db_type || \"\",",
    )
    for fragment in required_manager_fragments:
        assert fragment in manager_content

    required_filters_fragments = (
        'const meta = typeof getOptionMeta === "function" ? getOptionMeta(item) : {};',
        'option.classList.add("filter-multiselect__option--with-asset");',
        'asset.className = "filter-multiselect__asset";',
        'label.className = "filter-multiselect__label filter-multiselect__label--single-line";',
    )
    for fragment in required_filters_fragments:
        assert fragment in filters_content

    assert 'return dbType ? `${name} (${dbType})` : name;' not in manager_content


@pytest.mark.unit
def test_capacity_filter_styles_keep_instance_multiselect_single_line() -> None:
    filter_common = _read_text("app/static/css/components/filters/filter-common.css")
    capacity_page = _read_text("app/static/css/pages/capacity/databases.css")

    required_fragments = (
        ".filter-multiselect__option--with-asset {",
        ".filter-multiselect__asset {",
        ".filter-multiselect__label--single-line {",
        "white-space: nowrap;",
        "text-overflow: ellipsis;",
    )
    for fragment in required_fragments:
        assert fragment in filter_common or fragment in capacity_page

    assert "flex-wrap: wrap;" not in capacity_page
