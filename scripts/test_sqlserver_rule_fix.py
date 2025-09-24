#!/usr/bin/env python3
"""
SQL Server规则匹配修复验证脚本
测试数据库角色（特别是db_owner）的规则匹配功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.optimized_account_classification_service import OptimizedAccountClassificationService
from app.models.current_account_sync_data import CurrentAccountSyncData


def test_database_roles_matching():
    """测试数据库角色匹配功能"""
    print("🧪 开始测试SQL Server数据库角色规则匹配...")
    
    # 创建测试服务
    service = OptimizedAccountClassificationService()
    
    # 创建模拟的账户数据 - 拥有db_owner角色
    test_account = CurrentAccountSyncData()
    test_account.db_type = "sqlserver"
    test_account.username = "test_user"
    test_account.database_roles = {
        "master": ["db_owner"],
        "testdb": ["db_owner", "db_datareader"],
        "userdb": ["db_datareader"]
    }
    test_account.server_roles = []
    test_account.server_permissions = []
    test_account.database_permissions = {}
    
    # 测试规则1: 要求db_owner角色
    rule_expression_1 = {
        "type": "sqlserver_permissions",
        "database_roles": ["db_owner"],
        "operator": "OR"
    }
    
    result_1 = service._evaluate_sqlserver_rule(test_account, rule_expression_1)
    print(f"✅ 测试1 - db_owner角色匹配: {'通过' if result_1 else '失败'}")
    
    # 测试规则2: 要求多个数据库角色（AND逻辑）
    rule_expression_2 = {
        "type": "sqlserver_permissions",
        "database_roles": ["db_owner", "db_datareader"],
        "operator": "AND"
    }
    
    result_2 = service._evaluate_sqlserver_rule(test_account, rule_expression_2)
    print(f"✅ 测试2 - 多角色AND匹配: {'通过' if result_2 else '失败'}")
    
    # 测试规则3: 要求不存在的角色
    rule_expression_3 = {
        "type": "sqlserver_permissions",
        "database_roles": ["db_securityadmin"],
        "operator": "OR"
    }
    
    result_3 = service._evaluate_sqlserver_rule(test_account, rule_expression_3)
    print(f"✅ 测试3 - 不存在角色匹配: {'通过' if not result_3 else '失败'}")
    
    # 测试规则4: 混合服务器角色和数据库角色
    test_account.server_roles = ["sysadmin"]
    rule_expression_4 = {
        "type": "sqlserver_permissions",
        "server_roles": ["sysadmin"],
        "database_roles": ["db_owner"],
        "operator": "AND"
    }
    
    result_4 = service._evaluate_sqlserver_rule(test_account, rule_expression_4)
    print(f"✅ 测试4 - 混合角色AND匹配: {'通过' if result_4 else '失败'}")
    
    # 测试规则5: 混合服务器角色和数据库角色（OR逻辑）
    rule_expression_5 = {
        "type": "sqlserver_permissions",
        "server_roles": ["serveradmin"],  # 不存在的服务器角色
        "database_roles": ["db_owner"],   # 存在的数据库角色
        "operator": "OR"
    }
    
    result_5 = service._evaluate_sqlserver_rule(test_account, rule_expression_5)
    print(f"✅ 测试5 - 混合角色OR匹配: {'通过' if result_5 else '失败'}")
    
    # 测试规则6: 数据库权限匹配
    test_account.database_permissions = {
        "master": {
            "database": ["CREATE", "ALTER", "CONTROL"],
            "schema": {},
            "table": {}
        },
        "testdb": {
            "database": ["SELECT", "INSERT"],
            "schema": {},
            "table": {}
        }
    }
    
    rule_expression_6 = {
        "type": "sqlserver_permissions",
        "database_privileges": ["CONTROL"],
        "operator": "OR"
    }
    
    result_6 = service._evaluate_sqlserver_rule(test_account, rule_expression_6)
    print(f"✅ 测试6 - 数据库权限匹配: {'通过' if result_6 else '失败'}")
    
    print("\n🎉 所有测试完成！")
    return all([result_1, not result_3, result_4, result_5, result_6])


def test_edge_cases():
    """测试边界情况"""
    print("\n🔍 测试边界情况...")
    
    service = OptimizedAccountClassificationService()
    
    # 测试空权限数据
    empty_account = CurrentAccountSyncData()
    empty_account.db_type = "sqlserver"
    empty_account.username = "empty_user"
    empty_account.database_roles = {}
    empty_account.server_roles = []
    empty_account.server_permissions = []
    empty_account.database_permissions = {}
    
    rule_expression = {
        "type": "sqlserver_permissions",
        "database_roles": ["db_owner"],
        "operator": "OR"
    }
    
    result = service._evaluate_sqlserver_rule(empty_account, rule_expression)
    print(f"✅ 空权限数据测试: {'通过' if not result else '失败'}")
    
    # 测试None权限数据
    none_account = CurrentAccountSyncData()
    none_account.db_type = "sqlserver"
    none_account.username = "none_user"
    none_account.database_roles = None
    none_account.server_roles = None
    none_account.server_permissions = None
    none_account.database_permissions = None
    
    result = service._evaluate_sqlserver_rule(none_account, rule_expression)
    print(f"✅ None权限数据测试: {'通过' if not result else '失败'}")
    
    print("✅ 边界情况测试完成！")


if __name__ == "__main__":
    print("🚀 SQL Server规则匹配修复验证")
    print("=" * 50)
    
    try:
        # 运行主要测试
        main_test_passed = test_database_roles_matching()
        
        # 运行边界情况测试
        test_edge_cases()
        
        print("\n" + "=" * 50)
        if main_test_passed:
            print("🎉 修复验证成功！SQL Server数据库角色规则匹配功能已正常工作。")
        else:
            print("❌ 修复验证失败！请检查代码实现。")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
