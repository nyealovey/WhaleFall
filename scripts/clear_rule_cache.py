#!/usr/bin/env python3
"""
清除规则缓存脚本
"""

def clear_rule_cache():
    """清除规则缓存"""
    print("🔍 清除规则缓存")
    print("=" * 60)
    
    print("📋 问题分析:")
    print("  - 规则从缓存获取，可能不包含最新的mysql_grant_rule")
    print("  - 需要清除规则缓存，让系统重新从数据库获取规则")
    print()
    
    print("🛠️ 解决方案:")
    print("  1. 调用API清除分类缓存")
    print("  2. 重新运行自动分类")
    print("  3. 验证mysql_grant_rule是否匹配")
    print()
    
    print("📝 API调用示例:")
    print("  POST /account-classification/api/cache/clear")
    print("  POST /account-classification/api/cache/clear/mysql")
    print()
    
    print("🎯 预期结果:")
    print("  - 规则缓存被清除")
    print("  - 系统重新从数据库获取最新规则")
    print("  - mysql_grant_rule能够正确匹配账户")

if __name__ == "__main__":
    clear_rule_cache()
