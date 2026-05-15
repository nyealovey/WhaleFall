import pytest

from app import db
from app.models.instance import Instance
from app.models.tag import Tag


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
def test_api_v1_risk_center_cards_filters_by_search_status_and_tag(app, auth_client) -> None:
    _ensure_risk_center_tables(app)
    with app.app_context():
        finance = Tag(name="finance", display_name="财务", category="business")
        prod = Tag(name="prod", display_name="生产", category="environment")
        active = Instance(name="billing-main", db_type="mysql", host="10.2.0.10", port=3306, is_active=True)
        inactive = Instance(name="finance-ledger", db_type="sqlserver", host="10.8.0.20", port=1433, is_active=False)
        db.session.add_all([finance, prod, active, inactive])
        db.session.flush()
        active.tags.append(prod)
        inactive.tags.append(finance)
        db.session.commit()

    response = auth_client.get(
        "/api/v1/risk-center/cards",
        query_string={"search": "ledger", "status": "inactive", "tag": "finance", "limit": 0},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data["total"] == 1
    assert data["limit"] == 1
    assert [item["name"] for item in data["items"]] == ["finance-ledger"]


@pytest.mark.unit
def test_api_v1_risk_center_cards_returns_all_cards_by_default(app, auth_client) -> None:
    _ensure_risk_center_tables(app)
    with app.app_context():
        db.session.add_all(
            [
                Instance(name=f"db-page-{index:02d}", db_type="mysql", host=f"127.0.1.{index}", port=3306, is_active=True)
                for index in range(30)
            ]
        )
        db.session.commit()

    response = auth_client.get("/api/v1/risk-center/cards")

    assert response.status_code == 200
    payload = response.get_json()
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data["total"] == 30
    assert len(data["items"]) == 30
    assert data["pages"] == 1
    assert data["limit"] == 30


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
    assert "db-types/mysql.png" in html
    card_start = html.index('class="card risk-instance-card')
    card_end = html.index("</article>", card_start)
    card_html = html[card_start:card_end]
    assert "dropdown-menu" not in card_html
    assert "fa-ellipsis-v" not in card_html
    assert "risk-instance-card__severity" in card_html
    assert "risk-instance-card__subtitle" not in card_html
    assert "risk-signal__icon" in card_html
    assert card_html.index('data-risk-signal="backup"') < card_html.index('data-risk-signal="audit"')
    assert card_html.index('data-risk-signal="audit"') < card_html.index('data-risk-signal="managed"')
    assert card_html.index('data-risk-signal="managed"') < card_html.index('data-risk-signal="tasks"')
    assert 'aria-label="备份：' in card_html
    assert 'aria-label="审计：' in card_html
    assert 'aria-label="托管：' in card_html
    assert 'aria-label="任务：' in card_html
    assert ">备份<" not in card_html
    assert ">审计<" not in card_html
    assert ">托管<" not in card_html
    assert ">任务<" not in card_html
    assert ">Capacity<" not in html
    assert ">Access<" not in html


@pytest.mark.unit
def test_risk_center_page_renders_all_matching_cards_without_hidden_pagination(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )
        db.session.add_all(
            [
                Instance(name=f"db-visible-{index:02d}", db_type="mysql", host=f"10.1.0.{index}", port=3306, is_active=True)
                for index in range(30)
            ]
        )
        db.session.commit()

    response = auth_client.get("/risk-center/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('class="card risk-instance-card') == 30
    assert "db-visible-00" in html
    assert "db-visible-29" in html
