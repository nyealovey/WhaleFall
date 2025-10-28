"""
统一时间处理工具模块
基于Python 3.9+的zoneinfo模块，提供一致的时间处理功能
"""

from datetime import UTC, date, datetime

from app.constants import TimeConstants
from zoneinfo import ZoneInfo

# 时区配置
CHINA_TZ = ZoneInfo("Asia/Shanghai")
UTC_TZ = ZoneInfo("UTC")

# 时间格式常量类
class TimeFormats:
    """时间格式常量"""
    
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
    """统一时间处理工具类"""

    @staticmethod
    def now() -> datetime:
        """获取当前UTC时间"""
        return datetime.now(UTC)

    @staticmethod
    def now_china() -> datetime:
        """获取当前中国时间"""
        return datetime.now(CHINA_TZ)

    @staticmethod
    def to_china(dt: str | date | datetime | None) -> datetime | None:
        """将时间转换为中国时区"""
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
                # 如果没有时区信息，假设为UTC
                dt = dt.replace(tzinfo=UTC_TZ)

            return dt.astimezone(CHINA_TZ)
        except (ValueError, TypeError) as e:
            from app.utils.structlog_config import get_system_logger

            get_system_logger().warning("时间转换错误: %s", e)
            return None

    @staticmethod
    def to_utc(dt: str | date | datetime | None) -> datetime | None:
        """将时间转换为UTC时区"""
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
                # 如果没有时区信息，假设为中国时间
                dt = dt.replace(tzinfo=CHINA_TZ)

            return dt.astimezone(UTC_TZ)
        except (ValueError, TypeError) as e:
            from app.utils.structlog_config import get_system_logger

            get_system_logger().warning("时间转换错误: %s", e)
            return None

    @staticmethod
    def format_china_time(
        dt: str | date | datetime | None, format_str: str = TimeFormats.DATETIME_FORMAT
    ) -> str:
        """格式化中国时间显示"""
        china_dt = TimeUtils.to_china(dt)
        if not china_dt:
            return "-"

        try:
            return china_dt.strftime(format_str)
        except (ValueError, TypeError):
            return "-"

    @staticmethod
    def format_utc_time(dt: str | date | datetime | None, format_str: str = TimeFormats.DATETIME_FORMAT) -> str:
        """格式化UTC时间显示"""
        utc_dt = TimeUtils.to_utc(dt)
        if not utc_dt:
            return "-"

        try:
            return utc_dt.strftime(format_str)
        except (ValueError, TypeError):
            return "-"

    @staticmethod
    def get_relative_time(dt: str | date | datetime | None) -> str:
        """获取相对时间描述"""
        china_dt = TimeUtils.to_china(dt)
        if not china_dt:
            return "-"

        try:
            now = TimeUtils.now_china()
            diff = now - china_dt

            if diff.total_seconds() < 60:
                return "刚刚"
            if diff.total_seconds() < TimeConstants.ONE_HOUR:
                minutes = int(diff.total_seconds() / 60)
                return f"{minutes}分钟前"
            if diff.total_seconds() < TimeConstants.ONE_DAY:
                hours = int(diff.total_seconds() / TimeConstants.ONE_HOUR)
                return f"{hours}小时前"
            if diff.days < 7:
                return f"{diff.days}天前"
            return TimeUtils.format_china_time(china_dt)
        except (ValueError, TypeError):
            return "-"

    @staticmethod
    def is_today(dt: str | date | datetime | None) -> bool:
        """判断是否为今天"""
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
        """获取时间范围"""
        now = TimeUtils.now_china()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if hours < 24:
            start = now.replace(hour=now.hour - hours, minute=0, second=0, microsecond=0)

        return {
            "start": start.isoformat(),
            "end": now.isoformat(),
            "start_utc": start.astimezone(UTC_TZ).isoformat(),
            "end_utc": now.astimezone(UTC_TZ).isoformat(),
        }

    @staticmethod
    def to_json_serializable(dt: str | date | datetime | None) -> str | None:
        """转换为JSON可序列化的ISO格式"""
        if not dt:
            return None

        try:
            if isinstance(dt, str):
                return dt
            if isinstance(dt, datetime):
                return dt.isoformat()
            if isinstance(dt, date):
                return dt.isoformat()
            return None
        except (ValueError, TypeError):
            return None


# 创建全局实例
time_utils = TimeUtils()





# 常量（向后兼容）
# UTC_TZ 已在文件顶部定义
