"""统一时间处理工具模块.

基于Python 3.9+的zoneinfo模块,提供一致的时间处理功能.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.constants import TimeConstants

# 时区配置
CHINA_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = ZoneInfo("UTC")
DAYS_PER_WEEK = TimeConstants.ONE_WEEK // TimeConstants.ONE_DAY


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
        except (ValueError, TypeError):
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
        except (ValueError, TypeError):
            return None

    @staticmethod
    def format_china_time(
        dt: str | date | datetime | None,
        format_str: str = "%Y-%m-%d %H:%M:%S",
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
    def get_relative_time(dt: str | date | datetime | None) -> str:  # noqa: PLR0911
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


time_utils = TimeUtils()
