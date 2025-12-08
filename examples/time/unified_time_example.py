"""Unified time processing 示例脚本.

执行方式:
    $ python examples/time/unified_time_example.py

示例展示了如何在业务代码中使用统一的时间处理工具,包括:
1. 统一的时间获取和转换
2. 统一的时间格式化和显示
3. 数据库模型中的时间字段处理
4. API 响应中的时间序列化
5. 前端时间处理的最佳实践
6. 时区处理和相对时间计算
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.utils.time_utils import TimeFormats, time_utils


def demonstrate_basic_time_operations() -> None:
    """演示基础时间操作."""
    # 获取当前时间
    time_utils.now()
    time_utils.now_china()



def demonstrate_time_formatting() -> None:
    """演示时间格式化."""
    now = time_utils.now_china()

    # 使用不同格式格式化时间
    formats = {
        "标准日期时间": TimeFormats.DATETIME_FORMAT,
        "仅日期": TimeFormats.DATE_FORMAT,
        "仅时间": TimeFormats.TIME_FORMAT,
        "带毫秒": TimeFormats.DATETIME_MS_FORMAT,
        "ISO格式": TimeFormats.ISO_FORMAT,
        "中文日期时间": TimeFormats.CHINESE_DATETIME_FORMAT,
        "中文日期": TimeFormats.CHINESE_DATE_FORMAT,
    }

    for format_str in formats.values():
        time_utils.format_china_time(now, format_str)


def demonstrate_time_conversion() -> None:
    """演示时间转换."""
    # 模拟从不同来源获取的时间
    utc_time_str = "2025-01-17T10:30:00Z"
    iso_time_str = "2025-01-17T18:30:00+08:00"
    naive_time_str = "2025-01-17 18:30:00"

    time_utils.to_china(utc_time_str)

    time_utils.to_china(iso_time_str)

    time_utils.to_china(naive_time_str)


def demonstrate_relative_time() -> None:
    """演示相对时间计算."""
    now = time_utils.now_china()

    # 创建不同时间点
    time_points = [
        ("刚刚", now - timedelta(seconds=30)),
        ("5分钟前", now - timedelta(minutes=5)),
        ("2小时前", now - timedelta(hours=2)),
        ("3天前", now - timedelta(days=3)),
        ("1周前", now - timedelta(weeks=1)),
        ("1个月前", now - timedelta(days=30)),
    ]

    for _description, time_point in time_points:
        time_utils.get_relative_time(time_point)
        time_utils.format_china_time(time_point)


def demonstrate_today_check() -> None:
    """演示今天判断."""
    now = time_utils.now_china()

    # 创建不同日期
    test_dates = [
        ("今天", now),
        ("昨天", now - timedelta(days=1)),
        ("明天", now + timedelta(days=1)),
        ("一周前", now - timedelta(days=7)),
    ]

    for _description, test_date in test_dates:
        time_utils.is_today(test_date)
        time_utils.format_china_time(test_date, TimeFormats.DATE_FORMAT)


def demonstrate_time_range() -> None:
    """演示时间范围获取."""
    # 获取不同时间范围
    ranges = [
        ("最近1小时", 1),
        ("最近6小时", 6),
        ("最近24小时", 24),
        ("最近3天", 72),
        ("最近7天", 168),
    ]

    for _description, hours in ranges:
        time_utils.get_time_range(hours)


def simulate_database_model_usage() -> None:
    """模拟数据库模型中的时间字段使用."""
    # 模拟创建记录
    time_utils.now()  # UTC 时间存储到数据库

    # 模拟更新记录
    time_utils.now()

    # 模拟查询记录
    time_utils.get_time_range(24)  # 最近24小时


def simulate_api_response_serialization() -> None:
    """模拟 API 响应中的时间序列化."""
    # 模拟数据库记录
    mock_records = [
        {
            "id": 1,
            "name": "测试实例1",
            "created_at": time_utils.now() - timedelta(days=5),
            "updated_at": time_utils.now() - timedelta(hours=2),
            "last_connected": time_utils.now() - timedelta(minutes=30),
        },
        {
            "id": 2,
            "name": "测试实例2",
            "created_at": time_utils.now() - timedelta(days=10),
            "updated_at": time_utils.now() - timedelta(hours=1),
            "last_connected": None,
        },
    ]

    # 序列化为 API 响应
    def serialize_record(record: dict[str, Any]) -> dict[str, Any]:
        """序列化记录为 API 响应格式."""
        return {
            "id": record["id"],
            "name": record["name"],
            "created_at": time_utils.to_json_serializable(record["created_at"]),
            "updated_at": time_utils.to_json_serializable(record["updated_at"]),
            "last_connected": time_utils.to_json_serializable(record["last_connected"]),
            # 为前端提供格式化的时间
            "created_at_formatted": time_utils.format_china_time(record["created_at"]),
            "updated_at_formatted": time_utils.format_china_time(record["updated_at"]),
            "last_connected_relative": time_utils.get_relative_time(record["last_connected"]),
        }

    {
        "success": True,
        "data": [serialize_record(record) for record in mock_records],
        "timestamp": time_utils.to_json_serializable(time_utils.now()),
    }



def demonstrate_frontend_integration() -> None:
    """演示前端集成的最佳实践."""


    # 生成前端 JavaScript 代码示例



    # 生成模板代码示例



def demonstrate_error_handling() -> None:
    """演示时间处理中的错误处理."""
    # 测试各种无效输入
    invalid_inputs = [
        None,
        "",
        "invalid-date",
        "2025-13-45",  # 无效日期
        123456,  # 数字
        {},  # 对象
    ]

    for invalid_input in invalid_inputs:

        # 测试时间转换
        time_utils.to_china(invalid_input)

        # 测试时间格式化
        time_utils.format_china_time(invalid_input)

        # 测试相对时间
        time_utils.get_relative_time(invalid_input)



def demonstrate_performance_considerations() -> None:
    """演示性能考虑."""
    import time as time_module

    # 测试批量时间格式化性能
    test_times = [time_utils.now() - timedelta(minutes=i) for i in range(1000)]

    time_module.time()
    for test_time in test_times:
        time_utils.format_china_time(test_time)
    time_module.time()


    # 测试时区转换性能
    time_module.time()
    for test_time in test_times:
        time_utils.to_china(test_time)
    time_module.time()




def main() -> None:
    """主函数:运行所有演示."""
    # 运行所有演示
    demonstrate_basic_time_operations()
    demonstrate_time_formatting()
    demonstrate_time_conversion()
    demonstrate_relative_time()
    demonstrate_today_check()
    demonstrate_time_range()
    simulate_database_model_usage()
    simulate_api_response_serialization()
    demonstrate_frontend_integration()
    demonstrate_error_handling()
    demonstrate_performance_considerations()



if __name__ == "__main__":
    main()
