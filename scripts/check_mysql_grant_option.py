#!/usr/bin/env python3
"""
检查MySQL账户的GRANT OPTION权限
"""

def check_mysql_grant_option():
    """检查MySQL账户的GRANT OPTION权限"""
    print("🔍 检查MySQL账户的GRANT OPTION权限")
    print("=" * 60)
    
    print("📋 问题分析:")
    print("  - mysql_grant_rule规则已加载但未匹配到账户")
    print("  - 需要检查MySQL账户是否实际拥有GRANT OPTION权限")
    print("  - 需要检查权限数据格式是否正确")
    print()
    
    print("🔍 检查步骤:")
    print("  1. 查看MySQL账户的global_privileges数据")
    print("  2. 检查是否包含'GRANT OPTION'权限")
    print("  3. 验证权限数据格式")
    print("  4. 检查规则评估逻辑")
    print()
    
    print("📝 SQL查询示例:")
    print("  SELECT id, username, global_privileges")
    print("  FROM current_account_sync_data")
    print("  WHERE instance_id IN (SELECT id FROM instances WHERE db_type = 'mysql')")
    print("  AND global_privileges IS NOT NULL")
    print("  AND global_privileges::text LIKE '%GRANT OPTION%';")
    print()
    
    print("🎯 预期结果:")
    print("  - 应该找到包含'GRANT OPTION'的账户")
    print("  - 权限数据格式应该是字符串列表或字典列表")
    print("  - mysql_grant_rule应该能匹配到这些账户")

if __name__ == "__main__":
    check_mysql_grant_option()
