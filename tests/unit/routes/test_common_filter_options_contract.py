import pytest


@pytest.mark.unit
def test_common_instances_options_contract(client) -> None:
    response = client.get("/common/api/instances-options")
    assert response.status_code == 404

    filtered = client.get("/common/api/instances-options?db_type=MYSQL")
    assert filtered.status_code == 404


@pytest.mark.unit
def test_common_databases_options_contract(client) -> None:
    response = client.get("/common/api/databases-options?instance_id=1&limit=100&offset=0")
    assert response.status_code == 404


@pytest.mark.unit
def test_common_dbtypes_options_contract(client) -> None:
    response = client.get("/common/api/dbtypes-options")
    assert response.status_code == 404
