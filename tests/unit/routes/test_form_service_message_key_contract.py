import pytest

from app import create_app, db
from app.core.constants.http_headers import HttpHeaders
from app.models.user import User


@pytest.mark.unit
def test_account_classification_name_exists_message_key_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["account_classifications"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload["data"]["csrf_token"]

        headers = {HttpHeaders.X_CSRF_TOKEN: csrf_token}
        create_payload = {"code": "dup_classification", "display_name": "dup_classification"}

        response = client.post(
            "/api/v1/accounts/classifications",
            json=create_payload,
            headers=headers,
        )
        assert response.status_code == 201

        response = client.post(
            "/api/v1/accounts/classifications",
            json=create_payload,
            headers=headers,
        )
        assert response.status_code == 400

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("error") is True
        assert payload.get("message_code") == "NAME_EXISTS"


@pytest.mark.unit
def test_change_password_invalid_old_password_message_key_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload["data"]["csrf_token"]

        headers = {HttpHeaders.X_CSRF_TOKEN: csrf_token}
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "WrongPass1",
                "new_password": "NewPass1",
                "confirm_password": "NewPass1",
            },
            headers=headers,
        )

        assert response.status_code == 401
        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("error") is True
        assert payload.get("message_code") == "INVALID_OLD_PASSWORD"
