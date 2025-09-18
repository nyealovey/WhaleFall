from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3

"""
测试API日志记录功能
"""

import time

import requests


def test_api_endpoints():
    """测试所有API端点的日志记录"""
    base_url = "http://localhost:5001"

    # 需要测试的API端点
    endpoints = [
        "/api/health",
        "/api/status",
        "/api-status",
        "/dashboard/api/overview",
        "/dashboard/api/charts",
        "/dashboard/api/activities",
        "/dashboard/api/status",
    ]

    logger.debug("🧪 开始测试API日志记录...")
    logger.debug("=" * 50)

    for endpoint in endpoints:
        try:
            logger.debug("📡 测试端点: {endpoint}")

            # 发送请求
            response = requests.get(f"{base_url}{endpoint}", timeout=10)

            logger.debug("   ✅ 状态码: {response.status_code}")
            logger.debug("   ⏱️  响应时间: {response.elapsed.total_seconds():.3f}s")

            # 等待一下让日志写入
            time.sleep(0.1)

        except requests.exceptions.RequestException:
            logger.debug("   ❌ 请求失败: {e}")
        except Exception:
            logger.debug("   ❌ 其他错误: {e}")

        logger.debug("")

    logger.debug("=" * 50)
    logger.debug("✅ API日志记录测试完成！")
    logger.debug("\n📋 请检查以下日志文件:")
    logger.debug("   - userdata/logs/api.log (API专用日志)")
    logger.debug("   - userdata/logs/app.log (主应用日志)")


if __name__ == "__main__":
    test_api_endpoints()
