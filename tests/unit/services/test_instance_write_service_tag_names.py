import pytest

from app.errors import ValidationError
from app.services.instances.instance_write_service import InstanceWriteService


@pytest.mark.unit
def test_instance_write_service_rejects_tag_names_string() -> None:
    with pytest.raises(ValidationError):
        InstanceWriteService._normalize_tag_names({"tag_names": "a,b"})


@pytest.mark.unit
def test_instance_write_service_accepts_tag_names_list() -> None:
    assert InstanceWriteService._normalize_tag_names({"tag_names": ["prod", "mysql"]}) == ["prod", "mysql"]
