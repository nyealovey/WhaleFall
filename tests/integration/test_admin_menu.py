from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

#!/usr/bin/env python3
"""
管理菜单系统测试脚本
验证管理菜单和布局是否正常工作
"""

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_admin_menu_templates():
    """测试管理菜单模板"""
    logger.debug("=== 测试管理菜单模板 ===")

    try:
        # 检查模板文件是否存在
        template_files = [
            "app/templates/admin/menu.html",
            "app/templates/admin/layout.html",
            "app/templates/admin/dashboard.html",
            "app/templates/admin/system_management.html",
            "app/templates/admin/error_management.html",
            "app/templates/admin/constants.html",
        ]

        missing_files = []
        for file_path in template_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)

        if missing_files:
            logger.debug("✗ 缺少模板文件: {missing_files}")
            return False
        logger.debug("✓ 所有管理菜单模板文件存在")
        return True

    except Exception:
        logger.debug("✗ 模板文件检查失败: {e}")
        return False


def test_admin_endpoints():
    """测试管理API端点"""
    logger.debug("\n=== 测试管理API端点 ===")

    base_url = "http://localhost:5001"
    endpoints = [
        "/admin/dashboard",
        "/admin/system-management",
        "/admin/error-management",
        "/admin/constants",
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
            if response.status_code in [200, 302, 401, 403]:  # 302重定向到登录，401/403需要认证
                logger.debug("✓ {endpoint}: {response.status_code}")
                success_count += 1
            else:
                logger.debug("✗ {endpoint}: {response.status_code}")
        except Exception:
            logger.debug("✗ {endpoint}: 连接失败 - {e}")

    logger.debug("✓ 管理API端点测试: {success_count}/{len(endpoints)} 个端点可访问")
    return success_count >= len(endpoints) * 0.8  # 80% 成功率


def test_menu_structure():
    """测试菜单结构"""
    logger.debug("\n=== 测试菜单结构 ===")

    try:
        # 读取菜单模板文件
        with open("app/templates/admin/menu.html", encoding="utf-8") as f:
            menu_content = f.read()

        # 检查关键菜单项
        menu_items = ["系统概览", "系统管理", "错误管理", "配置管理", "用户管理", "数据管理", "开发工具"]

        missing_items = []
        for item in menu_items:
            if item not in menu_content:
                missing_items.append(item)

        if missing_items:
            logger.debug("✗ 缺少菜单项: {missing_items}")
            return False
        logger.debug("✓ 所有主要菜单项都存在")

        # 检查菜单链接
        menu_links = ["/admin/dashboard", "/admin/system-management", "/admin/error-management", "/admin/constants"]

        missing_links = []
        for link in menu_links:
            if link not in menu_content:
                missing_links.append(link)

        if missing_links:
            logger.debug("✗ 缺少菜单链接: {missing_links}")
            return False
        logger.debug("✓ 所有主要菜单链接都存在")
        return True

    except Exception:
        logger.debug("✗ 菜单结构检查失败: {e}")
        return False


def test_layout_integration():
    """测试布局集成"""
    logger.debug("\n=== 测试布局集成 ===")

    try:
        # 检查布局模板
        with open("app/templates/admin/layout.html", encoding="utf-8") as f:
            layout_content = f.read()

        # 检查关键元素
        layout_elements = ["admin-menu", "admin-content", "管理菜单组件", "管理中心"]

        missing_elements = []
        for element in layout_elements:
            if element not in layout_content:
                missing_elements.append(element)

        if missing_elements:
            logger.debug("✗ 缺少布局元素: {missing_elements}")
            return False
        logger.debug("✓ 所有布局元素都存在")

        # 检查CSS样式
        css_elements = ["position: fixed", "width: 280px", "height: 100vh", "admin-content"]

        missing_css = []
        for css in css_elements:
            if css not in layout_content:
                missing_css.append(css)

        if missing_css:
            logger.debug("✗ 缺少CSS样式: {missing_css}")
            return False
        logger.debug("✓ 所有CSS样式都存在")
        return True

    except Exception:
        logger.debug("✗ 布局集成检查失败: {e}")
        return False


def test_responsive_design():
    """测试响应式设计"""
    logger.debug("\n=== 测试响应式设计 ===")

    try:
        # 检查响应式CSS
        with open("app/templates/admin/menu.html", encoding="utf-8") as f:
            menu_content = f.read()

        responsive_elements = ["@media (max-width: 768px)", "width: 100%", "position: relative"]

        missing_responsive = []
        for element in responsive_elements:
            if element not in menu_content:
                missing_responsive.append(element)

        if missing_responsive:
            logger.debug("✗ 缺少响应式元素: {missing_responsive}")
            return False
        logger.debug("✓ 响应式设计元素完整")
        return True

    except Exception:
        logger.debug("✗ 响应式设计检查失败: {e}")
        return False


def main():
    """主函数"""
    logger.debug("开始管理菜单系统测试...\n")

    tests = [
        test_admin_menu_templates,
        test_admin_endpoints,
        test_menu_structure,
        test_layout_integration,
        test_responsive_design,
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
        logger.debug("🎉 所有测试通过！管理菜单系统完全正常！")
        return True
    logger.debug("❌ 部分测试失败，需要进一步检查")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
