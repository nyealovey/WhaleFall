import pytest
from app.models.user import User

@pytest.mark.unit
def test_create_user(db):
    """Test creating a new user and saving to the database."""
    # 1. Arrange: Create a new user instance
    username = "testuser"
    password = "Password123"
    user = User(username=username, password=password)

    # 2. Act: Add to session and commit
    db.session.add(user)
    db.session.commit()

    # 3. Assert: Retrieve the user and check its attributes
    retrieved_user = User.query.filter_by(username=username).first()
    assert retrieved_user is not None
    assert retrieved_user.username == username
    assert retrieved_user.id is not None

@pytest.mark.unit
def test_password_hashing(db):
    """Test the password hashing and checking mechanism."""
    # 1. Arrange: Create a user with a password
    user = User(username="hashuser", password="Password123")
    db.session.add(user)
    db.session.commit()

    # 2. Assert: Check password properties
    # The password should exist
    assert user.password is not None
    # The password should be hashed (not plain text)
    assert user.password != "Password123"

    # 3. Assert: Check password verification
    assert user.check_password("Password123") is True
    assert user.check_password("wrong_password") is False

@pytest.mark.unit
def test_password_validation_weak_password():
    """Test password validation with weak passwords."""
    # Create user with valid password first
    user = User(username="testuser", password="ValidPass123")
    
    # Test password too short
    with pytest.raises(ValueError, match="密码长度至少8位"):
        user.set_password("1234567")
    
    # Test password without uppercase
    with pytest.raises(ValueError, match="密码必须包含大写字母"):
        user.set_password("password123")
    
    # Test password without lowercase
    with pytest.raises(ValueError, match="密码必须包含小写字母"):
        user.set_password("PASSWORD123")
    
    # Test password without digits
    with pytest.raises(ValueError, match="密码必须包含数字"):
        user.set_password("Password")

@pytest.mark.unit
def test_password_validation_strong_password():
    """Test password validation with strong passwords."""
    # Create user with valid password first
    user = User(username="testuser", password="ValidPass123")
    
    # Test valid passwords
    valid_passwords = [
        "Password123",
        "MySecure123",
        "TestPass456",
        "StrongP@ss1"
    ]
    
    for password in valid_passwords:
        user.set_password(password)
        assert user.check_password(password) is True

@pytest.mark.unit
def test_user_roles(db):
    """Test user role functionality."""
    # Test admin user
    admin_user = User(username="admin", password="Admin123", role="admin")
    db.session.add(admin_user)
    
    # Test regular user
    regular_user = User(username="user", password="UserPass123", role="user")
    db.session.add(regular_user)
    
    db.session.commit()
    
    # Test role checks
    assert admin_user.is_admin() is True
    assert regular_user.is_admin() is False
    
    # Test permissions
    assert admin_user.has_permission("view") is True
    assert admin_user.has_permission("create") is True
    assert admin_user.has_permission("update") is True
    assert admin_user.has_permission("delete") is True
    
    assert regular_user.has_permission("view") is True
    assert regular_user.has_permission("create") is False
    assert regular_user.has_permission("update") is False
    assert regular_user.has_permission("delete") is False

@pytest.mark.unit
def test_user_to_dict(db):
    """Test user to_dict method."""
    user = User(username="testuser", password="Password123", role="user")
    db.session.add(user)
    db.session.commit()
    
    user_dict = user.to_dict()
    
    assert user_dict["username"] == "testuser"
    assert user_dict["role"] == "user"
    assert user_dict["is_active"] is True
    assert "id" in user_dict
    assert "created_at" in user_dict
    assert "last_login" in user_dict
    assert "password" not in user_dict  # Password should not be in dict

@pytest.mark.unit
def test_user_update_last_login(db):
    """Test updating last login time."""
    user = User(username="testuser", password="Password123")
    db.session.add(user)
    db.session.commit()
    
    # Initially last_login should be None
    assert user.last_login is None
    
    # Update last login
    user.update_last_login()
    
    # Check that last_login was updated
    assert user.last_login is not None

@pytest.mark.unit
def test_user_repr():
    """Test user string representation."""
    user = User(username="testuser", password="Password123")
    
    assert repr(user) == "<User testuser>"

@pytest.mark.unit
def test_user_unique_username(db):
    """Test that usernames must be unique."""
    user1 = User(username="testuser", password="Password123")
    db.session.add(user1)
    db.session.commit()
    
    # Try to create another user with the same username
    user2 = User(username="testuser", password="Password456")
    db.session.add(user2)
    
    # This should raise an IntegrityError
    with pytest.raises(Exception):  # SQLAlchemy IntegrityError
        db.session.commit()