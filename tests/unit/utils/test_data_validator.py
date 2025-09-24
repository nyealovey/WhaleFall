"""
DataValidator工具类单元测试
"""
import pytest
from app.utils.data_validator import DataValidator


@pytest.mark.unit
def test_data_validator_init():
    """Test DataValidator initialization."""
    validator = DataValidator()
    assert validator is not None


@pytest.mark.unit
def test_validate_instance_data_valid():
    """Test validating valid instance data."""
    data = {
        "name": "test-mysql",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database_name": "testdb",
        "description": "Test MySQL instance"
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_instance_data_missing_required_fields():
    """Test validating instance data with missing required fields."""
    data = {
        "name": "test-mysql",
        # Missing db_type, host, port
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is False
    assert "必填的" in error


@pytest.mark.unit
def test_validate_instance_data_invalid_name():
    """Test validating instance data with invalid name."""
    data = {
        "name": "",  # Empty name
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is False
    assert "名称" in error


@pytest.mark.unit
def test_validate_instance_data_invalid_db_type():
    """Test validating instance data with invalid database type."""
    data = {
        "name": "test-mysql",
        "db_type": "invalid_db",  # Invalid database type
        "host": "localhost",
        "port": 3306
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is False
    assert "数据库类型" in error


@pytest.mark.unit
def test_validate_instance_data_invalid_host():
    """Test validating instance data with invalid host."""
    data = {
        "name": "test-mysql",
        "db_type": "mysql",
        "host": "",  # Empty host
        "port": 3306
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is False
    assert "主机" in error


@pytest.mark.unit
def test_validate_instance_data_invalid_port():
    """Test validating instance data with invalid port."""
    data = {
        "name": "test-mysql",
        "db_type": "mysql",
        "host": "localhost",
        "port": 99999  # Invalid port
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is False
    assert "端口" in error


@pytest.mark.unit
def test_validate_instance_data_invalid_database_name():
    """Test validating instance data with invalid database name."""
    data = {
        "name": "test-mysql",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "database_name": "x" * 100  # Too long
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is False
    assert "数据库名称" in error


@pytest.mark.unit
def test_validate_instance_data_invalid_description():
    """Test validating instance data with invalid description."""
    data = {
        "name": "test-mysql",
        "db_type": "mysql",
        "host": "localhost",
        "port": 3306,
        "description": "x" * 1000  # Too long
    }
    
    is_valid, error = DataValidator.validate_instance_data(data)
    
    assert is_valid is False
    assert "描述" in error


@pytest.mark.unit
def test_validate_credential_data_valid():
    """Test validating valid credential data."""
    data = {
        "name": "test-credential",
        "credential_type": "database",
        "username": "testuser",
        "password": "testpass",
        "db_type": "mysql",
        "description": "Test credential"
    }
    
    is_valid, error = DataValidator.validate_credential_data(data)
    
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_credential_data_missing_required_fields():
    """Test validating credential data with missing required fields."""
    data = {
        "name": "test-credential",
        # Missing credential_type, username, password
    }
    
    is_valid, error = DataValidator.validate_credential_data(data)
    
    assert is_valid is False
    assert "必填的" in error


@pytest.mark.unit
def test_validate_credential_data_invalid_username():
    """Test validating credential data with invalid username."""
    data = {
        "name": "test-credential",
        "credential_type": "database",
        "username": "",  # Empty username
        "password": "testpass",
        "db_type": "mysql"
    }
    
    is_valid, error = DataValidator.validate_credential_data(data)
    
    assert is_valid is False
    assert "用户名" in error


@pytest.mark.unit
def test_validate_credential_data_invalid_password():
    """Test validating credential data with invalid password."""
    data = {
        "name": "test-credential",
        "credential_type": "database",
        "username": "testuser",
        "password": "",  # Empty password
        "db_type": "mysql"
    }
    
    is_valid, error = DataValidator.validate_credential_data(data)
    
    assert is_valid is False
    assert "密码" in error


@pytest.mark.unit
def test_validate_credential_data_invalid_credential_type():
    """Test validating credential data with invalid credential type."""
    data = {
        "name": "test-credential",
        "credential_type": "invalid_type",
        "username": "testuser",
        "password": "testpass",
        "db_type": "mysql"
    }
    
    is_valid, error = DataValidator.validate_credential_data(data)
    
    assert is_valid is False
    assert "凭据类型" in error


@pytest.mark.unit
def test_validate_tag_data_valid():
    """Test validating valid tag data."""
    data = {
        "name": "production",
        "display_name": "生产环境",
        "category": "environment",
        "color": "danger",
        "description": "生产环境标签"
    }
    
    is_valid, error = DataValidator.validate_tag_data(data)
    
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_tag_data_missing_required_fields():
    """Test validating tag data with missing required fields."""
    data = {
        "name": "production",
        # Missing display_name, category
    }
    
    is_valid, error = DataValidator.validate_tag_data(data)
    
    assert is_valid is False
    assert "必填的" in error


@pytest.mark.unit
def test_validate_tag_data_invalid_name():
    """Test validating tag data with invalid name."""
    data = {
        "name": "",  # Empty name
        "display_name": "生产环境",
        "category": "environment"
    }
    
    is_valid, error = DataValidator.validate_tag_data(data)
    
    assert is_valid is False
    assert "名称" in error


@pytest.mark.unit
def test_validate_tag_data_invalid_display_name():
    """Test validating tag data with invalid display name."""
    data = {
        "name": "production",
        "display_name": "",  # Empty display name
        "category": "environment"
    }
    
    is_valid, error = DataValidator.validate_tag_data(data)
    
    assert is_valid is False
    assert "显示名称" in error


@pytest.mark.unit
def test_validate_tag_data_invalid_category():
    """Test validating tag data with invalid category."""
    data = {
        "name": "production",
        "display_name": "生产环境",
        "category": ""  # Empty category
    }
    
    is_valid, error = DataValidator.validate_tag_data(data)
    
    assert is_valid is False
    assert "分类" in error


@pytest.mark.unit
def test_validate_tag_data_invalid_color():
    """Test validating tag data with invalid color."""
    data = {
        "name": "production",
        "display_name": "生产环境",
        "category": "environment",
        "color": "invalid_color"  # Invalid color
    }
    
    is_valid, error = DataValidator.validate_tag_data(data)
    
    assert is_valid is False
    assert "颜色" in error


@pytest.mark.unit
def test_validate_user_data_valid():
    """Test validating valid user data."""
    data = {
        "username": "testuser",
        "password": "TestPass123",
        "role": "user",
        "is_active": True
    }
    
    is_valid, error = DataValidator.validate_user_data(data)
    
    assert is_valid is True
    assert error is None


@pytest.mark.unit
def test_validate_user_data_missing_required_fields():
    """Test validating user data with missing required fields."""
    data = {
        "username": "testuser",
        # Missing password
    }
    
    is_valid, error = DataValidator.validate_user_data(data)
    
    assert is_valid is False
    assert "必填的" in error


@pytest.mark.unit
def test_validate_user_data_invalid_username():
    """Test validating user data with invalid username."""
    data = {
        "username": "",  # Empty username
        "password": "TestPass123",
        "role": "user"
    }
    
    is_valid, error = DataValidator.validate_user_data(data)
    
    assert is_valid is False
    assert "用户名" in error


@pytest.mark.unit
def test_validate_user_data_invalid_password():
    """Test validating user data with invalid password."""
    data = {
        "username": "testuser",
        "password": "weak",  # Weak password
        "role": "user"
    }
    
    is_valid, error = DataValidator.validate_user_data(data)
    
    assert is_valid is False
    assert "密码" in error


@pytest.mark.unit
def test_validate_user_data_invalid_role():
    """Test validating user data with invalid role."""
    data = {
        "username": "testuser",
        "password": "TestPass123",
        "role": "invalid_role"  # Invalid role
    }
    
    is_valid, error = DataValidator.validate_user_data(data)
    
    assert is_valid is False
    assert "角色" in error


@pytest.mark.unit
def test_validate_name_valid():
    """Test validating valid name."""
    valid_names = [
        "test-name",
        "test_name",
        "test123",
        "TestName",
        "test-name-123"
    ]
    
    for name in valid_names:
        error = DataValidator._validate_name(name)
        assert error is None


@pytest.mark.unit
def test_validate_name_invalid():
    """Test validating invalid name."""
    invalid_names = [
        "",  # Empty
        "x" * 101,  # Too long
        "test name",  # Space
        "test@name",  # Special char
        "123",  # Starts with number
    ]
    
    for name in invalid_names:
        error = DataValidator._validate_name(name)
        assert error is not None


@pytest.mark.unit
def test_validate_db_type_valid():
    """Test validating valid database type."""
    valid_types = ["mysql", "postgresql", "sqlserver", "oracle"]
    
    for db_type in valid_types:
        error = DataValidator._validate_db_type(db_type)
        assert error is None


@pytest.mark.unit
def test_validate_db_type_invalid():
    """Test validating invalid database type."""
    invalid_types = ["", "invalid", "MySQL", "postgres", None]
    
    for db_type in invalid_types:
        error = DataValidator._validate_db_type(db_type)
        assert error is not None


@pytest.mark.unit
def test_validate_host_valid():
    """Test validating valid host."""
    valid_hosts = [
        "localhost",
        "192.168.1.1",
        "example.com",
        "subdomain.example.com",
        "test-server"
    ]
    
    for host in valid_hosts:
        error = DataValidator._validate_host(host)
        assert error is None


@pytest.mark.unit
def test_validate_host_invalid():
    """Test validating invalid host."""
    invalid_hosts = [
        "",  # Empty
        "x" * 256,  # Too long
        "test host",  # Space
        "test@host",  # Special char
    ]
    
    for host in invalid_hosts:
        error = DataValidator._validate_host(host)
        assert error is not None


@pytest.mark.unit
def test_validate_port_valid():
    """Test validating valid port."""
    valid_ports = [1, 80, 443, 3306, 5432, 1521, 1433, 65535]
    
    for port in valid_ports:
        error = DataValidator._validate_port(port)
        assert error is None


@pytest.mark.unit
def test_validate_port_invalid():
    """Test validating invalid port."""
    invalid_ports = [0, -1, 65536, 70000, "80", None]
    
    for port in invalid_ports:
        error = DataValidator._validate_port(port)
        assert error is not None


@pytest.mark.unit
def test_validate_database_name_valid():
    """Test validating valid database name."""
    valid_names = [
        "testdb",
        "test_db",
        "test123",
        "TestDB",
        "test-db"
    ]
    
    for name in valid_names:
        error = DataValidator._validate_database_name(name)
        assert error is None


@pytest.mark.unit
def test_validate_database_name_invalid():
    """Test validating invalid database name."""
    invalid_names = [
        "",  # Empty
        "x" * 65,  # Too long
        "test db",  # Space
        "test@db",  # Special char
        "123",  # Starts with number
    ]
    
    for name in invalid_names:
        error = DataValidator._validate_database_name(name)
        assert error is not None


@pytest.mark.unit
def test_validate_username_valid():
    """Test validating valid username."""
    valid_usernames = [
        "testuser",
        "test_user",
        "test123",
        "TestUser",
        "user.name"
    ]
    
    for username in valid_usernames:
        error = DataValidator._validate_username(username)
        assert error is None


@pytest.mark.unit
def test_validate_username_invalid():
    """Test validating invalid username."""
    invalid_usernames = [
        "",  # Empty
        "x" * 257,  # Too long
        "test user",  # Space
        "test@user",  # Special char
        "123",  # Too short
    ]
    
    for username in invalid_usernames:
        error = DataValidator._validate_username(username)
        assert error is not None


@pytest.mark.unit
def test_validate_password_strength_valid():
    """Test validating valid password strength."""
    valid_passwords = [
        "Password123",
        "MySecure123",
        "TestPass456",
        "StrongP@ss1"
    ]
    
    for password in valid_passwords:
        error = DataValidator._validate_password_strength(password)
        assert error is None


@pytest.mark.unit
def test_validate_password_strength_invalid():
    """Test validating invalid password strength."""
    invalid_passwords = [
        "1234567",  # Too short
        "password",  # No uppercase, no number
        "PASSWORD",  # No lowercase, no number
        "Password",  # No number
        "12345678",  # No letter
        ""  # Empty
    ]
    
    for password in invalid_passwords:
        error = DataValidator._validate_password_strength(password)
        assert error is not None


@pytest.mark.unit
def test_validate_credential_type_valid():
    """Test validating valid credential type."""
    valid_types = ["database", "api", "ssh", "ldap"]
    
    for cred_type in valid_types:
        error = DataValidator._validate_credential_type(cred_type)
        assert error is None


@pytest.mark.unit
def test_validate_credential_type_invalid():
    """Test validating invalid credential type."""
    invalid_types = ["", "invalid", "Database", "API", None]
    
    for cred_type in invalid_types:
        error = DataValidator._validate_credential_type(cred_type)
        assert error is not None


@pytest.mark.unit
def test_validate_tag_color_valid():
    """Test validating valid tag color."""
    valid_colors = ["primary", "success", "info", "warning", "danger", "secondary", "light", "dark"]
    
    for color in valid_colors:
        error = DataValidator._validate_tag_color(color)
        assert error is None


@pytest.mark.unit
def test_validate_tag_color_invalid():
    """Test validating invalid tag color."""
    invalid_colors = ["", "invalid", "red", "blue", None]
    
    for color in invalid_colors:
        error = DataValidator._validate_tag_color(color)
        assert error is not None


@pytest.mark.unit
def test_validate_user_role_valid():
    """Test validating valid user role."""
    valid_roles = ["admin", "user", "viewer"]
    
    for role in valid_roles:
        error = DataValidator._validate_user_role(role)
        assert error is None


@pytest.mark.unit
def test_validate_user_role_invalid():
    """Test validating invalid user role."""
    invalid_roles = ["", "invalid", "Admin", "User", None]
    
    for role in invalid_roles:
        error = DataValidator._validate_user_role(role)
        assert error is not None


@pytest.mark.unit
def test_validate_string_length_valid():
    """Test validating valid string length."""
    # Test with valid length
    error = DataValidator._validate_string_length("test", "field", 1, 10)
    assert error is None


@pytest.mark.unit
def test_validate_string_length_invalid():
    """Test validating invalid string length."""
    # Test with empty string
    error = DataValidator._validate_string_length("", "field", 1, 10)
    assert error is not None
    
    # Test with too long string
    error = DataValidator._validate_string_length("x" * 11, "field", 1, 10)
    assert error is not None


@pytest.mark.unit
def test_validate_string_length_optional():
    """Test validating optional string length."""
    # Test with None (optional field)
    error = DataValidator._validate_string_length(None, "field", 1, 10, required=False)
    assert error is None
    
    # Test with empty string (optional field)
    error = DataValidator._validate_string_length("", "field", 1, 10, required=False)
    assert error is None


@pytest.mark.unit
def test_validate_integer_range_valid():
    """Test validating valid integer range."""
    # Test with valid range
    error = DataValidator._validate_integer_range(5, "field", 1, 10)
    assert error is None


@pytest.mark.unit
def test_validate_integer_range_invalid():
    """Test validating invalid integer range."""
    # Test with value below range
    error = DataValidator._validate_integer_range(0, "field", 1, 10)
    assert error is not None
    
    # Test with value above range
    error = DataValidator._validate_integer_range(11, "field", 1, 10)
    assert error is None


@pytest.mark.unit
def test_validate_integer_range_optional():
    """Test validating optional integer range."""
    # Test with None (optional field)
    error = DataValidator._validate_integer_range(None, "field", 1, 10, required=False)
    assert error is None


@pytest.mark.unit
def test_validate_regex_pattern_valid():
    """Test validating valid regex pattern."""
    # Test with valid pattern
    error = DataValidator._validate_regex_pattern("test123", "field", r"^[a-zA-Z0-9]+$")
    assert error is None


@pytest.mark.unit
def test_validate_regex_pattern_invalid():
    """Test validating invalid regex pattern."""
    # Test with invalid pattern
    error = DataValidator._validate_regex_pattern("test@123", "field", r"^[a-zA-Z0-9]+$")
    assert error is not None


@pytest.mark.unit
def test_validate_regex_pattern_optional():
    """Test validating optional regex pattern."""
    # Test with None (optional field)
    error = DataValidator._validate_regex_pattern(None, "field", r"^[a-zA-Z0-9]+$", required=False)
    assert error is None


@pytest.mark.unit
def test_validate_choice_valid():
    """Test validating valid choice."""
    # Test with valid choice
    error = DataValidator._validate_choice("mysql", "field", ["mysql", "postgresql", "sqlserver"])
    assert error is None


@pytest.mark.unit
def test_validate_choice_invalid():
    """Test validating invalid choice."""
    # Test with invalid choice
    error = DataValidator._validate_choice("invalid", "field", ["mysql", "postgresql", "sqlserver"])
    assert error is not None


@pytest.mark.unit
def test_validate_choice_optional():
    """Test validating optional choice."""
    # Test with None (optional field)
    error = DataValidator._validate_choice(None, "field", ["mysql", "postgresql", "sqlserver"], required=False)
    assert error is None


@pytest.mark.unit
def test_validate_required_fields_valid():
    """Test validating valid required fields."""
    data = {"field1": "value1", "field2": "value2", "field3": "value3"}
    required_fields = ["field1", "field2", "field3"]
    
    error = DataValidator._validate_required_fields(data, required_fields)
    assert error is None


@pytest.mark.unit
def test_validate_required_fields_invalid():
    """Test validating invalid required fields."""
    data = {"field1": "value1", "field2": "value2"}
    required_fields = ["field1", "field2", "field3"]  # field3 is missing
    
    error = DataValidator._validate_required_fields(data, required_fields)
    assert error is not None
    assert "field3" in error


@pytest.mark.unit
def test_validate_required_fields_empty_values():
    """Test validating required fields with empty values."""
    data = {"field1": "", "field2": None, "field3": "value3"}
    required_fields = ["field1", "field2", "field3"]
    
    error = DataValidator._validate_required_fields(data, required_fields)
    assert error is not None
    assert "field1" in error
    assert "field2" in error


@pytest.mark.unit
def test_validate_required_fields_none_data():
    """Test validating required fields with None data."""
    data = None
    required_fields = ["field1", "field2"]
    
    error = DataValidator._validate_required_fields(data, required_fields)
    assert error is not None


@pytest.mark.unit
def test_validate_required_fields_empty_required():
    """Test validating required fields with empty required list."""
    data = {"field1": "value1"}
    required_fields = []
    
    error = DataValidator._validate_required_fields(data, required_fields)
    assert error is None


@pytest.mark.unit
def test_validate_required_fields_none_required():
    """Test validating required fields with None required list."""
    data = {"field1": "value1"}
    required_fields = None
    
    error = DataValidator._validate_required_fields(data, required_fields)
    assert error is None

