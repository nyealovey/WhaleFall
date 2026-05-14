import pytest

from app import db
from app.models.instance import Instance


def _ensure_risk_center_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["instance_tags"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_change_log"],
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
                db.metadata.tables["credentials"],
                db.metadata.tables["instance_config_snapshots"],
                db.metadata.tables["jumpserver_asset_snapshots"],
                db.metadata.tables["veeam_source_bindings"],
                db.metadata.tables["veeam_machine_backup_snapshots"],
            ],
        )


@pytest.mark.unit
def test_api_v1_risk_center_requires_auth(client) -> None:
    response = client.get("/api/v1/risk-center/summary")
    assert response.status_code == 401

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_risk_center_summary_contract(app, auth_client) -> None:
    _ensure_risk_center_tables(app)
    with app.app_context():
        db.session.add(Instance(name="db01", db_type="mysql", host="127.0.0.1", port=3306, is_active=True))
        db.session.commit()

    response = auth_client.get("/api/v1/risk-center/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"total_instances", "severity_counts", "db_type_counts", "top_risks", "generated_at"}.issubset(data)
    assert data["total_instances"] == 1
    assert data["severity_counts"]["critical"] == 1


@pytest.mark.unit
def test_api_v1_risk_center_cards_contract_and_filters(app, auth_client) -> None:
    _ensure_risk_center_tables(app)
    with app.app_context():
        db.session.add_all(
            [
                Instance(name="db-critical", db_type="mysql", host="127.0.0.1", port=3306, is_active=True),
                Instance(name="db-disabled", db_type="sqlserver", host="127.0.0.2", port=1433, is_active=False),
            ]
        )
        db.session.commit()

    response = auth_client.get("/api/v1/risk-center/cards?severity=critical&db_type=mysql")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages", "limit"}.issubset(data)
    assert data["total"] == 1
    item = data["items"][0]
    expected_keys = {
        "instance_id",
        "name",
        "db_type",
        "host",
        "port",
        "overall_severity",
        "risk_score",
        "risk_flags",
        "risk_items",
        "backup",
        "audit",
        "managed",
        "capacity",
        "access",
        "tasks",
        "status_band",
        "links",
    }
    assert expected_keys.issubset(item)
    assert item["name"] == "db-critical"


@pytest.mark.unit
def test_risk_center_page_renders_card_wall(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )
        db.session.add(Instance(name="db-page", db_type="mysql", host="127.0.0.1", port=3306, is_active=True))
        db.session.commit()

    response = auth_client.get("/risk-center/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "风险中心" in html
    assert "risk-card-grid" in html
    assert "db-page" in html
    assert html.index(">备份<") < html.index(">审计<") < html.index(">托管<")
    assert ">Capacity<" not in html
    assert ">Access<" not in html
