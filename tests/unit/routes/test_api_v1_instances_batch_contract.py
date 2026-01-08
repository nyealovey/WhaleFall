import io

import pytest

from app.services.instances.batch_service import InstanceBatchCreationService, InstanceBatchDeletionService


@pytest.mark.unit
def test_api_v1_instances_batch_requires_auth(client) -> None:
    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    delete_response = client.post(
        "/api/v1/instances/actions/batch-delete",
        json={"instance_ids": [1]},
        headers=headers,
    )
    assert delete_response.status_code == 401
    payload = delete_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    csv_content = "name,db_type,host,port\ninstance-1,mysql,127.0.0.1,3306\n"
    create_response = client.post(
        "/api/v1/instances/actions/batch-create",
        data={"file": (io.BytesIO(csv_content.encode("utf-8")), "instances.csv")},
        content_type="multipart/form-data",
        headers=headers,
    )
    assert create_response.status_code == 401
    payload = create_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_instances_batch_endpoints_contract(auth_client, monkeypatch) -> None:
    def _dummy_create_instances(self, instances_data, *, operator_id=None):  # noqa: ANN001
        del self, instances_data, operator_id
        return {
            "created_count": 1,
            "errors": [],
            "duplicate_names": [],
            "skipped_existing_names": [],
            "message": "成功创建 1 个实例",
        }

    def _dummy_delete_instances(self, instance_ids, *, operator_id=None, deletion_mode=None):  # noqa: ANN001
        del self, instance_ids, operator_id, deletion_mode
        return {"deleted_count": 1, "instance_ids": [1]}

    monkeypatch.setattr(InstanceBatchCreationService, "create_instances", _dummy_create_instances)
    monkeypatch.setattr(InstanceBatchDeletionService, "delete_instances", _dummy_delete_instances)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    csv_content = "name,db_type,host,port\ninstance-1,mysql,127.0.0.1,3306\n"
    create_response = auth_client.post(
        "/api/v1/instances/actions/batch-create",
        data={"file": (io.BytesIO(csv_content.encode("utf-8")), "instances.csv")},
        content_type="multipart/form-data",
        headers=headers,
    )
    assert create_response.status_code == 200
    payload = create_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("created_count") == 1

    delete_response = auth_client.post(
        "/api/v1/instances/actions/batch-delete",
        json={"instance_ids": [1]},
        headers=headers,
    )
    assert delete_response.status_code == 200
    payload = delete_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("deleted_count") == 1
