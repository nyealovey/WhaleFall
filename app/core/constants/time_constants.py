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

    ONE_MONTH = 2592000  # 30天
    THREE_MONTHS = 7776000  # 90天
    SIX_MONTHS = 15552000  # 180天
    ONE_YEAR = 31536000  # 365天
