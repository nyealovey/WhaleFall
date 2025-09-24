#!/usr/bin/env python3
"""
调试mysql_grant_rule匹配问题
"""

def debug_mysql_grant_rule():
    """调试mysql_grant_rule匹配问题"""
    print("🔍 调试mysql_grant_rule匹配问题")
    print("=" * 60)
    
    print("📋 问题分析:")
    print("  - mysql_grant_rule规则已加载并处理")
    print("  - 但是matched_accounts=0，说明没有匹配到账户")
    print("  - 需要检查权限数据格式和规则评估逻辑")
    print()
    
    print("🔍 调试步骤:")
    print("  1. 检查mysql_grant_rule的规则表达式")
    print("  2. 检查MySQL账户的global_privileges数据")
    print("  3. 检查权限数据格式（字符串 vs 字典）")
    print("  4. 检查规则评估逻辑")
    print()
    
    print("📝 规则表达式:")
    print('  {"type": "mysql_permissions", "global_privileges": ["GRANT OPTION"], "database_privileges": [], "operator": "OR"}')
    print()
    
    print("🔍 可能的问题:")
    print("  1. 权限数据格式不匹配")
    print("     - 规则期望: 字符串列表 ['GRANT OPTION']")
    print("     - 实际数据: 可能是字典列表 [{'privilege': 'GRANT OPTION', 'granted': True}]")
    print("  2. 权限名称不匹配")
    print("     - 规则期望: 'GRANT OPTION'")
    print("     - 实际数据: 可能是 'GRANT' 或其他名称")
    print("  3. 权限解析问题")
    print("     - WITH GRANT OPTION 可能没有正确解析为 GRANT OPTION")
    print()
    
    print("🎯 解决方案:")
    print("  1. 检查实际的权限数据格式")
    print("  2. 修复权限数据格式转换逻辑")
    print("  3. 确保GRANT OPTION权限正确解析和存储")

if __name__ == "__main__":
    debug_mysql_grant_rule()
