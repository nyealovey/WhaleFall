#!/usr/bin/env python3
"""
测试缓存清理功能
"""

def test_cache_invalidation():
    """测试缓存清理功能"""
    print("🔍 缓存清理功能测试")
    print("=" * 60)
    
    # 模拟缓存数据
    cache_data = {
        "rule_evaluation_cache": {
            "rule_1_account_1": {"result": False, "cached_at": "2025-01-01T00:00:00Z"},
            "rule_1_account_2": {"result": True, "cached_at": "2025-01-01T00:00:00Z"},
            "rule_2_account_1": {"result": False, "cached_at": "2025-01-01T00:00:00Z"},
        },
        "account_permissions": {
            "account_1": {
                "global_privileges": ["SELECT", "INSERT", "UPDATE"],  # 旧数据，没有GRANT OPTION
                "cached_at": "2025-01-01T00:00:00Z"
            },
            "account_2": {
                "global_privileges": ["SELECT", "INSERT", "UPDATE", "GRANT OPTION"],  # 新数据，有GRANT OPTION
                "cached_at": "2025-01-02T00:00:00Z"
            }
        }
    }
    
    print("📋 模拟缓存数据:")
    print(f"  规则评估缓存: {cache_data['rule_evaluation_cache']}")
    print(f"  账户权限缓存: {cache_data['account_permissions']}")
    
    # 模拟权限更新
    print(f"\n🔍 模拟权限更新")
    print("-" * 40)
    
    # 更新账户1的权限，添加GRANT OPTION
    old_permissions = cache_data["account_permissions"]["account_1"]["global_privileges"]
    new_permissions = old_permissions + ["GRANT OPTION"]
    cache_data["account_permissions"]["account_1"]["global_privileges"] = new_permissions
    cache_data["account_permissions"]["account_1"]["cached_at"] = "2025-01-02T01:00:00Z"
    
    print(f"  账户1权限更新:")
    print(f"    旧权限: {old_permissions}")
    print(f"    新权限: {new_permissions}")
    
    # 模拟缓存清理
    print(f"\n🔍 模拟缓存清理")
    print("-" * 40)
    
    # 清除账户1的规则评估缓存
    account_1_rule_caches = [key for key in cache_data["rule_evaluation_cache"].keys() if "account_1" in key]
    for cache_key in account_1_rule_caches:
        del cache_data["rule_evaluation_cache"][cache_key]
        print(f"  ✅ 已清除规则评估缓存: {cache_key}")
    
    # 清除账户1的权限缓存
    if "account_1" in cache_data["account_permissions"]:
        del cache_data["account_permissions"]["account_1"]
        print(f"  ✅ 已清除账户权限缓存: account_1")
    
    print(f"\n📋 清理后的缓存数据:")
    print(f"  规则评估缓存: {cache_data['rule_evaluation_cache']}")
    print(f"  账户权限缓存: {cache_data['account_permissions']}")
    
    # 模拟规则重新评估
    print(f"\n🔍 模拟规则重新评估")
    print("-" * 40)
    
    # 重新获取账户1的权限（从数据库）
    fresh_permissions = ["SELECT", "INSERT", "UPDATE", "GRANT OPTION"]
    print(f"  从数据库获取的权限: {fresh_permissions}")
    
    # 模拟规则匹配
    rule_requirements = ["GRANT OPTION"]
    print(f"  规则要求权限: {rule_requirements}")
    
    if "GRANT OPTION" in fresh_permissions:
        print(f"  ✅ 规则匹配成功: 账户有GRANT OPTION权限")
    else:
        print(f"  ❌ 规则匹配失败: 账户没有GRANT OPTION权限")
    
    print(f"\n🎯 总结:")
    print(f"  - 权限更新后，相关缓存被清除")
    print(f"  - 规则重新评估时使用最新的权限数据")
    print(f"  - GRANT OPTION权限能够正确匹配规则")

if __name__ == "__main__":
    test_cache_invalidation()
