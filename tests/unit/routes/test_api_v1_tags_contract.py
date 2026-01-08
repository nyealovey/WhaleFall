import pytest

from app import create_app, db
from app.constants import DatabaseType
from app.models.instance import Instance
from app.models.tag import Tag
from app.models.user import User


@pytest.mark.unit
def test_api_v1_tags_list_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag = Tag(
            name="demo",
            display_name="示例标签",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/tags")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False
        assert "message" in payload
        assert "timestamp" in payload

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"items", "total", "page", "pages", "limit", "stats"}.issubset(data.keys())

        stats = data.get("stats")
        assert isinstance(stats, dict)
        assert {"total", "active", "inactive", "category_count"}.issubset(stats.keys())

        items = data.get("items")
        assert isinstance(items, list)
        assert len(items) == 1

        item = items[0]
        assert isinstance(item, dict)
        expected_keys = {
            "id",
            "name",
            "display_name",
            "category",
            "color",
            "color_value",
            "color_name",
            "css_class",
            "is_active",
            "created_at",
            "updated_at",
            "instance_count",
        }
        assert expected_keys.issubset(item.keys())


@pytest.mark.unit
def test_api_v1_tags_options_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag = Tag(
            name="demo",
            display_name="示例标签",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/tags/options")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"tags", "category"}.issubset(data.keys())
        assert isinstance(data.get("tags"), list)


@pytest.mark.unit
def test_api_v1_tags_categories_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag = Tag(
            name="demo",
            display_name="示例标签",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/api/v1/tags/categories")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert isinstance(data.get("categories"), list)


@pytest.mark.unit
def test_api_v1_tag_detail_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag = Tag(
            name="demo",
            display_name="示例标签",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(f"/api/v1/tags/{tag.id}")
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        tag_data = data.get("tag")
        assert isinstance(tag_data, dict)
        assert tag_data.get("id") == tag.id
        assert tag_data.get("name") == tag.name

@pytest.mark.unit
def test_api_v1_tags_requires_auth(client):
    response = client.get("/api/v1/tags")

    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_tags_create_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.post(
            "/api/v1/tags",
            json={
                "name": "demo_new",
                "display_name": "示例标签(新)",
                "category": "other",
                "color": "primary",
                "is_active": True,
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 201

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        tag_data = data.get("tag")
        assert isinstance(tag_data, dict)
        assert tag_data.get("name") == "demo_new"


@pytest.mark.unit
def test_api_v1_tags_update_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag = Tag(
            name="demo",
            display_name="示例标签",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.put(
            f"/api/v1/tags/{tag.id}",
            json={
                "name": "demo",
                "display_name": "示例标签(更新)",
                "category": "other",
                "color": "primary",
                "is_active": True,
            },
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        tag_data = data.get("tag")
        assert isinstance(tag_data, dict)
        assert tag_data.get("id") == tag.id
        assert tag_data.get("display_name") == "示例标签(更新)"


@pytest.mark.unit
def test_api_v1_tags_delete_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag = Tag(
            name="demo",
            display_name="示例标签",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.delete(
            f"/api/v1/tags/{tag.id}",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("tag_id") == tag.id


@pytest.mark.unit
def test_api_v1_tags_delete_in_use_returns_conflict() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag = Tag(
            name="demo",
            display_name="示例标签",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag)
        db.session.commit()

        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        tag.instances.append(instance)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.delete(
            f"/api/v1/tags/{tag.id}",
            json={},
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 409

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("error") is True
        assert payload.get("success") is False
        assert payload.get("message_code") == "TAG_IN_USE"


@pytest.mark.unit
def test_api_v1_tags_batch_delete_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["tags"],
                db.metadata.tables["instance_tags"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        tag_1 = Tag(
            name="demo1",
            display_name="示例标签1",
            category="other",
            color="primary",
            is_active=True,
        )
        tag_2 = Tag(
            name="demo2",
            display_name="示例标签2",
            category="other",
            color="primary",
            is_active=True,
        )
        db.session.add(tag_1)
        db.session.add(tag_2)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        csrf_response = client.get("/api/v1/auth/csrf-token")
        assert csrf_response.status_code == 200
        csrf_payload = csrf_response.get_json()
        assert isinstance(csrf_payload, dict)
        csrf_token = csrf_payload.get("data", {}).get("csrf_token")
        assert isinstance(csrf_token, str)

        response = client.post(
            "/api/v1/tags/batch-delete",
            json={"tag_ids": [tag_1.id, tag_2.id]},
            headers={"X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False

        data = payload.get("data")
        assert isinstance(data, dict)
        results = data.get("results")
        assert isinstance(results, list)
        assert len(results) == 2
