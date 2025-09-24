"""
认证路由集成测试
"""
import pytest
from flask import Flask
from app import create_app
from app.models.user import User


@pytest.mark.integration
def test_login_page_get(client):
    """Test GET request to login page."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower()


@pytest.mark.integration
def test_login_success(client, db):
    """Test successful login."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Login
    response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "TestPass123"
    })
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "access_token" in data


@pytest.mark.integration
def test_login_invalid_credentials(client, db):
    """Test login with invalid credentials."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Login with wrong password
    response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "WrongPass"
    })
    
    # 3. Assert
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert "用户名或密码错误" in data["message"]


@pytest.mark.integration
def test_login_missing_credentials(client):
    """Test login with missing credentials."""
    # 2. Act: Login without password
    response = client.post('/auth/login', json={
        "username": "testuser"
    })
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "用户名和密码不能为空" in data["message"]


@pytest.mark.integration
def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    # 2. Act: Login with nonexistent user
    response = client.post('/auth/login', json={
        "username": "nonexistent",
        "password": "password"
    })
    
    # 3. Assert
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert "用户名或密码错误" in data["message"]


@pytest.mark.integration
def test_login_inactive_user(client, db):
    """Test login with inactive user."""
    # 1. Arrange: Create inactive user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=False
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Login
    response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "TestPass123"
    })
    
    # 3. Assert
    assert response.status_code == 401
    data = response.get_json()
    assert data["success"] is False
    assert "用户已被禁用" in data["message"]


@pytest.mark.integration
def test_logout_success(client, auth_headers):
    """Test successful logout."""
    # 2. Act: Logout
    response = client.post('/auth/logout', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "登出成功" in data["message"]


@pytest.mark.integration
def test_logout_without_auth(client):
    """Test logout without authentication."""
    # 2. Act: Logout without auth
    response = client.post('/auth/logout')
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_register_success(client, db):
    """Test successful user registration."""
    # 2. Act: Register new user
    response = client.post('/auth/register', json={
        "username": "newuser",
        "password": "NewPass123",
        "role": "user"
    })
    
    # 3. Assert
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert "注册成功" in data["message"]
    
    # Verify user was created
    user = User.query.filter_by(username="newuser").first()
    assert user is not None
    assert user.role == "user"
    assert user.is_active is True


@pytest.mark.integration
def test_register_duplicate_username(client, db):
    """Test registration with duplicate username."""
    # 1. Arrange: Create existing user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Register with same username
    response = client.post('/auth/register', json={
        "username": "testuser",
        "password": "NewPass123",
        "role": "user"
    })
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "用户名已存在" in data["message"]


@pytest.mark.integration
def test_register_weak_password(client):
    """Test registration with weak password."""
    # 2. Act: Register with weak password
    response = client.post('/auth/register', json={
        "username": "newuser",
        "password": "weak",
        "role": "user"
    })
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "密码" in data["message"]


@pytest.mark.integration
def test_register_missing_fields(client):
    """Test registration with missing fields."""
    # 2. Act: Register without password
    response = client.post('/auth/register', json={
        "username": "newuser",
        "role": "user"
    })
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "必填字段" in data["message"]


@pytest.mark.integration
def test_register_invalid_role(client):
    """Test registration with invalid role."""
    # 2. Act: Register with invalid role
    response = client.post('/auth/register', json={
        "username": "newuser",
        "password": "NewPass123",
        "role": "invalid_role"
    })
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "角色" in data["message"]


@pytest.mark.integration
def test_get_current_user_success(client, auth_headers):
    """Test getting current user info."""
    # 2. Act: Get current user
    response = client.get('/auth/me', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "user" in data
    assert data["user"]["username"] is not None


@pytest.mark.integration
def test_get_current_user_unauthorized(client):
    """Test getting current user without authentication."""
    # 2. Act: Get current user without auth
    response = client.get('/auth/me')
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_refresh_token_success(client, auth_headers):
    """Test refreshing access token."""
    # 2. Act: Refresh token
    response = client.post('/auth/refresh', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "access_token" in data


@pytest.mark.integration
def test_refresh_token_unauthorized(client):
    """Test refreshing token without authentication."""
    # 2. Act: Refresh token without auth
    response = client.post('/auth/refresh')
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_change_password_success(client, auth_headers, db):
    """Test changing password successfully."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="OldPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Change password
    response = client.post('/auth/change-password', 
                          json={
                              "old_password": "OldPass123",
                              "new_password": "NewPass123"
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "密码修改成功" in data["message"]


@pytest.mark.integration
def test_change_password_wrong_old_password(client, auth_headers, db):
    """Test changing password with wrong old password."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="OldPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Change password with wrong old password
    response = client.post('/auth/change-password', 
                          json={
                              "old_password": "WrongOldPass",
                              "new_password": "NewPass123"
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "原密码错误" in data["message"]


@pytest.mark.integration
def test_change_password_weak_new_password(client, auth_headers, db):
    """Test changing password with weak new password."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="OldPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Change password with weak new password
    response = client.post('/auth/change-password', 
                          json={
                              "old_password": "OldPass123",
                              "new_password": "weak"
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "新密码" in data["message"]


@pytest.mark.integration
def test_change_password_missing_fields(client, auth_headers):
    """Test changing password with missing fields."""
    # 2. Act: Change password without new password
    response = client.post('/auth/change-password', 
                          json={
                              "old_password": "OldPass123"
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "必填字段" in data["message"]


@pytest.mark.integration
def test_change_password_unauthorized(client):
    """Test changing password without authentication."""
    # 2. Act: Change password without auth
    response = client.post('/auth/change-password', 
                          json={
                              "old_password": "OldPass123",
                              "new_password": "NewPass123"
                          })
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_login_with_form_data(client, db):
    """Test login with form data instead of JSON."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Login with form data
    response = client.post('/auth/login', data={
        "username": "testuser",
        "password": "TestPass123"
    })
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "access_token" in data


@pytest.mark.integration
def test_login_rate_limiting(client, db):
    """Test login rate limiting."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Make multiple failed login attempts
    for i in range(10):
        response = client.post('/auth/login', json={
            "username": "testuser",
            "password": "WrongPass"
        })
    
    # 3. Assert: Should be rate limited
    assert response.status_code == 429


@pytest.mark.integration
def test_csrf_protection(client, db):
    """Test CSRF protection on forms."""
    # 2. Act: Try to submit form without CSRF token
    response = client.post('/auth/login', data={
        "username": "testuser",
        "password": "TestPass123"
    }, follow_redirects=False)
    
    # 3. Assert: Should be redirected or show CSRF error
    assert response.status_code in [400, 403, 302]


@pytest.mark.integration
def test_login_with_remember_me(client, db):
    """Test login with remember me option."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Login with remember me
    response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "TestPass123",
        "remember_me": True
    })
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.integration
def test_login_without_remember_me(client, db):
    """Test login without remember me option."""
    # 1. Arrange: Create test user
    user = User(
        username="testuser",
        password="TestPass123",
        role="user",
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    # 2. Act: Login without remember me
    response = client.post('/auth/login', json={
        "username": "testuser",
        "password": "TestPass123",
        "remember_me": False
    })
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "access_token" in data
    # Should not have refresh token when remember_me is False
    assert "refresh_token" not in data or data.get("refresh_token") is None
