import pytest

from app.schemas.instances import InstanceCreatePayload


@pytest.mark.unit
def test_instance_schema_coerces_tag_names_string_to_list() -> None:
    params = InstanceCreatePayload.model_validate(
        {
            "name": "demo",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "tag_names": "prod",
        },
    )
    assert params.tag_names == ["prod"]


@pytest.mark.unit
def test_instance_schema_accepts_tag_names_list() -> None:
    params = InstanceCreatePayload.model_validate(
        {
            "name": "demo",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "tag_names": ["prod", "mysql"],
        },
    )
    assert params.tag_names == ["prod", "mysql"]
