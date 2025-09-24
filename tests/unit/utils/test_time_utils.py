"""
TimeUtils工具类单元测试
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.utils.time_utils import TimeUtils, CHINA_TZ, UTC_TZ, TIME_FORMATS


@pytest.mark.unit
def test_time_utils_init():
    """Test TimeUtils initialization."""
    # TimeUtils is a static class, so we just test that it can be imported
    assert TimeUtils is not None


@pytest.mark.unit
def test_now():
    """Test getting current UTC time."""
    now = TimeUtils.now()
    assert now is not None
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc


@pytest.mark.unit
def test_now_china():
    """Test getting current China time."""
    now = TimeUtils.now_china()
    assert now is not None
    assert isinstance(now, datetime)
    assert now.tzinfo == CHINA_TZ


@pytest.mark.unit
def test_to_china_with_datetime():
    """Test converting datetime to China timezone."""
    # Test with UTC datetime
    utc_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    china_time = TimeUtils.to_china(utc_time)
    
    assert china_time is not None
    assert china_time.tzinfo == CHINA_TZ
    # China is UTC+8, so 12:00 UTC should be 20:00 China time
    assert china_time.hour == 20


@pytest.mark.unit
def test_to_china_with_naive_datetime():
    """Test converting naive datetime to China timezone."""
    naive_time = datetime(2024, 1, 1, 12, 0, 0)
    china_time = TimeUtils.to_china(naive_time)
    
    assert china_time is not None
    assert china_time.tzinfo == CHINA_TZ
    assert china_time.hour == 12  # Naive time is treated as local time


@pytest.mark.unit
def test_to_china_with_string():
    """Test converting string to China timezone."""
    # Test with ISO format string
    iso_string = "2024-01-01T12:00:00Z"
    china_time = TimeUtils.to_china(iso_string)
    
    assert china_time is not None
    assert china_time.tzinfo == CHINA_TZ
    assert china_time.hour == 20  # UTC+8


@pytest.mark.unit
def test_to_china_with_none():
    """Test converting None to China timezone."""
    result = TimeUtils.to_china(None)
    assert result is None


@pytest.mark.unit
def test_to_china_with_empty_string():
    """Test converting empty string to China timezone."""
    result = TimeUtils.to_china("")
    assert result is None


@pytest.mark.unit
def test_to_china_with_invalid_string():
    """Test converting invalid string to China timezone."""
    with pytest.raises(ValueError):
        TimeUtils.to_china("invalid-date-string")


@pytest.mark.unit
def test_format_time():
    """Test formatting time."""
    dt = datetime(2024, 1, 1, 12, 30, 45, tzinfo=CHINA_TZ)
    
    # Test with custom format
    formatted = TimeUtils.format_time(dt, "%Y-%m-%d %H:%M:%S")
    assert formatted == "2024-01-01 12:30:45"
    
    # Test with predefined format
    formatted = TimeUtils.format_time(dt, "datetime")
    assert formatted == "2024-01-01 12:30:45"


@pytest.mark.unit
def test_format_time_with_string():
    """Test formatting time with string input."""
    dt_string = "2024-01-01 12:30:45"
    formatted = TimeUtils.format_time(dt_string, "%Y-%m-%d %H:%M:%S")
    assert formatted == "2024-01-01 12:30:45"


@pytest.mark.unit
def test_format_time_with_none():
    """Test formatting time with None input."""
    result = TimeUtils.format_time(None, "%Y-%m-%d %H:%M:%S")
    assert result is None


@pytest.mark.unit
def test_format_time_with_invalid_string():
    """Test formatting time with invalid string."""
    with pytest.raises(ValueError):
        TimeUtils.format_time("invalid-date", "%Y-%m-%d %H:%M:%S")


@pytest.mark.unit
def test_parse_time():
    """Test parsing time string."""
    # Test with valid datetime string
    dt_string = "2024-01-01 12:30:45"
    parsed = TimeUtils.parse_time(dt_string, "%Y-%m-%d %H:%M:%S")
    
    assert parsed is not None
    assert isinstance(parsed, datetime)
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 1
    assert parsed.hour == 12
    assert parsed.minute == 30
    assert parsed.second == 45


@pytest.mark.unit
def test_parse_time_with_timezone():
    """Test parsing time string with timezone."""
    dt_string = "2024-01-01T12:30:45+08:00"
    parsed = TimeUtils.parse_time(dt_string, "%Y-%m-%dT%H:%M:%S%z")
    
    assert parsed is not None
    assert parsed.tzinfo is not None


@pytest.mark.unit
def test_parse_time_with_invalid_string():
    """Test parsing invalid time string."""
    with pytest.raises(ValueError):
        TimeUtils.parse_time("invalid-date", "%Y-%m-%d %H:%M:%S")


@pytest.mark.unit
def test_parse_time_with_none():
    """Test parsing None."""
    result = TimeUtils.parse_time(None, "%Y-%m-%d %H:%M:%S")
    assert result is None


@pytest.mark.unit
def test_get_relative_time():
    """Test getting relative time."""
    # Test with recent time
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    relative = TimeUtils.get_relative_time(recent_time)
    
    assert relative is not None
    assert isinstance(relative, str)
    assert "分钟前" in relative or "刚刚" in relative
    
    # Test with older time
    old_time = datetime.now(timezone.utc) - timedelta(days=2)
    relative = TimeUtils.get_relative_time(old_time)
    
    assert relative is not None
    assert isinstance(relative, str)
    assert "天前" in relative


@pytest.mark.unit
def test_get_relative_time_with_none():
    """Test getting relative time with None."""
    result = TimeUtils.get_relative_time(None)
    assert result is None


@pytest.mark.unit
def test_is_today():
    """Test checking if datetime is today."""
    # Test with today's date
    today = datetime.now(timezone.utc)
    assert TimeUtils.is_today(today) is True
    
    # Test with yesterday's date
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    assert TimeUtils.is_today(yesterday) is False
    
    # Test with tomorrow's date
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    assert TimeUtils.is_today(tomorrow) is False


@pytest.mark.unit
def test_is_today_with_string():
    """Test checking if string date is today."""
    # Test with today's date string
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert TimeUtils.is_today(today_str) is True
    
    # Test with yesterday's date string
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    assert TimeUtils.is_today(yesterday_str) is False


@pytest.mark.unit
def test_is_today_with_none():
    """Test checking if None is today."""
    result = TimeUtils.is_today(None)
    assert result is False


@pytest.mark.unit
def test_is_today_with_invalid_string():
    """Test checking if invalid string is today."""
    result = TimeUtils.is_today("invalid-date")
    assert result is False


@pytest.mark.unit
def test_get_time_range():
    """Test getting time range."""
    # Test with hours parameter
    start, end = TimeUtils.get_time_range(24)
    
    assert start is not None
    assert end is not None
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert start < end
    
    # Test with different hours
    start, end = TimeUtils.get_time_range(12)
    assert start < end


@pytest.mark.unit
def test_get_time_range_with_zero_hours():
    """Test getting time range with zero hours."""
    start, end = TimeUtils.get_time_range(0)
    
    assert start is not None
    assert end is not None
    assert start < end


@pytest.mark.unit
def test_get_time_range_with_negative_hours():
    """Test getting time range with negative hours."""
    start, end = TimeUtils.get_time_range(-1)
    
    assert start is not None
    assert end is not None
    assert start < end


@pytest.mark.unit
def test_format_duration():
    """Test formatting duration."""
    # Test with seconds
    duration = timedelta(seconds=65)
    formatted = TimeUtils.format_duration(duration)
    
    assert formatted is not None
    assert isinstance(formatted, str)
    assert "1分5秒" in formatted or "1分钟5秒" in formatted
    
    # Test with hours
    duration = timedelta(hours=2, minutes=30, seconds=45)
    formatted = TimeUtils.format_duration(duration)
    
    assert formatted is not None
    assert isinstance(formatted, str)
    assert "2小时" in formatted or "2时" in formatted


@pytest.mark.unit
def test_format_duration_zero():
    """Test formatting zero duration."""
    duration = timedelta(seconds=0)
    formatted = TimeUtils.format_duration(duration)
    
    assert formatted is not None
    assert isinstance(formatted, str)
    assert "0秒" in formatted or "0" in formatted


@pytest.mark.unit
def test_format_duration_with_none():
    """Test formatting None duration."""
    result = TimeUtils.format_duration(None)
    assert result is None


@pytest.mark.unit
def test_get_week_start_end():
    """Test getting week start and end."""
    # Test with specific date (Monday)
    test_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    start, end = TimeUtils.get_week_start_end(test_date)
    
    assert start is not None
    assert end is not None
    assert start < end
    assert start.weekday() == 0  # Monday
    assert end.weekday() == 6    # Sunday


@pytest.mark.unit
def test_get_week_start_end_with_none():
    """Test getting week start and end with None."""
    start, end = TimeUtils.get_week_start_end(None)
    
    assert start is not None
    assert end is not None
    assert start < end


@pytest.mark.unit
def test_get_month_start_end():
    """Test getting month start and end."""
    # Test with specific date
    test_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    start, end = TimeUtils.get_month_start_end(test_date)
    
    assert start is not None
    assert end is not None
    assert start < end
    assert start.day == 1
    assert end.day == 31  # January has 31 days


@pytest.mark.unit
def test_get_month_start_end_with_none():
    """Test getting month start and end with None."""
    start, end = TimeUtils.get_month_start_end(None)
    
    assert start is not None
    assert end is not None
    assert start < end


@pytest.mark.unit
def test_is_weekend():
    """Test checking if date is weekend."""
    # Test with Monday (not weekend)
    monday = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)  # Monday
    assert TimeUtils.is_weekend(monday) is False
    
    # Test with Saturday (weekend)
    saturday = datetime(2024, 1, 13, 12, 0, 0, tzinfo=timezone.utc)  # Saturday
    assert TimeUtils.is_weekend(saturday) is True
    
    # Test with Sunday (weekend)
    sunday = datetime(2024, 1, 14, 12, 0, 0, tzinfo=timezone.utc)  # Sunday
    assert TimeUtils.is_weekend(sunday) is True


@pytest.mark.unit
def test_is_weekend_with_none():
    """Test checking if None is weekend."""
    result = TimeUtils.is_weekend(None)
    assert result is False


@pytest.mark.unit
def test_get_age():
    """Test getting age from birth date."""
    # Test with birth date 25 years ago
    birth_date = datetime.now(timezone.utc) - timedelta(days=25*365)
    age = TimeUtils.get_age(birth_date)
    
    assert age is not None
    assert isinstance(age, int)
    assert age >= 24  # Should be around 25, allowing for leap years


@pytest.mark.unit
def test_get_age_future_birth():
    """Test getting age with future birth date."""
    # Test with future birth date
    future_birth = datetime.now(timezone.utc) + timedelta(days=365)
    age = TimeUtils.get_age(future_birth)
    
    assert age is None or age < 0


@pytest.mark.unit
def test_get_age_with_none():
    """Test getting age with None."""
    age = TimeUtils.get_age(None)
    assert age is None


@pytest.mark.unit
def test_time_formats_constants():
    """Test TIME_FORMATS constants."""
    assert TIME_FORMATS["datetime"] == "%Y-%m-%d %H:%M:%S"
    assert TIME_FORMATS["date"] == "%Y-%m-%d"
    assert TIME_FORMATS["time"] == "%H:%M:%S"
    assert TIME_FORMATS["display"] == "%Y年%m月%d日 %H:%M:%S"


@pytest.mark.unit
def test_timezone_constants():
    """Test timezone constants."""
    assert CHINA_TZ is not None
    assert UTC_TZ is not None
    assert str(CHINA_TZ) == "Asia/Shanghai"
    assert str(UTC_TZ) == "UTC"


@pytest.mark.unit
def test_parse_time_with_iso_format():
    """Test parsing time with ISO format."""
    iso_string = "2024-01-01T12:30:45Z"
    parsed = TimeUtils.parse_time(iso_string, "%Y-%m-%dT%H:%M:%SZ")
    
    assert parsed is not None
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 1
    assert parsed.hour == 12
    assert parsed.minute == 30
    assert parsed.second == 45


@pytest.mark.unit
def test_format_time_with_display_format():
    """Test formatting time with display format."""
    dt = datetime(2024, 1, 1, 12, 30, 45, tzinfo=CHINA_TZ)
    formatted = TimeUtils.format_time(dt, "display")
    
    assert formatted is not None
    assert "2024年01月01日" in formatted
    assert "12:30:45" in formatted


@pytest.mark.unit
def test_get_relative_time_with_future_time():
    """Test getting relative time with future time."""
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    relative = TimeUtils.get_relative_time(future_time)
    
    assert relative is not None
    assert isinstance(relative, str)
    assert "后" in relative or "未来" in relative

