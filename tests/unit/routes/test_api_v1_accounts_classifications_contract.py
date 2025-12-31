import pytest

from app import db
from app.constants import DatabaseType
from app.models.account_classification import AccountClassificationAssignment
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.permission_config import PermissionConfig


def _ensure_account_classifications_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_classifications"],
                db.metadata.tables["classification_rules"],
                db.metadata.tables["account_classification_assignments"],
                db.metadata.tables["permission_configs"],
                db.metadata.tables["database_type_configs"],
            ],
        )


@pytest.mark.unit
def test_api_v1_accounts_classifications_requires_auth(client) -> None:
    response = client.get("/api/v1/accounts/classifications")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_accounts_classifications_auto_classify_contract(auth_client, monkeypatch) -> None:
    class _DummyAutoClassifyResult:
        @staticmethod
        def to_payload() -> dict[str, object]:
            return {
                "classified_accounts": 0,
                "total_classifications_added": 0,
                "failed_count": 0,
                "message": "自动分类成功",
            }

    class _DummyAutoClassifyService:
        @staticmethod
        def auto_classify(*, instance_id, created_by, use_optimized):  # noqa: ANN001
            return _DummyAutoClassifyResult()

    import app.api.v1.namespaces.accounts_classifications as api_module

    monkeypatch.setattr(api_module, "_auto_classify_service", _DummyAutoClassifyService())

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        "/api/v1/accounts/classifications/actions/auto-classify",
        json={"instance_id": None, "use_optimized": True},
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"classified_accounts", "total_classifications_added", "failed_count", "message"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_accounts_classifications_endpoints_contract(app, auth_client) -> None:
    _ensure_account_classifications_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.flush()

        instance_account = InstanceAccount(
            instance_id=instance.id,
            username="demo",
            db_type=DatabaseType.MYSQL,
            is_active=True,
        )
        db.session.add(instance_account)
        db.session.flush()

        permission = AccountPermission(
            instance_id=instance.id,
            db_type=DatabaseType.MYSQL,
            instance_account_id=instance_account.id,
            username="demo",
            permission_facts={
                "version": 2,
                "db_type": "mysql",
                "capabilities": [],
                "capability_reasons": {},
                "roles": [],
                "privileges": {},
                "errors": [],
                "meta": {},
            },
        )
        db.session.add(permission)
        db.session.flush()
        permission_id = permission.id

        permission_config = PermissionConfig(
            db_type="mysql",
            category="global_privileges",
            permission_name="SELECT",
            description="select",
            is_active=True,
            sort_order=0,
        )
        db.session.add(permission_config)
        db.session.commit()

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    colors_response = auth_client.get("/api/v1/accounts/classifications/colors")
    assert colors_response.status_code == 200
    colors_payload = colors_response.get_json()
    assert isinstance(colors_payload, dict)
    assert colors_payload.get("success") is True
    colors_data = colors_payload.get("data")
    assert isinstance(colors_data, dict)
    assert {"colors", "choices"}.issubset(colors_data.keys())

    classifications_response = auth_client.get("/api/v1/accounts/classifications")
    assert classifications_response.status_code == 200
    classifications_payload = classifications_response.get_json()
    assert isinstance(classifications_payload, dict)
    assert classifications_payload.get("success") is True
    classifications_data = classifications_payload.get("data")
    assert isinstance(classifications_data, dict)
    assert isinstance(classifications_data.get("classifications"), list)

    create_classification_response = auth_client.post(
        "/api/v1/accounts/classifications",
        json={
            "name": "demo-classification",
            "description": "demo",
            "risk_level": "medium",
            "color": "info",
            "icon_name": "fa-tag",
            "priority": 0,
        },
        headers=headers,
    )
    assert create_classification_response.status_code == 201
    create_classification_payload = create_classification_response.get_json()
    assert isinstance(create_classification_payload, dict)
    assert create_classification_payload.get("success") is True
    classification_data = create_classification_payload.get("data", {}).get("classification")
    assert isinstance(classification_data, dict)
    classification_id = classification_data.get("id")
    assert isinstance(classification_id, int)

    detail_response = auth_client.get(f"/api/v1/accounts/classifications/{classification_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()
    assert isinstance(detail_payload, dict)
    assert detail_payload.get("success") is True
    detail_data = detail_payload.get("data", {}).get("classification")
    assert isinstance(detail_data, dict)
    assert {"id", "name", "rules_count"}.issubset(detail_data.keys())

    update_response = auth_client.put(
        f"/api/v1/accounts/classifications/{classification_id}",
        json={"name": "demo-classification-updated"},
        headers=headers,
    )
    assert update_response.status_code == 200
    update_payload = update_response.get_json()
    assert isinstance(update_payload, dict)
    assert update_payload.get("success") is True

    rules_response = auth_client.get("/api/v1/accounts/classifications/rules")
    assert rules_response.status_code == 200
    rules_payload = rules_response.get_json()
    assert isinstance(rules_payload, dict)
    assert rules_payload.get("success") is True
    rules_data = rules_payload.get("data")
    assert isinstance(rules_data, dict)
    assert isinstance(rules_data.get("rules_by_db_type"), dict)

    create_rule_response = auth_client.post(
        "/api/v1/accounts/classifications/rules",
        json={
            "rule_name": "demo-rule",
            "classification_id": classification_id,
            "db_type": "mysql",
            "operator": "AND",
            "rule_expression": {},
            "is_active": True,
        },
        headers=headers,
    )
    assert create_rule_response.status_code == 201
    create_rule_payload = create_rule_response.get_json()
    assert isinstance(create_rule_payload, dict)
    assert create_rule_payload.get("success") is True
    rule_id = create_rule_payload.get("data", {}).get("rule_id")
    assert isinstance(rule_id, int)

    rule_detail_response = auth_client.get(f"/api/v1/accounts/classifications/rules/{rule_id}")
    assert rule_detail_response.status_code == 200
    rule_detail_payload = rule_detail_response.get_json()
    assert isinstance(rule_detail_payload, dict)
    assert rule_detail_payload.get("success") is True
    rule_detail_data = rule_detail_payload.get("data", {}).get("rule")
    assert isinstance(rule_detail_data, dict)
    assert {"id", "rule_name", "db_type", "rule_expression"}.issubset(rule_detail_data.keys())

    update_rule_response = auth_client.put(
        f"/api/v1/accounts/classifications/rules/{rule_id}",
        json={
            "rule_name": "demo-rule-updated",
            "classification_id": classification_id,
            "db_type": "mysql",
            "operator": "AND",
            "rule_expression": {},
            "is_active": True,
        },
        headers=headers,
    )
    assert update_rule_response.status_code == 200
    update_rule_payload = update_rule_response.get_json()
    assert isinstance(update_rule_payload, dict)
    assert update_rule_payload.get("success") is True

    filter_response = auth_client.get(
        f"/api/v1/accounts/classifications/rules/filter?classification_id={classification_id}&db_type=mysql",
    )
    assert filter_response.status_code == 200
    filter_payload = filter_response.get_json()
    assert isinstance(filter_payload, dict)
    assert filter_payload.get("success") is True
    filter_data = filter_payload.get("data")
    assert isinstance(filter_data, dict)
    assert isinstance(filter_data.get("rules"), list)

    with app.app_context():
        assignment = AccountClassificationAssignment(
            account_id=permission_id,
            classification_id=classification_id,
            rule_id=rule_id,
            assigned_by=None,
            assignment_type="auto",
            is_active=True,
        )
        db.session.add(assignment)
        db.session.commit()
        assignment_id = assignment.id

    assignments_response = auth_client.get("/api/v1/accounts/classifications/assignments")
    assert assignments_response.status_code == 200
    assignments_payload = assignments_response.get_json()
    assert isinstance(assignments_payload, dict)
    assert assignments_payload.get("success") is True
    assignments_data = assignments_payload.get("data")
    assert isinstance(assignments_data, dict)
    assert isinstance(assignments_data.get("assignments"), list)

    stats_response = auth_client.get(f"/api/v1/accounts/classifications/rules/stats?rule_ids={rule_id}")
    assert stats_response.status_code == 200
    stats_payload = stats_response.get_json()
    assert isinstance(stats_payload, dict)
    assert stats_payload.get("success") is True
    stats_data = stats_payload.get("data")
    assert isinstance(stats_data, dict)
    assert isinstance(stats_data.get("rule_stats"), list)

    remove_assignment_response = auth_client.delete(
        f"/api/v1/accounts/classifications/assignments/{assignment_id}",
        headers=headers,
    )
    assert remove_assignment_response.status_code == 200

    permissions_response = auth_client.get("/api/v1/accounts/classifications/permissions/mysql")
    assert permissions_response.status_code == 200
    permissions_payload = permissions_response.get_json()
    assert isinstance(permissions_payload, dict)
    assert permissions_payload.get("success") is True
    permissions_data = permissions_payload.get("data")
    assert isinstance(permissions_data, dict)
    assert "permissions" in permissions_data
    assert "version_context" not in permissions_data
    permissions = permissions_data.get("permissions")
    assert isinstance(permissions, dict)
    global_privileges = permissions.get("global_privileges")
    assert isinstance(global_privileges, list)
    assert global_privileges
    first_perm = global_privileges[0]
    assert isinstance(first_perm, dict)
    assert first_perm.get("name") == "SELECT"
    assert "introduced_in_major" in first_perm
    assert first_perm.get("introduced_in_major") is None

    delete_rule_response = auth_client.delete(
        f"/api/v1/accounts/classifications/rules/{rule_id}",
        headers=headers,
    )
    assert delete_rule_response.status_code == 200

    delete_classification_response = auth_client.delete(
        f"/api/v1/accounts/classifications/{classification_id}",
        headers=headers,
    )
    assert delete_classification_response.status_code == 200
