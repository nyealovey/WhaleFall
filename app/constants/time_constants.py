"""时间常量.

提供常用时间单位的秒数表示,提高代码可读性.
"""


class TimeConstants:
    """时间常量(秒数).

    提供常用时间单位的秒数表示,避免在代码中使用魔法数字.
    """

    ONE_MINUTE = 60
    FIVE_MINUTES = 300
    TEN_MINUTES = 600
    FIFTEEN_MINUTES = 900
    THIRTY_MINUTES = 1800

    # 小时
    ONE_HOUR = 3600
    TWO_HOURS = 7200
    THREE_HOURS = 10800
    SIX_HOURS = 21600
    TWELVE_HOURS = 43200

    # 天
    ONE_DAY = 86400
    TWO_DAYS = 172800
    THREE_DAYS = 259200
    ONE_WEEK = 604800

    ONE_MONTH = 2592000    # 30天
    THREE_MONTHS = 7776000 # 90天
    SIX_MONTHS = 15552000  # 180天
    ONE_YEAR = 31536000    # 365天

    # 辅助方法

    @classmethod
    def minutes(cls, n: int) -> int:
        """返回n分钟的秒数.

        Args:
            n: 分钟数

        Returns:
            int: 秒数

        """
        return n * cls.ONE_MINUTE

    @classmethod
    def hours(cls, n: int) -> int:
        """返回n小时的秒数.

        Args:
            n: 小时数

        Returns:
            int: 秒数

        """
        return n * cls.ONE_HOUR

    @classmethod
    def days(cls, n: int) -> int:
        """返回n天的秒数.

        Args:
            n: 天数

        Returns:
            int: 秒数

        """
        return n * cls.ONE_DAY

    @classmethod
    def to_minutes(cls, seconds: int) -> float:
        """将秒数转换为分钟.

        Args:
            seconds: 秒数

        Returns:
            float: 分钟数

        """
        return seconds / cls.ONE_MINUTE

    @classmethod
    def to_hours(cls, seconds: int) -> float:
        """将秒数转换为小时.

        Args:
            seconds: 秒数

        Returns:
            float: 小时数

        """
        return seconds / cls.ONE_HOUR

    @classmethod
    def to_days(cls, seconds: int) -> float:
        """将秒数转换为天数.

        Args:
            seconds: 秒数

        Returns:
            float: 天数

        """
        return seconds / cls.ONE_DAY
