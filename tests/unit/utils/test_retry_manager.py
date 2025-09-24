"""
RetryManager工具类单元测试
"""
import pytest
from unittest.mock import Mock, patch
from app.utils.retry_manager import RetryManager, RetryStrategy


@pytest.mark.unit
def test_retry_manager_init():
    """Test RetryManager initialization."""
    retry_manager = RetryManager()
    assert retry_manager.max_attempts == 3
    assert retry_manager.base_delay == 1.0
    assert retry_manager.max_delay == 60.0
    assert retry_manager.strategy == RetryStrategy.EXPONENTIAL
    assert retry_manager.system_logger is not None


@pytest.mark.unit
def test_retry_manager_init_custom_params():
    """Test RetryManager initialization with custom parameters."""
    retry_manager = RetryManager(
        max_attempts=5,
        base_delay=2.0,
        max_delay=120.0,
        strategy=RetryStrategy.FIXED
    )
    assert retry_manager.max_attempts == 5
    assert retry_manager.base_delay == 2.0
    assert retry_manager.max_delay == 120.0
    assert retry_manager.strategy == RetryStrategy.FIXED


@pytest.mark.unit
def test_calculate_delay_fixed_strategy():
    """Test calculate_delay with fixed strategy."""
    retry_manager = RetryManager(
        base_delay=2.0,
        strategy=RetryStrategy.FIXED
    )
    
    # Test multiple attempts
    for attempt in range(1, 6):
        delay = retry_manager.calculate_delay(attempt)
        assert delay == 2.0


@pytest.mark.unit
def test_calculate_delay_linear_strategy():
    """Test calculate_delay with linear strategy."""
    retry_manager = RetryManager(
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.LINEAR
    )
    
    # Test linear growth
    assert retry_manager.calculate_delay(1) == 1.0
    assert retry_manager.calculate_delay(2) == 2.0
    assert retry_manager.calculate_delay(3) == 3.0
    assert retry_manager.calculate_delay(4) == 4.0
    assert retry_manager.calculate_delay(5) == 5.0
    assert retry_manager.calculate_delay(10) == 10.0
    assert retry_manager.calculate_delay(15) == 10.0  # Max delay


@pytest.mark.unit
def test_calculate_delay_exponential_strategy():
    """Test calculate_delay with exponential strategy."""
    retry_manager = RetryManager(
        base_delay=1.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL
    )
    
    # Test exponential growth
    assert retry_manager.calculate_delay(1) == 1.0
    assert retry_manager.calculate_delay(2) == 2.0
    assert retry_manager.calculate_delay(3) == 4.0
    assert retry_manager.calculate_delay(4) == 8.0
    assert retry_manager.calculate_delay(5) == 16.0
    assert retry_manager.calculate_delay(6) == 32.0
    assert retry_manager.calculate_delay(7) == 60.0  # Max delay


@pytest.mark.unit
def test_calculate_delay_max_delay_limit():
    """Test calculate_delay with max delay limit."""
    retry_manager = RetryManager(
        base_delay=10.0,
        max_delay=5.0,
        strategy=RetryStrategy.LINEAR
    )
    
    # All delays should be capped at max_delay
    for attempt in range(1, 10):
        delay = retry_manager.calculate_delay(attempt)
        assert delay <= 5.0


@pytest.mark.unit
def test_calculate_delay_zero_attempt():
    """Test calculate_delay with zero attempt."""
    retry_manager = RetryManager(strategy=RetryStrategy.LINEAR)
    
    # Zero attempt should return base_delay
    delay = retry_manager.calculate_delay(0)
    assert delay == 1.0


@pytest.mark.unit
def test_calculate_delay_negative_attempt():
    """Test calculate_delay with negative attempt."""
    retry_manager = RetryManager(strategy=RetryStrategy.LINEAR)
    
    # Negative attempt should return base_delay
    delay = retry_manager.calculate_delay(-1)
    assert delay == 1.0


@pytest.mark.unit
def test_retry_decorator_success():
    """Test retry decorator with successful function."""
    retry_manager = RetryManager(max_attempts=3)
    
    @retry_manager.retry
    def test_function():
        return "success"
    
    result = test_function()
    assert result == "success"


@pytest.mark.unit
def test_retry_decorator_failure_then_success():
    """Test retry decorator with failure then success."""
    retry_manager = RetryManager(max_attempts=3)
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    result = test_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
def test_retry_decorator_max_attempts_exceeded():
    """Test retry decorator with max attempts exceeded."""
    retry_manager = RetryManager(max_attempts=3)
    
    @retry_manager.retry
    def test_function():
        raise Exception("Permanent failure")
    
    with pytest.raises(Exception, match="Permanent failure"):
        test_function()


@pytest.mark.unit
def test_retry_decorator_with_specific_exception():
    """Test retry decorator with specific exception."""
    retry_manager = RetryManager(max_attempts=3)
    
    call_count = 0
    
    @retry_manager.retry(exceptions=(ValueError,))
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Value error")
        return "success"
    
    result = test_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
def test_retry_decorator_with_wrong_exception():
    """Test retry decorator with wrong exception type."""
    retry_manager = RetryManager(max_attempts=3)
    
    @retry_manager.retry(exceptions=(ValueError,))
    def test_function():
        raise TypeError("Type error")
    
    with pytest.raises(TypeError, match="Type error"):
        test_function()


@pytest.mark.unit
def test_retry_decorator_with_multiple_exceptions():
    """Test retry decorator with multiple exceptions."""
    retry_manager = RetryManager(max_attempts=3)
    
    call_count = 0
    
    @retry_manager.retry(exceptions=(ValueError, TypeError))
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            if call_count == 1:
                raise ValueError("Value error")
            else:
                raise TypeError("Type error")
        return "success"
    
    result = test_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
def test_retry_decorator_with_custom_delay():
    """Test retry decorator with custom delay."""
    retry_manager = RetryManager(
        base_delay=0.1,
        max_delay=1.0,
        strategy=RetryStrategy.FIXED
    )
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    result = test_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
def test_retry_decorator_with_function_args():
    """Test retry decorator with function arguments."""
    retry_manager = RetryManager(max_attempts=3)
    
    call_count = 0
    
    @retry_manager.retry
    def test_function(arg1, arg2, kwarg1=None):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return f"{arg1}_{arg2}_{kwarg1}"
    
    result = test_function("test", "value", kwarg1="keyword")
    assert result == "test_value_keyword"
    assert call_count == 3


@pytest.mark.unit
def test_retry_decorator_with_return_value():
    """Test retry decorator with return value."""
    retry_manager = RetryManager(max_attempts=3)
    
    @retry_manager.retry
    def test_function():
        return {"status": "success", "data": [1, 2, 3]}
    
    result = test_function()
    assert result == {"status": "success", "data": [1, 2, 3]}


@pytest.mark.unit
def test_retry_decorator_with_none_return():
    """Test retry decorator with None return."""
    retry_manager = RetryManager(max_attempts=3)
    
    @retry_manager.retry
    def test_function():
        return None
    
    result = test_function()
    assert result is None


@pytest.mark.unit
def test_retry_decorator_with_exception_in_final_attempt():
    """Test retry decorator with exception in final attempt."""
    retry_manager = RetryManager(max_attempts=3)
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        raise Exception(f"Failure {call_count}")
    
    with pytest.raises(Exception, match="Failure 3"):
        test_function()
    
    assert call_count == 3


@pytest.mark.unit
def test_retry_decorator_with_zero_max_attempts():
    """Test retry decorator with zero max attempts."""
    retry_manager = RetryManager(max_attempts=0)
    
    @retry_manager.retry
    def test_function():
        raise Exception("Should not retry")
    
    with pytest.raises(Exception, match="Should not retry"):
        test_function()


@pytest.mark.unit
def test_retry_decorator_with_negative_max_attempts():
    """Test retry decorator with negative max attempts."""
    retry_manager = RetryManager(max_attempts=-1)
    
    @retry_manager.retry
    def test_function():
        raise Exception("Should not retry")
    
    with pytest.raises(Exception, match="Should not retry"):
        test_function()


@pytest.mark.unit
def test_retry_decorator_with_large_max_attempts():
    """Test retry decorator with large max attempts."""
    retry_manager = RetryManager(max_attempts=100)
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 50:
            raise Exception("Temporary failure")
        return "success"
    
    result = test_function()
    assert result == "success"
    assert call_count == 50


@pytest.mark.unit
def test_retry_decorator_with_custom_logger():
    """Test retry decorator with custom logger."""
    mock_logger = Mock()
    retry_manager = RetryManager(max_attempts=3)
    retry_manager.system_logger = mock_logger
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    result = test_function()
    assert result == "success"
    assert call_count == 3
    # Verify logging was called
    assert mock_logger.warning.call_count == 2  # Two retries


@pytest.mark.unit
def test_retry_decorator_with_delay_calculation():
    """Test retry decorator with delay calculation."""
    retry_manager = RetryManager(
        base_delay=0.1,
        max_delay=1.0,
        strategy=RetryStrategy.EXPONENTIAL
    )
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    with patch('time.sleep') as mock_sleep:
        result = test_function()
        assert result == "success"
        assert call_count == 3
        # Verify sleep was called with calculated delays
        assert mock_sleep.call_count == 2  # Two retries
        # First retry: 0.1 * 2^0 = 0.1
        # Second retry: 0.1 * 2^1 = 0.2
        expected_delays = [0.1, 0.2]
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


@pytest.mark.unit
def test_retry_decorator_with_exponential_backoff():
    """Test retry decorator with exponential backoff."""
    retry_manager = RetryManager(
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL
    )
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 5:
            raise Exception("Temporary failure")
        return "success"
    
    with patch('time.sleep') as mock_sleep:
        result = test_function()
        assert result == "success"
        assert call_count == 5
        # Verify exponential backoff delays
        expected_delays = [1.0, 2.0, 4.0, 8.0]  # 1, 2, 4, 8
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


@pytest.mark.unit
def test_retry_decorator_with_linear_backoff():
    """Test retry decorator with linear backoff."""
    retry_manager = RetryManager(
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.LINEAR
    )
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 5:
            raise Exception("Temporary failure")
        return "success"
    
    with patch('time.sleep') as mock_sleep:
        result = test_function()
        assert result == "success"
        assert call_count == 5
        # Verify linear backoff delays
        expected_delays = [1.0, 2.0, 3.0, 4.0]  # 1, 2, 3, 4
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


@pytest.mark.unit
def test_retry_decorator_with_fixed_delay():
    """Test retry decorator with fixed delay."""
    retry_manager = RetryManager(
        base_delay=2.0,
        strategy=RetryStrategy.FIXED
    )
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    with patch('time.sleep') as mock_sleep:
        result = test_function()
        assert result == "success"
        assert call_count == 3
        # Verify fixed delays
        expected_delays = [2.0, 2.0]  # Fixed delay
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


@pytest.mark.unit
def test_retry_decorator_with_max_delay_limit():
    """Test retry decorator with max delay limit."""
    retry_manager = RetryManager(
        base_delay=1.0,
        max_delay=3.0,
        strategy=RetryStrategy.EXPONENTIAL
    )
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 5:
            raise Exception("Temporary failure")
        return "success"
    
    with patch('time.sleep') as mock_sleep:
        result = test_function()
        assert result == "success"
        assert call_count == 5
        # Verify max delay limit
        expected_delays = [1.0, 2.0, 3.0, 3.0]  # 1, 2, 3, 3 (capped)
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


@pytest.mark.unit
def test_retry_decorator_with_sleep_exception():
    """Test retry decorator with sleep exception."""
    retry_manager = RetryManager(max_attempts=3)
    
    call_count = 0
    
    @retry_manager.retry
    def test_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"
    
    with patch('time.sleep', side_effect=Exception("Sleep error")):
        # Should still work despite sleep error
        result = test_function()
        assert result == "success"
        assert call_count == 3


@pytest.mark.unit
def test_retry_decorator_with_function_metadata():
    """Test retry decorator preserves function metadata."""
    retry_manager = RetryManager(max_attempts=3)
    
    @retry_manager.retry
    def test_function(arg1, arg2, kwarg1=None):
        """Test function docstring."""
        return f"{arg1}_{arg2}_{kwarg1}"
    
    # Check metadata is preserved
    assert test_function.__name__ == "test_function"
    assert test_function.__doc__ == "Test function docstring"
    assert callable(test_function)


@pytest.mark.unit
def test_retry_strategy_enum():
    """Test RetryStrategy enum values."""
    assert RetryStrategy.FIXED.value == "fixed"
    assert RetryStrategy.EXPONENTIAL.value == "exponential"
    assert RetryStrategy.LINEAR.value == "linear"


@pytest.mark.unit
def test_retry_strategy_enum_comparison():
    """Test RetryStrategy enum comparison."""
    assert RetryStrategy.FIXED == RetryStrategy.FIXED
    assert RetryStrategy.FIXED != RetryStrategy.EXPONENTIAL
    assert RetryStrategy.LINEAR != RetryStrategy.FIXED


@pytest.mark.unit
def test_retry_manager_str_representation():
    """Test RetryManager string representation."""
    retry_manager = RetryManager(
        max_attempts=5,
        base_delay=2.0,
        max_delay=120.0,
        strategy=RetryStrategy.LINEAR
    )
    
    str_repr = str(retry_manager)
    assert "RetryManager" in str_repr
    assert "max_attempts=5" in str_repr
    assert "base_delay=2.0" in str_repr
    assert "max_delay=120.0" in str_repr
    assert "strategy=RetryStrategy.LINEAR" in str_repr
