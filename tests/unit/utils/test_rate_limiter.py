"""
RateLimiter工具类单元测试
"""
import pytest
from unittest.mock import Mock, patch
from app.utils.rate_limiter import RateLimiter


@pytest.mark.unit
def test_rate_limiter_init():
    """Test RateLimiter initialization."""
    rate_limiter = RateLimiter()
    assert rate_limiter is not None
    assert rate_limiter.cache is None
    assert rate_limiter.memory_store == {}


@pytest.mark.unit
def test_rate_limiter_init_with_cache():
    """Test RateLimiter initialization with cache."""
    mock_cache = Mock()
    rate_limiter = RateLimiter(cache=mock_cache)
    assert rate_limiter.cache == mock_cache


@pytest.mark.unit
def test_get_key():
    """Test key generation."""
    rate_limiter = RateLimiter()
    
    key = rate_limiter._get_key("192.168.1.1", "login")
    assert key == "rate_limit:login:192.168.1.1"


@pytest.mark.unit
def test_get_memory_key():
    """Test memory key generation."""
    rate_limiter = RateLimiter()
    
    key = rate_limiter._get_memory_key("192.168.1.1", "login")
    assert key == "login:192.168.1.1"


@pytest.mark.unit
def test_is_allowed_with_cache_success():
    """Test is_allowed with cache success."""
    # 1. Arrange
    mock_cache = Mock()
    rate_limiter = RateLimiter(cache=mock_cache)
    
    # Mock cache data
    mock_cache.get.return_value = {
        "count": 5,
        "window_start": 1000
    }
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 5
    assert result["reset_time"] is not None


@pytest.mark.unit
def test_is_allowed_with_cache_limit_exceeded():
    """Test is_allowed with cache limit exceeded."""
    # 1. Arrange
    mock_cache = Mock()
    rate_limiter = RateLimiter(cache=mock_cache)
    
    # Mock cache data with limit exceeded
    mock_cache.get.return_value = {
        "count": 15,
        "window_start": 1000
    }
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is False
    assert result["remaining"] == 0


@pytest.mark.unit
def test_is_allowed_with_cache_exception():
    """Test is_allowed with cache exception."""
    # 1. Arrange
    mock_cache = Mock()
    rate_limiter = RateLimiter(cache=mock_cache)
    
    # Mock cache exception
    mock_cache.get.side_effect = Exception("Cache error")
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True  # Fallback to memory store


@pytest.mark.unit
def test_is_allowed_without_cache():
    """Test is_allowed without cache."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_memory_store_limit_exceeded():
    """Test is_allowed with memory store limit exceeded."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # Add existing requests to memory store
    key = rate_limiter._get_memory_key("192.168.1.1", "login")
    rate_limiter.memory_store[key] = {
        "count": 15,
        "window_start": 1000
    }
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is False
    assert result["remaining"] == 0


@pytest.mark.unit
def test_is_allowed_memory_store_new_window():
    """Test is_allowed with memory store new window."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # Add old window data to memory store
    key = rate_limiter._get_memory_key("192.168.1.1", "login")
    rate_limiter.memory_store[key] = {
        "count": 15,
        "window_start": 1000  # Very old window
    }
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_different_identifiers():
    """Test is_allowed with different identifiers."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result1 = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    result2 = rate_limiter.is_allowed("192.168.1.2", "login", 10, 60)
    
    # 3. Assert
    assert result1["allowed"] is True
    assert result2["allowed"] is True
    assert result1["remaining"] == 9
    assert result2["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_different_endpoints():
    """Test is_allowed with different endpoints."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result1 = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    result2 = rate_limiter.is_allowed("192.168.1.1", "register", 10, 60)
    
    # 3. Assert
    assert result1["allowed"] is True
    assert result2["allowed"] is True
    assert result1["remaining"] == 9
    assert result2["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_multiple_requests():
    """Test is_allowed with multiple requests."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result1 = rate_limiter.is_allowed("192.168.1.1", "login", 3, 60)
    result2 = rate_limiter.is_allowed("192.168.1.1", "login", 3, 60)
    result3 = rate_limiter.is_allowed("192.168.1.1", "login", 3, 60)
    result4 = rate_limiter.is_allowed("192.168.1.1", "login", 3, 60)
    
    # 3. Assert
    assert result1["allowed"] is True
    assert result2["allowed"] is True
    assert result3["allowed"] is True
    assert result4["allowed"] is False  # Limit exceeded


@pytest.mark.unit
def test_is_allowed_different_limits():
    """Test is_allowed with different limits."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result1 = rate_limiter.is_allowed("192.168.1.1", "login", 5, 60)
    result2 = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result1["allowed"] is True
    assert result2["allowed"] is True
    assert result1["remaining"] == 4
    assert result2["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_different_windows():
    """Test is_allowed with different windows."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result1 = rate_limiter.is_allowed("192.168.1.1", "login", 10, 30)
    result2 = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result1["allowed"] is True
    assert result2["allowed"] is True
    assert result1["remaining"] == 9
    assert result2["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_empty_identifier():
    """Test is_allowed with empty identifier."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_none_identifier():
    """Test is_allowed with None identifier."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed(None, "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_empty_endpoint():
    """Test is_allowed with empty endpoint."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_none_endpoint():
    """Test is_allowed with None endpoint."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", None, 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_zero_limit():
    """Test is_allowed with zero limit."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 0, 60)
    
    # 3. Assert
    assert result["allowed"] is False
    assert result["remaining"] == 0


@pytest.mark.unit
def test_is_allowed_negative_limit():
    """Test is_allowed with negative limit."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", -1, 60)
    
    # 3. Assert
    assert result["allowed"] is False
    assert result["remaining"] == 0


@pytest.mark.unit
def test_is_allowed_zero_window():
    """Test is_allowed with zero window."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 0)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_negative_window():
    """Test is_allowed with negative window."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, -1)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_large_limit():
    """Test is_allowed with large limit."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 1000000, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 999999


@pytest.mark.unit
def test_is_allowed_large_window():
    """Test is_allowed with large window."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 86400)  # 24 hours
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9


@pytest.mark.unit
def test_is_allowed_memory_store_cleanup():
    """Test is_allowed memory store cleanup."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # Add old data to memory store
    key = rate_limiter._get_memory_key("192.168.1.1", "login")
    rate_limiter.memory_store[key] = {
        "count": 15,
        "window_start": 1000  # Very old window
    }
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result["allowed"] is True
    assert result["remaining"] == 9
    # Old data should be cleaned up
    assert key in rate_limiter.memory_store  # New data should be added


@pytest.mark.unit
def test_is_allowed_memory_store_multiple_keys():
    """Test is_allowed memory store with multiple keys."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    rate_limiter.is_allowed("192.168.1.2", "login", 10, 60)
    rate_limiter.is_allowed("192.168.1.1", "register", 10, 60)
    
    # 3. Assert
    assert len(rate_limiter.memory_store) == 3
    assert "login:192.168.1.1" in rate_limiter.memory_store
    assert "login:192.168.1.2" in rate_limiter.memory_store
    assert "register:192.168.1.1" in rate_limiter.memory_store


@pytest.mark.unit
def test_is_allowed_memory_store_data_structure():
    """Test is_allowed memory store data structure."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    result = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    key = rate_limiter._get_memory_key("192.168.1.1", "login")
    assert key in rate_limiter.memory_store
    
    data = rate_limiter.memory_store[key]
    assert "count" in data
    assert "window_start" in data
    assert data["count"] == 1
    assert isinstance(data["window_start"], int)


@pytest.mark.unit
def test_is_allowed_memory_store_window_rollover():
    """Test is_allowed memory store window rollover."""
    # 1. Arrange
    rate_limiter = RateLimiter()
    
    # 2. Act
    # First request
    result1 = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # Simulate time passing by modifying window_start
    key = rate_limiter._get_memory_key("192.168.1.1", "login")
    rate_limiter.memory_store[key]["window_start"] = 1000  # Very old window
    
    # Second request (should start new window)
    result2 = rate_limiter.is_allowed("192.168.1.1", "login", 10, 60)
    
    # 3. Assert
    assert result1["allowed"] is True
    assert result2["allowed"] is True
    assert result1["remaining"] == 9
    assert result2["remaining"] == 9  # New window, so count resets
