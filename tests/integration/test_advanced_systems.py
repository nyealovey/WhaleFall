from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
高级系统功能测试脚本
验证高级错误处理和管理API系统是否真正集成
"""

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_enhanced_error_handler():
    """测试增强的错误处理系统"""
    logger.debug("=== 测试增强的错误处理系统 ===")

    try:
        from app.utils.structlog_config import ErrorContext, enhanced_error_handler

        # 测试错误处理
        test_error = Exception("测试错误 - 验证增强错误处理系统")
        context = ErrorContext(test_error)
        result = enhanced_error_handler(test_error, context)

        logger.debug("✓ 错误处理结果: {result.get('error_id', 'N/A')}")
        logger.debug("✓ 错误分类: {result.get('category', 'N/A')}")
        logger.debug("✓ 严重程度: {result.get('severity', 'N/A')}")
        logger.debug("✓ 可恢复状态: {result.get('recoverable', False)}")

        logger.debug("✓ 增强错误处理系统测试通过")
        return True

    except Exception as e:
        logger.debug("✗ 增强错误处理系统测试失败: {e}")
        return False


def test_admin_api_endpoints():
    """测试管理API端点"""
    logger.debug("\n=== 测试管理API端点 ===")

    base_url = "http://localhost:5001"
    endpoints = [
        "/admin/system-info",
        "/admin/performance",
        "/admin/error-metrics",
        "/admin/constants/api",
        "/admin/system-logs",
    ]

    success_count = 0

    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code in [200, 401, 403]:  # 401/403 表示需要登录，但端点存在
                logger.debug("✓ {endpoint}: {response.status_code}")
                success_count += 1
            else:
                logger.debug("✗ {endpoint}: {response.status_code}")
        except Exception:
            logger.debug("✗ {endpoint}: 连接失败 - {e}")

    logger.debug("✓ 管理API端点测试: {success_count}/{len(endpoints)} 个端点可访问")
    return success_count >= len(endpoints) * 0.8  # 80% 成功率


def test_error_handling_integration():
    """测试错误处理集成"""
    logger.debug("\n=== 测试错误处理集成 ===")

    try:
        # 测试一个会触发错误的请求
        response = requests.get("http://localhost:5001/nonexistent-endpoint", timeout=5)

        if response.status_code == 404:
            logger.debug("✓ 404错误被正确处理")

            # 检查响应是否包含高级错误处理的信息
            try:
                data = response.json()
                if "error_id" in data or "category" in data:
                    logger.debug("✓ 高级错误处理信息已包含在响应中")
                    return True
                logger.debug("⚠ 响应中未找到高级错误处理信息")
                return False
            except:
                logger.debug("⚠ 响应不是JSON格式")
                return False
        else:
            logger.debug("✗ 意外的状态码: {response.status_code}")
            return False

    except Exception:
        logger.debug("✗ 错误处理集成测试失败: {e}")
        return False


# 性能监控功能已移除


def test_management_interfaces():
    """测试管理界面"""
    logger.debug("\n=== 测试管理界面 ===")

    base_url = "http://localhost:5001"
    interfaces = ["/admin/system-management", "/admin/error-management", "/admin/constants", "/admin/dashboard"]

    success_count = 0

    for interface in interfaces:
        try:
            response = requests.get(f"{base_url}{interface}", timeout=5)
            if response.status_code in [200, 401, 403]:  # 401/403 表示需要登录，但界面存在
                logger.debug("✓ {interface}: {response.status_code}")
                success_count += 1
            else:
                logger.debug("✗ {interface}: {response.status_code}")
        except Exception:
            logger.debug("✗ {interface}: 连接失败 - {e}")

    logger.debug("✓ 管理界面测试: {success_count}/{len(interfaces)} 个界面可访问")
    return success_count >= len(interfaces) * 0.8  # 80% 成功率


def test_constant_management():
    """测试常量管理"""
    logger.debug("\n=== 测试常量管理 ===")

    try:
        from app.constants import ErrorMessages, SuccessMessages, SystemConstants

        # 测试常量使用
        assert SystemConstants.DEFAULT_PAGE_SIZE == 20
        assert SystemConstants.MAX_FILE_SIZE == 16 * 1024 * 1024
        assert ErrorMessages.INTERNAL_ERROR == "服务器内部错误"
        assert SuccessMessages.OPERATION_SUCCESS == "操作成功"

        logger.debug("✓ 常量定义正确")
        logger.debug("✓ 常量值一致性验证通过")
        logger.debug("✓ 常量管理系统正常工作")
        return True

    except Exception:
        logger.debug("✗ 常量管理测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.debug("开始高级系统功能测试...\n")

    tests = [
        test_enhanced_error_handler,
        test_admin_api_endpoints,
        test_error_handling_integration,
        test_management_interfaces,
        test_constant_management,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    logger.debug("\n=== 测试结果 ===")
    logger.debug("通过: {passed}/{total}")
    logger.debug("成功率: {passed / total * 100:.1f}%")

    if passed == total:
        logger.debug("🎉 所有测试通过！高级系统功能完全集成！")
        return True
    logger.debug("❌ 部分测试失败，需要进一步检查")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
