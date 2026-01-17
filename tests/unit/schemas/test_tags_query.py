import pytest

from app.schemas.tags_query import TagOptionsQuery, TagsListQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_tags_list_query_defaults() -> None:
    query = validate_or_raise(TagsListQuery, {})
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 20
    assert filters.search == ""
    assert filters.category == ""
    assert filters.status_filter == ""


@pytest.mark.unit
def test_tags_list_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        TagsListQuery,
        {"page": 0, "limit": 999, "search": "  foo  ", "category": " env ", "status": " ACTIVE "},
    )
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 200
    assert filters.search == "foo"
    assert filters.category == "env"
    assert filters.status_filter == "active"


@pytest.mark.unit
def test_tag_options_query_strips_category() -> None:
    query = validate_or_raise(TagOptionsQuery, {"category": "  env  "})
    assert query.category == "env"
