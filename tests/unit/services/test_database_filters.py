"""
数据库过滤器单元测试
"""
import pytest
from unittest.mock import Mock, patch
from app.services.database_filters.base_filter import BaseDatabaseFilter
from app.services.database_filters.mysql_filter import MySQLFilter
from app.services.database_filters.postgresql_filter import PostgreSQLFilter
from app.services.database_filters.sqlserver_filter import SQLServerFilter
from app.services.database_filters.oracle_filter import OracleFilter


class TestBaseDatabaseFilter:
    """BaseDatabaseFilter测试类"""
    
    def test_base_filter_init(self):
        """Test BaseDatabaseFilter initialization."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["root", "admin"],
            "exclude_patterns": ["test_*", "temp_*"],
            "exclude_roles": ["readonly"],
            "include_only": False,
            "custom_rules": []
        }
        
        # 2. Act
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 3. Assert
        assert filter_obj.config_data == config_data
        assert filter_obj.exclude_users == ["root", "admin"]
        assert filter_obj.exclude_patterns == ["test_*", "temp_*"]
        assert filter_obj.exclude_roles == ["readonly"]
        assert filter_obj.include_only is False
        assert filter_obj.custom_rules == []
    
    def test_base_filter_init_empty_config(self):
        """Test BaseDatabaseFilter initialization with empty config."""
        # 2. Act
        filter_obj = BaseDatabaseFilter()
        
        # 3. Assert
        assert filter_obj.config_data == {}
        assert filter_obj.exclude_users == []
        assert filter_obj.exclude_patterns == []
        assert filter_obj.exclude_roles == []
        assert filter_obj.include_only is False
        assert filter_obj.custom_rules == []
    
    def test_should_include_user_excluded(self):
        """Test should_include_user with excluded user."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["root", "admin"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result = filter_obj.should_include_user("root")
        
        # 3. Assert
        assert result is False
    
    def test_should_include_user_not_excluded(self):
        """Test should_include_user with not excluded user."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["root", "admin"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result = filter_obj.should_include_user("normal_user")
        
        # 3. Assert
        assert result is True
    
    def test_should_include_user_pattern_match(self):
        """Test should_include_user with pattern match."""
        # 1. Arrange
        config_data = {
            "exclude_patterns": ["test_*", "temp_*"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result = filter_obj.should_include_user("test_user")
        
        # 3. Assert
        assert result is False
    
    def test_should_include_user_pattern_no_match(self):
        """Test should_include_user with pattern no match."""
        # 1. Arrange
        config_data = {
            "exclude_patterns": ["test_*", "temp_*"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result = filter_obj.should_include_user("normal_user")
        
        # 3. Assert
        assert result is True
    
    def test_should_include_user_include_only_true(self):
        """Test should_include_user with include_only=True."""
        # 1. Arrange
        config_data = {
            "include_only": True,
            "exclude_users": ["root", "admin"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result = filter_obj.should_include_user("root")
        
        # 3. Assert
        assert result is True
    
    def test_should_include_user_include_only_false(self):
        """Test should_include_user with include_only=False."""
        # 1. Arrange
        config_data = {
            "include_only": False,
            "exclude_users": ["root", "admin"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result = filter_obj.should_include_user("root")
        
        # 3. Assert
        assert result is False
    
    def test_should_include_user_empty_username(self):
        """Test should_include_user with empty username."""
        # 1. Arrange
        filter_obj = BaseDatabaseFilter()
        
        # 2. Act
        result = filter_obj.should_include_user("")
        
        # 3. Assert
        assert result is False
    
    def test_should_include_user_none_username(self):
        """Test should_include_user with None username."""
        # 1. Arrange
        filter_obj = BaseDatabaseFilter()
        
        # 2. Act
        result = filter_obj.should_include_user(None)
        
        # 3. Assert
        assert result is False
    
    def test_should_include_user_case_sensitive(self):
        """Test should_include_user case sensitivity."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["Root", "Admin"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result1 = filter_obj.should_include_user("root")
        result2 = filter_obj.should_include_user("Root")
        
        # 3. Assert
        assert result1 is True  # Case sensitive
        assert result2 is False
    
    def test_should_include_user_multiple_patterns(self):
        """Test should_include_user with multiple patterns."""
        # 1. Arrange
        config_data = {
            "exclude_patterns": ["test_*", "temp_*", "backup_*"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result1 = filter_obj.should_include_user("test_user")
        result2 = filter_obj.should_include_user("temp_user")
        result3 = filter_obj.should_include_user("backup_user")
        result4 = filter_obj.should_include_user("normal_user")
        
        # 3. Assert
        assert result1 is False
        assert result2 is False
        assert result3 is False
        assert result4 is True
    
    def test_should_include_user_complex_patterns(self):
        """Test should_include_user with complex patterns."""
        # 1. Arrange
        config_data = {
            "exclude_patterns": ["user_*_test", "admin_*", "*_backup"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result1 = filter_obj.should_include_user("user_123_test")
        result2 = filter_obj.should_include_user("admin_user")
        result3 = filter_obj.should_include_user("data_backup")
        result4 = filter_obj.should_include_user("normal_user")
        
        # 3. Assert
        assert result1 is False
        assert result2 is False
        assert result3 is False
        assert result4 is True
    
    def test_should_include_user_regex_patterns(self):
        """Test should_include_user with regex patterns."""
        # 1. Arrange
        config_data = {
            "exclude_patterns": [r"^test\d+$", r"^admin.*", r".*_temp$"]
        }
        filter_obj = BaseDatabaseFilter(config_data)
        
        # 2. Act
        result1 = filter_obj.should_include_user("test123")
        result2 = filter_obj.should_include_user("admin_user")
        result3 = filter_obj.should_include_user("user_temp")
        result4 = filter_obj.should_include_user("normal_user")
        
        # 3. Assert
        assert result1 is False
        assert result2 is False
        assert result3 is False
        assert result4 is True


class TestMySQLFilter:
    """MySQLFilter测试类"""
    
    def test_mysql_filter_init(self):
        """Test MySQLFilter initialization."""
        # 2. Act
        filter_obj = MySQLFilter()
        
        # 3. Assert
        assert filter_obj.db_type == "mysql"
    
    def test_mysql_filter_get_database_type(self):
        """Test MySQLFilter get_database_type."""
        # 2. Act
        filter_obj = MySQLFilter()
        db_type = filter_obj.get_database_type()
        
        # 3. Assert
        assert db_type == "mysql"
    
    def test_mysql_filter_should_include_user(self):
        """Test MySQLFilter should_include_user."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["root", "mysql.sys"],
            "exclude_patterns": ["test_*"]
        }
        filter_obj = MySQLFilter(config_data)
        
        # 2. Act & Assert
        assert filter_obj.should_include_user("root") is False
        assert filter_obj.should_include_user("mysql.sys") is False
        assert filter_obj.should_include_user("test_user") is False
        assert filter_obj.should_include_user("normal_user") is True


class TestPostgreSQLFilter:
    """PostgreSQLFilter测试类"""
    
    def test_postgresql_filter_init(self):
        """Test PostgreSQLFilter initialization."""
        # 2. Act
        filter_obj = PostgreSQLFilter()
        
        # 3. Assert
        assert filter_obj.db_type == "postgresql"
    
    def test_postgresql_filter_get_database_type(self):
        """Test PostgreSQLFilter get_database_type."""
        # 2. Act
        filter_obj = PostgreSQLFilter()
        db_type = filter_obj.get_database_type()
        
        # 3. Assert
        assert db_type == "postgresql"
    
    def test_postgresql_filter_should_include_user(self):
        """Test PostgreSQLFilter should_include_user."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["postgres", "rdsadmin"],
            "exclude_patterns": ["test_*"]
        }
        filter_obj = PostgreSQLFilter(config_data)
        
        # 2. Act & Assert
        assert filter_obj.should_include_user("postgres") is False
        assert filter_obj.should_include_user("rdsadmin") is False
        assert filter_obj.should_include_user("test_user") is False
        assert filter_obj.should_include_user("normal_user") is True


class TestSQLServerFilter:
    """SQLServerFilter测试类"""
    
    def test_sqlserver_filter_init(self):
        """Test SQLServerFilter initialization."""
        # 2. Act
        filter_obj = SQLServerFilter()
        
        # 3. Assert
        assert filter_obj.db_type == "sqlserver"
    
    def test_sqlserver_filter_get_database_type(self):
        """Test SQLServerFilter get_database_type."""
        # 2. Act
        filter_obj = SQLServerFilter()
        db_type = filter_obj.get_database_type()
        
        # 3. Assert
        assert db_type == "sqlserver"
    
    def test_sqlserver_filter_should_include_user(self):
        """Test SQLServerFilter should_include_user."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["sa", "rdsadmin"],
            "exclude_patterns": ["test_*"]
        }
        filter_obj = SQLServerFilter(config_data)
        
        # 2. Act & Assert
        assert filter_obj.should_include_user("sa") is False
        assert filter_obj.should_include_user("rdsadmin") is False
        assert filter_obj.should_include_user("test_user") is False
        assert filter_obj.should_include_user("normal_user") is True


class TestOracleFilter:
    """OracleFilter测试类"""
    
    def test_oracle_filter_init(self):
        """Test OracleFilter initialization."""
        # 2. Act
        filter_obj = OracleFilter()
        
        # 3. Assert
        assert filter_obj.db_type == "oracle"
    
    def test_oracle_filter_get_database_type(self):
        """Test OracleFilter get_database_type."""
        # 2. Act
        filter_obj = OracleFilter()
        db_type = filter_obj.get_database_type()
        
        # 3. Assert
        assert db_type == "oracle"
    
    def test_oracle_filter_should_include_user(self):
        """Test OracleFilter should_include_user."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["SYS", "SYSTEM"],
            "exclude_patterns": ["test_*"]
        }
        filter_obj = OracleFilter(config_data)
        
        # 2. Act & Assert
        assert filter_obj.should_include_user("SYS") is False
        assert filter_obj.should_include_user("SYSTEM") is False
        assert filter_obj.should_include_user("test_user") is False
        assert filter_obj.should_include_user("normal_user") is True


class TestDatabaseFilterIntegration:
    """数据库过滤器集成测试"""
    
    def test_filter_chain(self):
        """Test filter chain with multiple conditions."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["root", "admin"],
            "exclude_patterns": ["test_*", "temp_*"],
            "exclude_roles": ["readonly"],
            "include_only": False
        }
        filter_obj = MySQLFilter(config_data)
        
        # 2. Act & Assert
        # Should be excluded by exclude_users
        assert filter_obj.should_include_user("root") is False
        assert filter_obj.should_include_user("admin") is False
        
        # Should be excluded by exclude_patterns
        assert filter_obj.should_include_user("test_user") is False
        assert filter_obj.should_include_user("temp_user") is False
        
        # Should be included
        assert filter_obj.should_include_user("normal_user") is True
        assert filter_obj.should_include_user("app_user") is True
    
    def test_filter_with_include_only(self):
        """Test filter with include_only=True."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["root", "admin"],
            "include_only": True
        }
        filter_obj = MySQLFilter(config_data)
        
        # 2. Act & Assert
        # Should be included because include_only=True
        assert filter_obj.should_include_user("root") is True
        assert filter_obj.should_include_user("admin") is True
        assert filter_obj.should_include_user("normal_user") is True
    
    def test_filter_with_custom_rules(self):
        """Test filter with custom rules."""
        # 1. Arrange
        config_data = {
            "custom_rules": [
                {"type": "exclude", "pattern": "custom_*"},
                {"type": "include", "pattern": "special_*"}
            ]
        }
        filter_obj = MySQLFilter(config_data)
        
        # 2. Act & Assert
        # Custom rules are not implemented in base class
        # This test verifies the structure is correct
        assert filter_obj.custom_rules == config_data["custom_rules"]
    
    def test_filter_performance(self):
        """Test filter performance with many patterns."""
        # 1. Arrange
        config_data = {
            "exclude_patterns": [f"pattern_{i}_*" for i in range(100)]
        }
        filter_obj = MySQLFilter(config_data)
        
        # 2. Act
        import time
        start_time = time.time()
        
        for i in range(1000):
            filter_obj.should_include_user(f"user_{i}")
        
        end_time = time.time()
        
        # 3. Assert
        # Should complete within reasonable time
        assert (end_time - start_time) < 1.0  # Less than 1 second
    
    def test_filter_edge_cases(self):
        """Test filter edge cases."""
        # 1. Arrange
        filter_obj = MySQLFilter()
        
        # 2. Act & Assert
        # Empty string
        assert filter_obj.should_include_user("") is False
        
        # None
        assert filter_obj.should_include_user(None) is False
        
        # Very long username
        long_username = "x" * 1000
        assert filter_obj.should_include_user(long_username) is True
        
        # Username with special characters
        special_username = "user@domain.com"
        assert filter_obj.should_include_user(special_username) is True
        
        # Username with spaces
        space_username = "user name"
        assert filter_obj.should_include_user(space_username) is True
    
    def test_filter_unicode_username(self):
        """Test filter with unicode username."""
        # 1. Arrange
        config_data = {
            "exclude_users": ["测试用户", "管理员"]
        }
        filter_obj = MySQLFilter(config_data)
        
        # 2. Act & Assert
        assert filter_obj.should_include_user("测试用户") is False
        assert filter_obj.should_include_user("管理员") is False
        assert filter_obj.should_include_user("普通用户") is True
    
    def test_filter_case_insensitive_patterns(self):
        """Test filter with case insensitive patterns."""
        # 1. Arrange
        config_data = {
            "exclude_patterns": ["TEST_*", "TEMP_*"]
        }
        filter_obj = MySQLFilter(config_data)
        
        # 2. Act & Assert
        # Patterns are case sensitive by default
        assert filter_obj.should_include_user("test_user") is True
        assert filter_obj.should_include_user("TEST_USER") is False
        assert filter_obj.should_include_user("temp_user") is True
        assert filter_obj.should_include_user("TEMP_USER") is False
