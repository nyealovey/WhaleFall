import pytest


@pytest.mark.unit
def test_capacity_databases_contract(client) -> None:
    response = client.get(
        "/capacity/api/databases?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert response.status_code == 404

    summary_response = client.get(
        "/capacity/api/databases/summary?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert summary_response.status_code == 404
