import pytest

from app.schemas.internal_contracts.permission_snapshot_v4 import normalize_permission_snapshot_categories_v4


@pytest.mark.unit
def test_normalize_permission_snapshot_categories_v4_postgresql_predefined_roles() -> None:
    cases = [
        ([{"role": "readonly"}], ["readonly"]),
        (["readonly"], ["readonly"]),
        ([{"role": "readonly"}, "writer", {"role": ""}, "", {"role": None}], ["readonly", "writer"]),
    ]
    for raw, expected in cases:
        categories = {"predefined_roles": raw}
        normalized = normalize_permission_snapshot_categories_v4("postgresql", categories)
        assert normalized["predefined_roles"] == expected


@pytest.mark.unit
def test_normalize_permission_snapshot_categories_v4_sqlserver_server_roles() -> None:
    cases = [
        ([{"name": "sysadmin"}], ["sysadmin"]),
        (["sysadmin"], ["sysadmin"]),
        ([{"name": "sysadmin"}, "securityadmin", {"name": ""}, ""], ["sysadmin", "securityadmin"]),
    ]
    for raw, expected in cases:
        categories = {"server_roles": raw}
        normalized = normalize_permission_snapshot_categories_v4("sqlserver", categories)
        assert normalized["server_roles"] == expected


@pytest.mark.unit
def test_normalize_permission_snapshot_categories_v4_sqlserver_database_roles_dict() -> None:
    categories = {
        "database_roles": {
            "db1": [{"name": "db_owner"}],
            "db2": ["db_datareader", {"name": "db_datawriter"}],
            "": [{"name": "ignored"}],
            123: [{"name": "ignored"}],
        },
    }
    normalized = normalize_permission_snapshot_categories_v4("sqlserver", categories)
    assert normalized["database_roles"] == {
        "db1": ["db_owner"],
        "db2": ["db_datareader", "db_datawriter"],
    }


@pytest.mark.unit
def test_normalize_permission_snapshot_categories_v4_sqlserver_database_roles_list_coerces_to_mapping() -> None:
    categories = {"database_roles": [{"name": "db_owner"}, "db_datareader"]}
    normalized = normalize_permission_snapshot_categories_v4("sqlserver", categories)
    assert normalized["database_roles"] == {"__all__": ["db_owner", "db_datareader"]}


@pytest.mark.unit
def test_normalize_permission_snapshot_categories_v4_oracle_roles() -> None:
    cases = [
        ([{"role": "DBA"}], ["DBA"]),
        (["DBA"], ["DBA"]),
        ([{"role": "DBA"}, "CONNECT", {"role": ""}, ""], ["DBA", "CONNECT"]),
    ]
    for raw, expected in cases:
        categories = {"oracle_roles": raw}
        normalized = normalize_permission_snapshot_categories_v4("oracle", categories)
        assert normalized["oracle_roles"] == expected
