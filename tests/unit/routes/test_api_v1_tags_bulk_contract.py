import pytest

from app import db
from app.models.instance import Instance
from app.models.tag import Tag


@pytest.mark.unit
def test_api_v1_tags_bulk_requires_auth(client) -> None:
    response = client.get("/api/v1/tags/bulk/instances")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    assign_response = client.post(
        "/api/v1/tags/bulk/assign",
        json={"instance_ids": [1], "tag_ids": [1]},
        headers=headers,
    )
    assert assign_response.status_code == 401
    payload = assign_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_tags_bulk_endpoints_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
                db.metadata.tables["unified_logs"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)

        tag = Tag(
            name="t1",
            display_name="T1",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        instance_id = instance.id
        tag_id = tag.id

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    instances_response = auth_client.get("/api/v1/tags/bulk/instances")
    assert instances_response.status_code == 200
    payload = instances_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert "instances" in data

    tags_response = auth_client.get("/api/v1/tags/bulk/tags")
    assert tags_response.status_code == 200
    payload = tags_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"tags", "category_names"}.issubset(data.keys())

    assign_response = auth_client.post(
        "/api/v1/tags/bulk/assign",
        json={"instance_ids": [instance_id], "tag_ids": [tag_id]},
        headers=headers,
    )
    assert assign_response.status_code == 200
    payload = assign_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    instance_tags_response = auth_client.post(
        "/api/v1/tags/bulk/instance-tags",
        json={"instance_ids": [instance_id]},
        headers=headers,
    )
    assert instance_tags_response.status_code == 200
    payload = instance_tags_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    remove_response = auth_client.post(
        "/api/v1/tags/bulk/remove",
        json={"instance_ids": [instance_id], "tag_ids": [tag_id]},
        headers=headers,
    )
    assert remove_response.status_code == 200
    payload = remove_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    remove_all_response = auth_client.post(
        "/api/v1/tags/bulk/remove-all",
        json={"instance_ids": [instance_id]},
        headers=headers,
    )
    assert remove_all_response.status_code == 200
    payload = remove_all_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
