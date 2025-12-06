"""
Unified time processing 示例脚本。

执行方式：
    $ python examples/time/unified_time_example.py

示例展示了如何在业务代码中使用统一的时间处理工具，包括：
1. 统一的时间获取和转换
2. 统一的时间格式化和显示
3. 数据库模型中的时间字段处理
4. API 响应中的时间序列化
5. 前端时间处理的最佳实践
6. 时区处理和相对时间计算
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict

from app.utils.time_utils import TimeFormats, time_utils


def demonstrate_basic_time_operations() -> None:
    """演示基础时间操作"""
    print("=" * 60)
    print("1. 基础时间操作演示")
    print("=" * 60)

    # 获取当前时间
    utc_now = time_utils.now()
    china_now = time_utils.now_china()

    print(f"当前 UTC 时间: {utc_now}")
    print(f"当前中国时间: {china_now}")
    print(f"时区信息: UTC={utc_now.tzinfo}, China={china_now.tzinfo}")
    print()


def demonstrate_time_formatting() -> None:
    """演示时间格式化"""
    print("=" * 60)
    print("2. 时间格式化演示")
    print("=" * 60)

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

    for name, format_str in formats.items():
        formatted = time_utils.format_china_time(now, format_str)
        print(f"{name:12}: {formatted}")
    print()


def demonstrate_time_conversion() -> None:
    """演示时间转换"""
    print("=" * 60)
    print("3. 时间转换演示")
    print("=" * 60)

    # 模拟从不同来源获取的时间
    utc_time_str = "2025-01-17T10:30:00Z"
    iso_time_str = "2025-01-17T18:30:00+08:00"
    naive_time_str = "2025-01-17 18:30:00"

    print(f"原始 UTC 时间字符串: {utc_time_str}")
    china_time1 = time_utils.to_china(utc_time_str)
    print(f"转换为中国时间: {time_utils.format_china_time(china_time1)}")
    print()

    print(f"原始 ISO 时间字符串: {iso_time_str}")
    china_time2 = time_utils.to_china(iso_time_str)
    print(f"转换为中国时间: {time_utils.format_china_time(china_time2)}")
    print()

    print(f"原始朴素时间字符串: {naive_time_str}")
    china_time3 = time_utils.to_china(naive_time_str)
    print(f"转换为中国时间: {time_utils.format_china_time(china_time3)}")
    print()


def demonstrate_relative_time() -> None:
    """演示相对时间计算"""
    print("=" * 60)
    print("4. 相对时间计算演示")
    print("=" * 60)

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

    for description, time_point in time_points:
        relative = time_utils.get_relative_time(time_point)
        formatted = time_utils.format_china_time(time_point)
        print(f"{description:8} ({formatted}) -> {relative}")
    print()


def demonstrate_today_check() -> None:
    """演示今天判断"""
    print("=" * 60)
    print("5. 今天判断演示")
    print("=" * 60)

    now = time_utils.now_china()

    # 创建不同日期
    test_dates = [
        ("今天", now),
        ("昨天", now - timedelta(days=1)),
        ("明天", now + timedelta(days=1)),
        ("一周前", now - timedelta(days=7)),
    ]

    for description, test_date in test_dates:
        is_today = time_utils.is_today(test_date)
        formatted = time_utils.format_china_time(test_date, TimeFormats.DATE_FORMAT)
        print(f"{description:6} ({formatted}) -> 是否今天: {is_today}")
    print()


def demonstrate_time_range() -> None:
    """演示时间范围获取"""
    print("=" * 60)
    print("6. 时间范围获取演示")
    print("=" * 60)

    # 获取不同时间范围
    ranges = [
        ("最近1小时", 1),
        ("最近6小时", 6),
        ("最近24小时", 24),
        ("最近3天", 72),
        ("最近7天", 168),
    ]

    for description, hours in ranges:
        time_range = time_utils.get_time_range(hours)
        print(f"{description}:")
        print(f"  开始时间: {time_range['start']}")
        print(f"  结束时间: {time_range['end']}")
        print(f"  开始时间(UTC): {time_range['start_utc']}")
        print(f"  结束时间(UTC): {time_range['end_utc']}")
        print()


def simulate_database_model_usage() -> None:
    """模拟数据库模型中的时间字段使用"""
    print("=" * 60)
    print("7. 数据库模型时间字段使用演示")
    print("=" * 60)

    # 模拟创建记录
    print("创建新记录:")
    created_at = time_utils.now()  # UTC 时间存储到数据库
    print(f"  数据库存储时间 (UTC): {created_at}")
    print(f"  用户显示时间 (中国): {time_utils.format_china_time(created_at)}")
    print()

    # 模拟更新记录
    print("更新记录:")
    updated_at = time_utils.now()
    print(f"  数据库存储时间 (UTC): {updated_at}")
    print(f"  用户显示时间 (中国): {time_utils.format_china_time(updated_at)}")
    print()

    # 模拟查询记录
    print("查询记录时间范围:")
    time_range = time_utils.get_time_range(24)  # 最近24小时
    print(f"  查询开始时间 (UTC): {time_range['start_utc']}")
    print(f"  查询结束时间 (UTC): {time_range['end_utc']}")
    print()


def simulate_api_response_serialization() -> None:
    """模拟 API 响应中的时间序列化"""
    print("=" * 60)
    print("8. API 响应时间序列化演示")
    print("=" * 60)

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
    def serialize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """序列化记录为 API 响应格式"""
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

    api_response = {
        "success": True,
        "data": [serialize_record(record) for record in mock_records],
        "timestamp": time_utils.to_json_serializable(time_utils.now()),
    }

    print("API 响应示例:")
    print(json.dumps(api_response, indent=2, ensure_ascii=False))
    print()


def demonstrate_frontend_integration() -> None:
    """演示前端集成的最佳实践"""
    print("=" * 60)
    print("9. 前端集成最佳实践演示")
    print("=" * 60)

    print("前端 JavaScript 时间处理示例:")
    print()

    # 生成前端 JavaScript 代码示例
    js_code = '''
// 前端时间处理统一使用 timeUtils
const timestamp = "2025-01-17T10:30:00.000Z";

// 基础格式化
const formatted = timeUtils.formatDateTime(timestamp);
console.log("格式化时间:", formatted);

// 相对时间
const relative = timeUtils.formatRelativeTime(timestamp);
console.log("相对时间:", relative);

// 智能时间显示
const smart = timeUtils.formatSmartTime(timestamp);
console.log("智能显示:", smart);

// 判断是否今天
const isToday = timeUtils.isToday(timestamp);
console.log("是否今天:", isToday);

// 时间解析
const parsed = timeUtils.parseTime(timestamp);
console.log("解析结果:", parsed);
'''

    print(js_code)

    print("模板中的时间过滤器使用示例:")
    print()

    # 生成模板代码示例
    template_code = '''
<!-- 使用统一的时间过滤器 -->
<td>{{ instance.created_at | china_datetime }}</td>
<td>{{ instance.last_connected | china_time('%Y-%m-%d %H:%M') }}</td>
<td>{{ log.timestamp | relative_time }}</td>
<td>{{ account.updated_at | smart_time }}</td>
'''

    print(template_code)


def demonstrate_error_handling() -> None:
    """演示时间处理中的错误处理"""
    print("=" * 60)
    print("10. 错误处理演示")
    print("=" * 60)

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
        print(f"输入: {invalid_input} ({type(invalid_input).__name__})")

        # 测试时间转换
        result = time_utils.to_china(invalid_input)
        print(f"  to_china() -> {result}")

        # 测试时间格式化
        formatted = time_utils.format_china_time(invalid_input)
        print(f"  format_china_time() -> {formatted}")

        # 测试相对时间
        relative = time_utils.get_relative_time(invalid_input)
        print(f"  get_relative_time() -> {relative}")

        print()


def demonstrate_performance_considerations() -> None:
    """演示性能考虑"""
    print("=" * 60)
    print("11. 性能考虑演示")
    print("=" * 60)

    import time as time_module

    # 测试批量时间格式化性能
    test_times = [time_utils.now() - timedelta(minutes=i) for i in range(1000)]

    start_time = time_module.time()
    for test_time in test_times:
        time_utils.format_china_time(test_time)
    end_time = time_module.time()

    print(f"格式化 1000 个时间耗时: {(end_time - start_time) * 1000:.2f} ms")

    # 测试时区转换性能
    start_time = time_module.time()
    for test_time in test_times:
        time_utils.to_china(test_time)
    end_time = time_module.time()

    print(f"转换 1000 个时间耗时: {(end_time - start_time) * 1000:.2f} ms")
    print()

    print("性能优化建议:")
    print("1. 在数据库查询时就进行时间范围过滤，避免在应用层过滤大量数据")
    print("2. 对于列表页面，考虑在后端预格式化时间，减少前端计算")
    print("3. 使用缓存机制缓存相对时间计算结果")
    print("4. 避免在循环中重复调用时间格式化函数")
    print()


def main() -> None:
    """主函数：运行所有演示"""
    print("🕒 统一时间处理工具演示")
    print("基于 timezone_and_loglevel_unification.md 强制统一策略")
    print()

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

    print("=" * 60)
    print("✅ 统一时间处理演示完成")
    print("=" * 60)
    print()
    print("核心原则:")
    print("1. 数据库存储：统一使用 UTC 时间")
    print("2. 用户显示：统一转换为中国时区")
    print("3. API 序列化：统一使用 ISO 格式")
    print("4. 前端处理：统一使用 timeUtils 工具")
    print("5. 模板显示：统一使用后端过滤器")
    print()
    print("最佳实践:")
    print("- 后端：强制使用 time_utils.method() 方式")
    print("- 前端：强制使用 timeUtils.method() 方式")
    print("- 模板：使用 china_time、china_datetime 等过滤器")
    print("- 数据库：所有时间字段使用 timezone=True")
    print("- 错误处理：统一返回 '-' 或 None")


if __name__ == "__main__":
    main()