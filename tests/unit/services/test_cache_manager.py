"""
CacheManager单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.cache_manager import CacheManager


@pytest.mark.unit
def test_cache_manager_init():
    """Test CacheManager initialization."""
    cache_manager = CacheManager()
    assert cache_manager is not None
    assert cache_manager.cache is None
    assert cache_manager.default_ttl == 7 * 24 * 3600  # 7 days


@pytest.mark.unit
def test_cache_manager_init_with_cache():
    """Test CacheManager initialization with cache."""
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    assert cache_manager.cache == mock_cache


@pytest.mark.unit
def test_generate_cache_key():
    """Test cache key generation."""
    cache_manager = CacheManager()
    
    # Test with all parameters
    key = cache_manager._generate_cache_key("db_perms", 1, "testuser", "testdb")
    assert key.startswith("whalefall:")
    assert len(key) > 10  # Should be hashed
    
    # Test without db_name
    key2 = cache_manager._generate_cache_key("db_perms", 1, "testuser")
    assert key2.startswith("whalefall:")
    assert key != key2  # Different keys for different parameters


@pytest.mark.unit
def test_generate_cache_key_consistency():
    """Test cache key generation consistency."""
    cache_manager = CacheManager()
    
    # Same parameters should generate same key
    key1 = cache_manager._generate_cache_key("db_perms", 1, "testuser", "testdb")
    key2 = cache_manager._generate_cache_key("db_perms", 1, "testuser", "testdb")
    assert key1 == key2
    
    # Different parameters should generate different keys
    key3 = cache_manager._generate_cache_key("db_perms", 2, "testuser", "testdb")
    assert key1 != key3


@pytest.mark.unit
def test_get_database_permissions_cache_success():
    """Test getting database permissions cache successfully."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    cached_data = {
        "roles": ["admin", "user"],
        "permissions": ["SELECT", "INSERT", "UPDATE"]
    }
    mock_cache.get.return_value = cached_data
    
    # 2. Act
    result = cache_manager.get_database_permissions_cache(1, "testuser", "testdb")
    
    # 3. Assert
    assert result is not None
    roles, permissions = result
    assert roles == ["admin", "user"]
    assert permissions == ["SELECT", "INSERT", "UPDATE"]


@pytest.mark.unit
def test_get_database_permissions_cache_string_data():
    """Test getting database permissions cache with string data."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    cached_data = '{"roles": ["admin"], "permissions": ["SELECT"]}'
    mock_cache.get.return_value = cached_data
    
    # 2. Act
    result = cache_manager.get_database_permissions_cache(1, "testuser", "testdb")
    
    # 3. Assert
    assert result is not None
    roles, permissions = result
    assert roles == ["admin"]
    assert permissions == ["SELECT"]


@pytest.mark.unit
def test_get_database_permissions_cache_miss():
    """Test getting database permissions cache miss."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.get.return_value = None
    
    # 2. Act
    result = cache_manager.get_database_permissions_cache(1, "testuser", "testdb")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_get_database_permissions_cache_no_cache():
    """Test getting database permissions cache when no cache instance."""
    # 1. Arrange
    cache_manager = CacheManager(cache=None)
    
    # 2. Act
    result = cache_manager.get_database_permissions_cache(1, "testuser", "testdb")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_get_database_permissions_cache_exception():
    """Test getting database permissions cache with exception."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.get.side_effect = Exception("Cache error")
    
    # 2. Act
    result = cache_manager.get_database_permissions_cache(1, "testuser", "testdb")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_set_database_permissions_cache_success():
    """Test setting database permissions cache successfully."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    roles = ["admin", "user"]
    permissions = ["SELECT", "INSERT", "UPDATE"]
    
    # 2. Act
    result = cache_manager.set_database_permissions_cache(1, "testuser", "testdb", roles, permissions)
    
    # 3. Assert
    assert result is True
    mock_cache.set.assert_called_once()


@pytest.mark.unit
def test_set_database_permissions_cache_no_cache():
    """Test setting database permissions cache when no cache instance."""
    # 1. Arrange
    cache_manager = CacheManager(cache=None)
    
    roles = ["admin", "user"]
    permissions = ["SELECT", "INSERT", "UPDATE"]
    
    # 2. Act
    result = cache_manager.set_database_permissions_cache(1, "testuser", "testdb", roles, permissions)
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_set_database_permissions_cache_exception():
    """Test setting database permissions cache with exception."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.set.side_effect = Exception("Cache error")
    
    roles = ["admin", "user"]
    permissions = ["SELECT", "INSERT", "UPDATE"]
    
    # 2. Act
    result = cache_manager.set_database_permissions_cache(1, "testuser", "testdb", roles, permissions)
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_get_instance_accounts_cache_success():
    """Test getting instance accounts cache successfully."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    cached_data = {
        "accounts": [
            {"username": "user1", "host": "localhost"},
            {"username": "user2", "host": "localhost"}
        ]
    }
    mock_cache.get.return_value = cached_data
    
    # 2. Act
    result = cache_manager.get_instance_accounts_cache(1, "testuser")
    
    # 3. Assert
    assert result is not None
    assert len(result) == 2
    assert result[0]["username"] == "user1"


@pytest.mark.unit
def test_get_instance_accounts_cache_miss():
    """Test getting instance accounts cache miss."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.get.return_value = None
    
    # 2. Act
    result = cache_manager.get_instance_accounts_cache(1, "testuser")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_set_instance_accounts_cache_success():
    """Test setting instance accounts cache successfully."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    accounts = [
        {"username": "user1", "host": "localhost"},
        {"username": "user2", "host": "localhost"}
    ]
    
    # 2. Act
    result = cache_manager.set_instance_accounts_cache(1, "testuser", accounts)
    
    # 3. Assert
    assert result is True
    mock_cache.set.assert_called_once()


@pytest.mark.unit
def test_clear_cache_success():
    """Test clearing cache successfully."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    # 2. Act
    result = cache_manager.clear_cache()
    
    # 3. Assert
    assert result is True
    mock_cache.clear.assert_called_once()


@pytest.mark.unit
def test_clear_cache_no_cache():
    """Test clearing cache when no cache instance."""
    # 1. Arrange
    cache_manager = CacheManager(cache=None)
    
    # 2. Act
    result = cache_manager.clear_cache()
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_clear_cache_exception():
    """Test clearing cache with exception."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.clear.side_effect = Exception("Cache clear error")
    
    # 2. Act
    result = cache_manager.clear_cache()
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_clear_instance_cache_success():
    """Test clearing instance cache successfully."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    # 2. Act
    result = cache_manager.clear_instance_cache(1, "testuser")
    
    # 3. Assert
    assert result is True
    # Should call delete for both permissions and accounts cache
    assert mock_cache.delete.call_count == 2


@pytest.mark.unit
def test_clear_instance_cache_no_cache():
    """Test clearing instance cache when no cache instance."""
    # 1. Arrange
    cache_manager = CacheManager(cache=None)
    
    # 2. Act
    result = cache_manager.clear_instance_cache(1, "testuser")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_clear_instance_cache_exception():
    """Test clearing instance cache with exception."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.delete.side_effect = Exception("Cache delete error")
    
    # 2. Act
    result = cache_manager.clear_instance_cache(1, "testuser")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_get_cache_stats_success():
    """Test getting cache stats successfully."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.get_stats.return_value = {
        "hits": 100,
        "misses": 50,
        "total": 150
    }
    
    # 2. Act
    result = cache_manager.get_cache_stats()
    
    # 3. Assert
    assert result is not None
    assert result["hits"] == 100
    assert result["misses"] == 50
    assert result["total"] == 150


@pytest.mark.unit
def test_get_cache_stats_no_cache():
    """Test getting cache stats when no cache instance."""
    # 1. Arrange
    cache_manager = CacheManager(cache=None)
    
    # 2. Act
    result = cache_manager.get_cache_stats()
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_get_cache_stats_exception():
    """Test getting cache stats with exception."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    mock_cache.get_stats.side_effect = Exception("Stats error")
    
    # 2. Act
    result = cache_manager.get_cache_stats()
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_cache_key_generation_different_prefixes():
    """Test cache key generation with different prefixes."""
    cache_manager = CacheManager()
    
    # Test different prefixes generate different keys
    key1 = cache_manager._generate_cache_key("db_perms", 1, "testuser", "testdb")
    key2 = cache_manager._generate_cache_key("instance_accounts", 1, "testuser", "testdb")
    
    assert key1 != key2
    assert key1.startswith("whalefall:")
    assert key2.startswith("whalefall:")


@pytest.mark.unit
def test_cache_key_generation_special_characters():
    """Test cache key generation with special characters in username."""
    cache_manager = CacheManager()
    
    # Test with special characters in username
    key1 = cache_manager._generate_cache_key("db_perms", 1, "test@user", "testdb")
    key2 = cache_manager._generate_cache_key("db_perms", 1, "test.user", "testdb")
    
    assert key1 != key2
    assert key1.startswith("whalefall:")
    assert key2.startswith("whalefall:")


@pytest.mark.unit
def test_cache_key_generation_long_values():
    """Test cache key generation with long values."""
    cache_manager = CacheManager()
    
    # Test with very long username and database name
    long_username = "x" * 1000
    long_db_name = "y" * 1000
    
    key = cache_manager._generate_cache_key("db_perms", 1, long_username, long_db_name)
    
    assert key.startswith("whalefall:")
    assert len(key) < 100  # Should be hashed to reasonable length


@pytest.mark.unit
def test_cache_ttl_configuration():
    """Test cache TTL configuration."""
    # Test default TTL
    cache_manager = CacheManager()
    assert cache_manager.default_ttl == 7 * 24 * 3600  # 7 days
    
    # Test custom TTL
    custom_ttl = 3600  # 1 hour
    cache_manager = CacheManager()
    cache_manager.default_ttl = custom_ttl
    assert cache_manager.default_ttl == custom_ttl


@pytest.mark.unit
def test_cache_operations_with_empty_data():
    """Test cache operations with empty data."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    # Test setting empty data
    result = cache_manager.set_database_permissions_cache(1, "testuser", "testdb", [], [])
    assert result is True
    
    # Test getting empty data
    mock_cache.get.return_value = {"roles": [], "permissions": []}
    result = cache_manager.get_database_permissions_cache(1, "testuser", "testdb")
    assert result is not None
    roles, permissions = result
    assert roles == []
    assert permissions == []


@pytest.mark.unit
def test_cache_operations_with_none_data():
    """Test cache operations with None data."""
    # 1. Arrange
    mock_cache = Mock()
    cache_manager = CacheManager(cache=mock_cache)
    
    # Test setting None data
    result = cache_manager.set_database_permissions_cache(1, "testuser", "testdb", None, None)
    assert result is True
    
    # Test getting None data
    mock_cache.get.return_value = {"roles": None, "permissions": None}
    result = cache_manager.get_database_permissions_cache(1, "testuser", "testdb")
    assert result is not None
    roles, permissions = result
    assert roles is None
    assert permissions is None
