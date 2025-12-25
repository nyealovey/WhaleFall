import pytest

from app import create_app, db
from app.models.tag import Tag
from app.models.user import User


@pytest.mark.unit
def test_tags_list_contract() -> None:
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

        response = client.get("/tags/api/list")
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
