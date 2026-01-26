---
title: Testing 示例(长示例)
aliases:
  - testing-examples
tags:
  - reference
  - reference/examples
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: `standards/testing-standards` 引用的测试示例集合(非规则 SSOT)
related:
  - "[[reference/examples/README]]"
  - "[[standards/core/guide/testing]]"
  - "[[standards/doc/guide/document-boundary]]"
---

# Testing 示例(长示例)

> [!important] 说明
> 本文仅用于承载长示例代码, 便于 standards 引用与收敛. 规则 SSOT 以 `docs/Obsidian/standards/**` 为准.

## 常用 Fixtures 示例

```python
import pytest
from app import create_app, db

@pytest.fixture(scope="session")
def app():
    """应用实例, 整个测试会话复用"""
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True
    return app

@pytest.fixture(scope="function")
def client(app):
    """测试客户端, 每个测试函数独立"""
    return app.test_client()

@pytest.fixture(scope="function")
def db_session(app):
    """数据库会话, 测试后自动回滚"""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()

@pytest.fixture(scope="function")
def auth_session(client, db_session):
    """已认证的会话, 用于需要登录的测试"""
    from app.models.user import User
    user = User(username="test_admin", password="TestPass1", role="admin")
    db_session.add(user)
    db_session.commit()

    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)

    yield client

    # teardown: 清理测试用户
    db_session.delete(user)
    db_session.commit()
```

## API 契约测试示例

```python
@pytest.mark.unit
def test_instances_list_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        # 创建最小测试数据
        db.metadata.create_all(bind=db.engine, tables=[...])
        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get("/instances/api/instances")

        # 验证状态码
        assert response.status_code == 200

        # 验证 envelope 结构
        payload = response.get_json()
        assert payload.get("success") is True
        assert payload.get("error") is False
        assert "message" in payload
        assert "timestamp" in payload

        # 验证 data 字段结构
        data = payload.get("data")
        assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
```
