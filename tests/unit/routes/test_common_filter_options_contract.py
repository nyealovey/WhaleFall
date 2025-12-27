import pytest


@pytest.mark.unit
def test_common_instances_options_contract(client) -> None:
    response = client.get("/common/api/instances-options")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"

    filtered = client.get("/common/api/instances-options?db_type=MYSQL")
    assert filtered.status_code == 410
    filtered_payload = filtered.get_json()
    assert isinstance(filtered_payload, dict)
    assert filtered_payload.get("message_code") == "API_GONE"


@pytest.mark.unit
def test_common_databases_options_contract(client) -> None:
    response = client.get("/common/api/databases-options?instance_id=1&limit=100&offset=0")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"


@pytest.mark.unit
def test_common_dbtypes_options_contract(client) -> None:
    response = client.get("/common/api/dbtypes-options")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"
