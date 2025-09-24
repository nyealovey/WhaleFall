#!/usr/bin/env python3
"""
清除所有缓存脚本
"""

def clear_all_caches():
    """清除所有缓存"""
    print("🔍 清除所有缓存")
    print("=" * 60)
    
    print("📋 问题分析:")
    print("  - 规则查询中的JOIN操作导致mysql_grant_rule被过滤")
    print("  - 缓存中可能包含旧的规则数据")
    print("  - 需要清除所有缓存确保修复生效")
    print()
    
    print("🛠️ 修复内容:")
    print("  1. 移除规则查询中的JOIN操作")
    print("  2. 添加详细的规则加载和分组日志")
    print("  3. 确保所有激活的规则都能被正确加载")
    print()
    
    print("📝 需要执行的API调用:")
    print("  POST /account-classification/api/cache/clear")
    print("  POST /account-classification/api/cache/clear/mysql")
    print("  POST /cache/api/cache/clear/all")
    print()
    
    print("🎯 预期结果:")
    print("  - 所有缓存被清除")
    print("  - 系统重新从数据库加载最新规则")
    print("  - 日志中显示mysql_grant_rule被正确加载")
    print("  - mysql_grant_rule能够正确匹配账户")
    print()
    
    print("🔍 验证方法:")
    print("  1. 查看日志中是否显示'从数据库加载分类规则'")
    print("  2. 查看日志中是否显示'mysql_grant_rule'在规则列表中")
    print("  3. 查看日志中是否显示'规则 mysql_grant_rule 处理完成'")
    print("  4. 检查mysql_grant_rule的匹配账户数量")

if __name__ == "__main__":
    clear_all_caches()
