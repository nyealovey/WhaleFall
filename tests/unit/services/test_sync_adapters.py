"""
同步适配器单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.sync_adapters.base_sync_adapter import BaseSyncAdapter
from app.services.sync_adapters.mysql_sync_adapter import MySQLSyncAdapter
from app.services.sync_adapters.postgresql_sync_adapter import PostgreSQLSyncAdapter
from app.services.sync_adapters.sqlserver_sync_adapter import SQLServerSyncAdapter
from app.services.sync_adapters.oracle_sync_adapter import OracleSyncAdapter
from app.models.instance import Instance


class TestBaseSyncAdapter:
    """BaseSyncAdapter测试类"""
    
    def test_base_sync_adapter_init(self):
        """Test BaseSyncAdapter initialization."""
        # 2. Act
        adapter = BaseSyncAdapter()
        
        # 3. Assert
        assert adapter is not None
        assert adapter.sync_logger is not None
    
    def test_base_sync_adapter_abstract_methods(self):
        """Test BaseSyncAdapter abstract methods."""
        # 1. Arrange
        adapter = BaseSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # 2. Act & Assert
        with pytest.raises(NotImplementedError):
            adapter.get_database_accounts(instance, connection)
        
        with pytest.raises(NotImplementedError):
            adapter.extract_permissions({})
        
        with pytest.raises(NotImplementedError):
            adapter.format_account_data({})
        
        with pytest.raises(NotImplementedError):
            adapter.validate_account_data({})
        
        with pytest.raises(NotImplementedError):
            adapter.get_database_type()


class TestMySQLSyncAdapter:
    """MySQLSyncAdapter测试类"""
    
    def test_mysql_sync_adapter_init(self):
        """Test MySQLSyncAdapter initialization."""
        # 2. Act
        adapter = MySQLSyncAdapter()
        
        # 3. Assert
        assert adapter is not None
        assert adapter.sync_logger is not None
    
    def test_mysql_sync_adapter_get_database_type(self):
        """Test MySQLSyncAdapter get_database_type."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        
        # 2. Act
        db_type = adapter.get_database_type()
        
        # 3. Assert
        assert db_type == "mysql"
    
    def test_mysql_sync_adapter_get_database_accounts(self):
        """Test MySQLSyncAdapter get_database_accounts."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # Mock connection query results
        mock_results = [
            {"User": "user1", "Host": "localhost", "authentication_string": "hash1"},
            {"User": "user2", "Host": "%", "authentication_string": "hash2"}
        ]
        connection.execute.return_value.fetchall.return_value = mock_results
        
        # 2. Act
        result = adapter.get_database_accounts(instance, connection)
        
        # 3. Assert
        assert len(result) == 2
        assert result[0]["User"] == "user1"
        assert result[1]["User"] == "user2"
        connection.execute.assert_called_once()
    
    def test_mysql_sync_adapter_extract_permissions(self):
        """Test MySQLSyncAdapter extract_permissions."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        account_data = {
            "User": "testuser",
            "Host": "localhost",
            "authentication_string": "hash123"
        }
        
        # 2. Act
        result = adapter.extract_permissions(account_data)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["host"] == "localhost"
        assert result["password_hash"] == "hash123"
    
    def test_mysql_sync_adapter_format_account_data(self):
        """Test MySQLSyncAdapter format_account_data."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        raw_account = {
            "User": "testuser",
            "Host": "localhost",
            "authentication_string": "hash123"
        }
        
        # 2. Act
        result = adapter.format_account_data(raw_account)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["host"] == "localhost"
        assert result["password_hash"] == "hash123"
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_mysql_sync_adapter_validate_account_data(self):
        """Test MySQLSyncAdapter validate_account_data."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        
        # Test valid data
        valid_data = {
            "username": "testuser",
            "host": "localhost",
            "password_hash": "hash123"
        }
        
        # Test invalid data
        invalid_data = {
            "username": "",
            "host": "localhost",
            "password_hash": "hash123"
        }
        
        # 2. Act & Assert
        assert adapter.validate_account_data(valid_data) is True
        assert adapter.validate_account_data(invalid_data) is False
    
    def test_mysql_sync_adapter_get_database_accounts_empty(self):
        """Test MySQLSyncAdapter get_database_accounts with empty results."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # Mock empty results
        connection.execute.return_value.fetchall.return_value = []
        
        # 2. Act
        result = adapter.get_database_accounts(instance, connection)
        
        # 3. Assert
        assert result == []
    
    def test_mysql_sync_adapter_get_database_accounts_exception(self):
        """Test MySQLSyncAdapter get_database_accounts with exception."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # Mock exception
        connection.execute.side_effect = Exception("Database error")
        
        # 2. Act
        result = adapter.get_database_accounts(instance, connection)
        
        # 3. Assert
        assert result == []


class TestPostgreSQLSyncAdapter:
    """PostgreSQLSyncAdapter测试类"""
    
    def test_postgresql_sync_adapter_init(self):
        """Test PostgreSQLSyncAdapter initialization."""
        # 2. Act
        adapter = PostgreSQLSyncAdapter()
        
        # 3. Assert
        assert adapter is not None
        assert adapter.sync_logger is not None
    
    def test_postgresql_sync_adapter_get_database_type(self):
        """Test PostgreSQLSyncAdapter get_database_type."""
        # 1. Arrange
        adapter = PostgreSQLSyncAdapter()
        
        # 2. Act
        db_type = adapter.get_database_type()
        
        # 3. Assert
        assert db_type == "postgresql"
    
    def test_postgresql_sync_adapter_get_database_accounts(self):
        """Test PostgreSQLSyncAdapter get_database_accounts."""
        # 1. Arrange
        adapter = PostgreSQLSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # Mock connection query results
        mock_results = [
            {"usename": "user1", "usesysid": 1, "passwd": "hash1"},
            {"usename": "user2", "usesysid": 2, "passwd": "hash2"}
        ]
        connection.execute.return_value.fetchall.return_value = mock_results
        
        # 2. Act
        result = adapter.get_database_accounts(instance, connection)
        
        # 3. Assert
        assert len(result) == 2
        assert result[0]["usename"] == "user1"
        assert result[1]["usename"] == "user2"
        connection.execute.assert_called_once()
    
    def test_postgresql_sync_adapter_extract_permissions(self):
        """Test PostgreSQLSyncAdapter extract_permissions."""
        # 1. Arrange
        adapter = PostgreSQLSyncAdapter()
        account_data = {
            "usename": "testuser",
            "usesysid": 123,
            "passwd": "hash123"
        }
        
        # 2. Act
        result = adapter.extract_permissions(account_data)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["user_id"] == 123
        assert result["password_hash"] == "hash123"
    
    def test_postgresql_sync_adapter_format_account_data(self):
        """Test PostgreSQLSyncAdapter format_account_data."""
        # 1. Arrange
        adapter = PostgreSQLSyncAdapter()
        raw_account = {
            "usename": "testuser",
            "usesysid": 123,
            "passwd": "hash123"
        }
        
        # 2. Act
        result = adapter.format_account_data(raw_account)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["user_id"] == 123
        assert result["password_hash"] == "hash123"
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_postgresql_sync_adapter_validate_account_data(self):
        """Test PostgreSQLSyncAdapter validate_account_data."""
        # 1. Arrange
        adapter = PostgreSQLSyncAdapter()
        
        # Test valid data
        valid_data = {
            "username": "testuser",
            "user_id": 123,
            "password_hash": "hash123"
        }
        
        # Test invalid data
        invalid_data = {
            "username": "",
            "user_id": 123,
            "password_hash": "hash123"
        }
        
        # 2. Act & Assert
        assert adapter.validate_account_data(valid_data) is True
        assert adapter.validate_account_data(invalid_data) is False


class TestSQLServerSyncAdapter:
    """SQLServerSyncAdapter测试类"""
    
    def test_sqlserver_sync_adapter_init(self):
        """Test SQLServerSyncAdapter initialization."""
        # 2. Act
        adapter = SQLServerSyncAdapter()
        
        # 3. Assert
        assert adapter is not None
        assert adapter.sync_logger is not None
    
    def test_sqlserver_sync_adapter_get_database_type(self):
        """Test SQLServerSyncAdapter get_database_type."""
        # 1. Arrange
        adapter = SQLServerSyncAdapter()
        
        # 2. Act
        db_type = adapter.get_database_type()
        
        # 3. Assert
        assert db_type == "sqlserver"
    
    def test_sqlserver_sync_adapter_get_database_accounts(self):
        """Test SQLServerSyncAdapter get_database_accounts."""
        # 1. Arrange
        adapter = SQLServerSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # Mock connection query results
        mock_results = [
            {"name": "user1", "principal_id": 1, "type": "S"},
            {"name": "user2", "principal_id": 2, "type": "S"}
        ]
        connection.execute.return_value.fetchall.return_value = mock_results
        
        # 2. Act
        result = adapter.get_database_accounts(instance, connection)
        
        # 3. Assert
        assert len(result) == 2
        assert result[0]["name"] == "user1"
        assert result[1]["name"] == "user2"
        connection.execute.assert_called_once()
    
    def test_sqlserver_sync_adapter_extract_permissions(self):
        """Test SQLServerSyncAdapter extract_permissions."""
        # 1. Arrange
        adapter = SQLServerSyncAdapter()
        account_data = {
            "name": "testuser",
            "principal_id": 123,
            "type": "S"
        }
        
        # 2. Act
        result = adapter.extract_permissions(account_data)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["principal_id"] == 123
        assert result["type"] == "S"
    
    def test_sqlserver_sync_adapter_format_account_data(self):
        """Test SQLServerSyncAdapter format_account_data."""
        # 1. Arrange
        adapter = SQLServerSyncAdapter()
        raw_account = {
            "name": "testuser",
            "principal_id": 123,
            "type": "S"
        }
        
        # 2. Act
        result = adapter.format_account_data(raw_account)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["principal_id"] == 123
        assert result["type"] == "S"
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_sqlserver_sync_adapter_validate_account_data(self):
        """Test SQLServerSyncAdapter validate_account_data."""
        # 1. Arrange
        adapter = SQLServerSyncAdapter()
        
        # Test valid data
        valid_data = {
            "username": "testuser",
            "principal_id": 123,
            "type": "S"
        }
        
        # Test invalid data
        invalid_data = {
            "username": "",
            "principal_id": 123,
            "type": "S"
        }
        
        # 2. Act & Assert
        assert adapter.validate_account_data(valid_data) is True
        assert adapter.validate_account_data(invalid_data) is False


class TestOracleSyncAdapter:
    """OracleSyncAdapter测试类"""
    
    def test_oracle_sync_adapter_init(self):
        """Test OracleSyncAdapter initialization."""
        # 2. Act
        adapter = OracleSyncAdapter()
        
        # 3. Assert
        assert adapter is not None
        assert adapter.sync_logger is not None
    
    def test_oracle_sync_adapter_get_database_type(self):
        """Test OracleSyncAdapter get_database_type."""
        # 1. Arrange
        adapter = OracleSyncAdapter()
        
        # 2. Act
        db_type = adapter.get_database_type()
        
        # 3. Assert
        assert db_type == "oracle"
    
    def test_oracle_sync_adapter_get_database_accounts(self):
        """Test OracleSyncAdapter get_database_accounts."""
        # 1. Arrange
        adapter = OracleSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # Mock connection query results
        mock_results = [
            {"username": "user1", "user_id": 1, "account_status": "OPEN"},
            {"username": "user2", "user_id": 2, "account_status": "OPEN"}
        ]
        connection.execute.return_value.fetchall.return_value = mock_results
        
        # 2. Act
        result = adapter.get_database_accounts(instance, connection)
        
        # 3. Assert
        assert len(result) == 2
        assert result[0]["username"] == "user1"
        assert result[1]["username"] == "user2"
        connection.execute.assert_called_once()
    
    def test_oracle_sync_adapter_extract_permissions(self):
        """Test OracleSyncAdapter extract_permissions."""
        # 1. Arrange
        adapter = OracleSyncAdapter()
        account_data = {
            "username": "testuser",
            "user_id": 123,
            "account_status": "OPEN"
        }
        
        # 2. Act
        result = adapter.extract_permissions(account_data)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["user_id"] == 123
        assert result["account_status"] == "OPEN"
    
    def test_oracle_sync_adapter_format_account_data(self):
        """Test OracleSyncAdapter format_account_data."""
        # 1. Arrange
        adapter = OracleSyncAdapter()
        raw_account = {
            "username": "testuser",
            "user_id": 123,
            "account_status": "OPEN"
        }
        
        # 2. Act
        result = adapter.format_account_data(raw_account)
        
        # 3. Assert
        assert result["username"] == "testuser"
        assert result["user_id"] == 123
        assert result["account_status"] == "OPEN"
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_oracle_sync_adapter_validate_account_data(self):
        """Test OracleSyncAdapter validate_account_data."""
        # 1. Arrange
        adapter = OracleSyncAdapter()
        
        # Test valid data
        valid_data = {
            "username": "testuser",
            "user_id": 123,
            "account_status": "OPEN"
        }
        
        # Test invalid data
        invalid_data = {
            "username": "",
            "user_id": 123,
            "account_status": "OPEN"
        }
        
        # 2. Act & Assert
        assert adapter.validate_account_data(valid_data) is True
        assert adapter.validate_account_data(invalid_data) is False


class TestSyncAdapterIntegration:
    """同步适配器集成测试"""
    
    def test_adapter_factory_pattern(self):
        """Test adapter factory pattern."""
        # 1. Arrange
        adapters = {
            "mysql": MySQLSyncAdapter(),
            "postgresql": PostgreSQLSyncAdapter(),
            "sqlserver": SQLServerSyncAdapter(),
            "oracle": OracleSyncAdapter()
        }
        
        # 2. Act & Assert
        for db_type, adapter in adapters.items():
            assert adapter.get_database_type() == db_type
    
    def test_adapter_common_interface(self):
        """Test adapter common interface."""
        # 1. Arrange
        adapters = [
            MySQLSyncAdapter(),
            PostgreSQLSyncAdapter(),
            SQLServerSyncAdapter(),
            OracleSyncAdapter()
        ]
        
        # 2. Act & Assert
        for adapter in adapters:
            # All adapters should have these methods
            assert hasattr(adapter, 'get_database_accounts')
            assert hasattr(adapter, 'extract_permissions')
            assert hasattr(adapter, 'format_account_data')
            assert hasattr(adapter, 'validate_account_data')
            assert hasattr(adapter, 'get_database_type')
            
            # All adapters should return string for database type
            assert isinstance(adapter.get_database_type(), str)
    
    def test_adapter_error_handling(self):
        """Test adapter error handling."""
        # 1. Arrange
        adapter = MySQLSyncAdapter()
        instance = Mock(spec=Instance)
        connection = Mock()
        
        # Mock connection error
        connection.execute.side_effect = Exception("Connection error")
        
        # 2. Act
        result = adapter.get_database_accounts(instance, connection)
        
        # 3. Assert
        assert result == []
    
    def test_adapter_data_validation(self):
        """Test adapter data validation."""
        # 1. Arrange
        adapters = [
            MySQLSyncAdapter(),
            PostgreSQLSyncAdapter(),
            SQLServerSyncAdapter(),
            OracleSyncAdapter()
        ]
        
        # 2. Act & Assert
        for adapter in adapters:
            # Test valid data
            valid_data = {"username": "testuser"}
            assert adapter.validate_account_data(valid_data) is True
            
            # Test invalid data
            invalid_data = {"username": ""}
            assert adapter.validate_account_data(invalid_data) is False
    
    def test_adapter_data_formatting(self):
        """Test adapter data formatting."""
        # 1. Arrange
        adapters = [
            MySQLSyncAdapter(),
            PostgreSQLSyncAdapter(),
            SQLServerSyncAdapter(),
            OracleSyncAdapter()
        ]
        
        # 2. Act & Assert
        for adapter in adapters:
            # Test data formatting
            raw_data = {"username": "testuser"}
            formatted_data = adapter.format_account_data(raw_data)
            
            assert "username" in formatted_data
            assert "created_at" in formatted_data
            assert "updated_at" in formatted_data
    
    def test_adapter_permission_extraction(self):
        """Test adapter permission extraction."""
        # 1. Arrange
        adapters = [
            MySQLSyncAdapter(),
            PostgreSQLSyncAdapter(),
            SQLServerSyncAdapter(),
            OracleSyncAdapter()
        ]
        
        # 2. Act & Assert
        for adapter in adapters:
            # Test permission extraction
            account_data = {"username": "testuser"}
            permissions = adapter.extract_permissions(account_data)
            
            assert "username" in permissions
            assert isinstance(permissions, dict)
