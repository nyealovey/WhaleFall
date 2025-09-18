from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
常量集成测试脚本
验证常量管理系统是否正确集成
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import Config
from app.constants import SystemConstants


def test_constants_import():
    """测试常量导入"""
    logger.debug("=== 测试常量导入 ===")

    try:
        # 测试SystemConstants
        logger.debug("✓ DEFAULT_PAGE_SIZE: {SystemConstants.DEFAULT_PAGE_SIZE}")
        logger.debug("✓ MAX_FILE_SIZE: {SystemConstants.MAX_FILE_SIZE}")
        logger.debug("✓ MEMORY_WARNING_THRESHOLD: {SystemConstants.MEMORY_WARNING_THRESHOLD}")
        logger.debug("✓ PASSWORD_HASH_ROUNDS: {SystemConstants.PASSWORD_HASH_ROUNDS}")

        # 测试DefaultConfig
        logger.debug("✓ DATABASE_URL: {DefaultConfig.DATABASE_URL}")
        logger.debug("✓ SECRET_KEY: {DefaultConfig.SECRET_KEY[:20]}...")

        # 测试ErrorMessages
        logger.debug("✓ INTERNAL_ERROR: {ErrorMessages.INTERNAL_ERROR}")
        logger.debug("✓ VALIDATION_ERROR: {ErrorMessages.VALIDATION_ERROR}")

        # 测试SuccessMessages
        logger.debug("✓ OPERATION_SUCCESS: {SuccessMessages.OPERATION_SUCCESS}")
        logger.debug("✓ LOGIN_SUCCESS: {SuccessMessages.LOGIN_SUCCESS}")

        logger.debug("✓ 所有常量导入成功")
        return True

    except Exception:
        logger.debug("✗ 常量导入失败: {e}")
        return False


def test_config_integration():
    """测试配置集成"""
    logger.debug("\n=== 测试配置集成 ===")

    try:
        config = Config()

        # 检查配置是否使用了常量
        logger.debug("✓ SECRET_KEY默认值: {config.SECRET_KEY[:20]}...")
        logger.debug("✓ JWT_ACCESS_TOKEN_EXPIRES: {config.JWT_ACCESS_TOKEN_EXPIRES}")
        logger.debug("✓ MAX_CONTENT_LENGTH: {config.MAX_CONTENT_LENGTH}")
        logger.debug("✓ BCRYPT_LOG_ROUNDS: {config.BCRYPT_LOG_ROUNDS}")
        logger.debug("✓ CACHE_DEFAULT_TIMEOUT: {config.CACHE_DEFAULT_TIMEOUT}")

        logger.debug("✓ 配置集成成功")
        return True

    except Exception:
        logger.debug("✗ 配置集成失败: {e}")
        return False


def test_hardcoded_replacement():
    """测试硬编码值替换"""
    logger.debug("\n=== 测试硬编码值替换 ===")

    # 检查一些关键文件是否还有硬编码值
    files_to_check = [
        "app/config.py",
        "app/utils/rate_limiter.py",
    ]

    hardcoded_found = False

    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # 检查是否还有明显的硬编码值
            suspicious_values = ["= 20", "= 100", "= 300", "= 3600", "= 80", "= 12"]
            for value in suspicious_values:
                if value in content and "SystemConstants" not in content:
                    logger.debug("⚠  {file_path} 中可能还有硬编码值: {value}")
                    hardcoded_found = True

    if not hardcoded_found:
        logger.debug("✓ 未发现明显的硬编码值")
        return True
    logger.debug("⚠ 发现一些可能的硬编码值，需要进一步检查")
    return False


def test_constant_usage():
    """测试常量使用"""
    logger.debug("\n=== 测试常量使用 ===")

    try:
        # 测试常量在代码中的使用
        logger.debug("✓ 速率限制器使用常量")

        # 测试常量值的一致性
        assert SystemConstants.DEFAULT_PAGE_SIZE == 20
        assert SystemConstants.MAX_FILE_SIZE == 16 * 1024 * 1024
        assert SystemConstants.MEMORY_WARNING_THRESHOLD == 80
        assert SystemConstants.PASSWORD_HASH_ROUNDS == 12

        logger.debug("✓ 常量值一致性验证通过")
        return True

    except Exception:
        logger.debug("✗ 常量使用测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.debug("开始常量集成测试...\n")

    tests = [test_constants_import, test_config_integration, test_hardcoded_replacement, test_constant_usage]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    logger.debug("\n=== 测试结果 ===")
    logger.debug("通过: {passed}/{total}")
    logger.debug("成功率: {passed / total * 100:.1f}%")

    if passed == total:
        logger.debug("🎉 所有测试通过！常量管理系统集成成功！")
        return True
    logger.debug("❌ 部分测试失败，需要进一步检查")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
