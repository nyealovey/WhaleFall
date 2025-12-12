"""统一时间处理工具模块.

基于Python 3.9+的zoneinfo模块,提供一致的时间处理功能.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.constants import TimeConstants
from app.utils.structlog_config import get_system_logger

# 时区配置
CHINA_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = ZoneInfo("UTC")
MINUTES_PER_HOUR = TimeConstants.ONE_HOUR // TimeConstants.ONE_MINUTE
HOURS_PER_DAY = TimeConstants.ONE_DAY // TimeConstants.ONE_HOUR
DAYS_PER_WEEK = TimeConstants.ONE_WEEK // TimeConstants.ONE_DAY


# 时间格式常量类
class TimeFormats:
    """时间格式常量."""

    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    DATETIME_MS_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    CHINESE_DATETIME_FORMAT = "%Y年%m月%d日 %H:%M:%S"
    CHINESE_DATE_FORMAT = "%Y年%m月%d日"


# 向后兼容的时间格式字典
TIME_FORMATS = {
    "datetime": TimeFormats.DATETIME_FORMAT,
    "date": TimeFormats.DATE_FORMAT,
    "time": TimeFormats.TIME_FORMAT,
    "datetime_ms": TimeFormats.DATETIME_MS_FORMAT,
    "iso": TimeFormats.ISO_FORMAT,
    "display": TimeFormats.CHINESE_DATETIME_FORMAT,
}


class TimeUtils:
    """统一时间处理工具类.

    提供一致的时间处理功能,包括时区转换、时间格式化、
    相对时间计算等.基于 Python 3.9+ 的 zoneinfo 模块.
    """

    @staticmethod
    def now() -> datetime:
        """获取当前 UTC 时间.

        Returns:
            带 UTC 时区信息的当前时间.

        """
        return datetime.now(UTC)

    @staticmethod
    def now_china() -> datetime:
        """获取当前中国时间.

        Returns:
            带中国时区信息的当前时间.

        """
        return datetime.now(CHINA_TZ)

    @staticmethod
    def to_china(dt: str | date | datetime | None) -> datetime | None:
        """将时间转换为中国时区.

        Args:
            dt: 待转换的时间,可以是字符串、date 或 datetime 对象.

        Returns:
            转换后的中国时区时间,转换失败时返回 None.

        """
        if not dt:
            return None

        try:
            if isinstance(dt, str):
                # 处理ISO格式字符串
                if dt.endswith("Z"):
                    dt = dt[:-1] + "+00:00"
                dt = datetime.fromisoformat(dt)
            elif isinstance(dt, date) and not isinstance(dt, datetime):
                dt = datetime.combine(dt, datetime.min.time())

            if dt.tzinfo is None:
                # 如果没有时区信息,假设为UTC
                dt = dt.replace(tzinfo=UTC_TZ)

            return dt.astimezone(CHINA_TZ)
        except (ValueError, TypeError) as e:
            get_system_logger().warning(f"时间转换错误: {e}")
            return None

    @staticmethod
    def to_utc(dt: str | date | datetime | None) -> datetime | None:
        """将时间转换为 UTC 时区.

        Args:
            dt: 待转换的时间,可以是字符串、date 或 datetime 对象.

        Returns:
            转换后的 UTC 时区时间,转换失败时返回 None.

        """
        if not dt:
            return None

        try:
            if isinstance(dt, str):
                if dt.endswith("Z"):
                    dt = dt[:-1] + "+00:00"
                dt = datetime.fromisoformat(dt)
            elif isinstance(dt, date) and not isinstance(dt, datetime):
                dt = datetime.combine(dt, datetime.min.time())

            if dt.tzinfo is None:
                # 如果没有时区信息,假设为中国时间
                dt = dt.replace(tzinfo=CHINA_TZ)

            return dt.astimezone(UTC_TZ)
        except (ValueError, TypeError) as e:
            get_system_logger().warning(f"时间转换错误: {e}")
            return None

    @staticmethod
    def format_china_time(
        dt: str | date | datetime | None,
        format_str: str = TimeFormats.DATETIME_FORMAT,
    ) -> str:
        """格式化中国时间显示.

        Args:
            dt: 待格式化的时间.
            format_str: 时间格式字符串,默认为 '%Y-%m-%d %H:%M:%S'.

        Returns:
            格式化后的时间字符串,失败时返回 '-'.

        """
        china_dt = TimeUtils.to_china(dt)
        if not china_dt:
            return "-"

        try:
            return china_dt.strftime(format_str)
        except (ValueError, TypeError):
            return "-"

    @staticmethod
    def format_utc_time(dt: str | date | datetime | None, format_str: str = TimeFormats.DATETIME_FORMAT) -> str:
        """格式化 UTC 时间显示.

        Args:
            dt: 待格式化的日期时间对象或 ISO 字符串.
            format_str: strftime 兼容格式,默认为 `%Y-%m-%d %H:%M:%S`.

        Returns:
            成功时返回格式化后的 UTC 字符串;转换失败时返回 `-`.

        """
        utc_dt = TimeUtils.to_utc(dt)
        if not utc_dt:
            return "-"

        try:
            return utc_dt.strftime(format_str)
        except (ValueError, TypeError):
            return "-"

    @staticmethod
    def get_relative_time(dt: str | date | datetime | None) -> str:
        """获取相对时间描述.

        将时间转换为人类可读的相对时间描述,如"刚刚"、"5分钟前"、"2小时前"等.

        Args:
            dt: 待转换的时间.

        Returns:
            相对时间描述字符串,失败时返回 '-'.

        """
        china_dt = TimeUtils.to_china(dt)
        if not china_dt:
            return "-"

        try:
            now = TimeUtils.now_china()
            diff = now - china_dt

            if diff.total_seconds() < TimeConstants.ONE_MINUTE:
                return "刚刚"
            if diff.total_seconds() < TimeConstants.ONE_HOUR:
                minutes = int(diff.total_seconds() / TimeConstants.ONE_MINUTE)
                return f"{minutes}分钟前"
            if diff.total_seconds() < TimeConstants.ONE_DAY:
                hours = int(diff.total_seconds() / TimeConstants.ONE_HOUR)
                return f"{hours}小时前"
            if diff.days < DAYS_PER_WEEK:
                return f"{diff.days}天前"
            return TimeUtils.format_china_time(china_dt)
        except (ValueError, TypeError):
            return "-"

    @staticmethod
    def is_today(dt: str | date | datetime | None) -> bool:
        """判断给定时间是否属于今天(以中国时区为准).

        Args:
            dt: 日期、时间或字符串表示.

        Returns:
            True 表示在当前中国日期内;无法解析或不属于今天则为 False.

        """
        china_dt = TimeUtils.to_china(dt)
        if not china_dt:
            return False

        try:
            now = TimeUtils.now_china()
            return china_dt.date() == now.date()
        except (ValueError, TypeError):
            return False

    @staticmethod
    def get_time_range(hours: int = 24) -> dict[str, str]:
        """获取指定小时跨度的起止时间.

        Args:
            hours: 向前追溯的小时数,默认 24 小时.

        Returns:
            包含本地/UTC 起止时间的字典.

        """
        now = TimeUtils.now_china()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if hours < HOURS_PER_DAY:
            start = now.replace(hour=now.hour - hours, minute=0, second=0, microsecond=0)

        return {
            "start": start.isoformat(),
            "end": now.isoformat(),
            "start_utc": start.astimezone(UTC_TZ).isoformat(),
            "end_utc": now.astimezone(UTC_TZ).isoformat(),
        }

    @staticmethod
    def to_json_serializable(dt: str | date | datetime | None) -> str | None:
        """转换时间对象为 JSON 可序列化的 ISO 字符串.

        Args:
            dt: 字符串、date 或 datetime 实例.

        Returns:
            ISO 格式字符串;若无法转换则返回 None.

        """
        if not dt:
            return None

        try:
            if isinstance(dt, str):
                return dt
            if isinstance(dt, datetime):
                return dt.isoformat()
            if isinstance(dt, date):
                return dt.isoformat()
        except (ValueError, TypeError):
            return None
        return None


time_utils = TimeUtils()
