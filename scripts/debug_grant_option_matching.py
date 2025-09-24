#!/usr/bin/env python3
"""
调试GRANT OPTION权限匹配问题
"""

def debug_grant_option_matching():
    """调试GRANT OPTION权限匹配问题"""
    print("🔍 调试GRANT OPTION权限匹配问题")
    print("=" * 60)
    
    # 模拟mysql_grant_rule的配置
    rule_expression = {
        "type": "mysql_permissions",
        "global_privileges": ["GRANT OPTION"],
        "database_privileges": [],
        "operator": "OR"
    }
    
    print("📋 规则配置:")
    print(f"  规则表达式: {rule_expression}")
    print()
    
    # 模拟不同的权限数据格式
    test_cases = [
        {
            "name": "格式1: 简单列表格式",
            "permissions": {
                "global_privileges": ["SELECT", "INSERT", "UPDATE", "GRANT OPTION"],
                "database_privileges": {},
                "type_specific": {}
            }
        },
        {
            "name": "格式2: 复杂对象格式",
            "permissions": {
                "global_privileges": [
                    {"privilege": "SELECT", "granted": True},
                    {"privilege": "INSERT", "granted": True},
                    {"privilege": "UPDATE", "granted": True},
                    {"privilege": "GRANT OPTION", "granted": True}
                ],
                "database_privileges": {},
                "type_specific": {}
            }
        },
        {
            "name": "格式3: 混合格式",
            "permissions": {
                "global_privileges": [
                    "SELECT",
                    "INSERT", 
                    {"privilege": "UPDATE", "granted": True},
                    "GRANT OPTION"
                ],
                "database_privileges": {},
                "type_specific": {}
            }
        },
        {
            "name": "格式4: 空权限",
            "permissions": {
                "global_privileges": [],
                "database_privileges": {},
                "type_specific": {}
            }
        },
        {
            "name": "格式5: None权限",
            "permissions": {
                "global_privileges": None,
                "database_privileges": {},
                "type_specific": {}
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        
        permissions = test_case["permissions"]
        print(f"  权限数据: {permissions}")
        
        # 模拟_evaluate_mysql_rule的逻辑
        result = evaluate_mysql_rule_debug(permissions, rule_expression)
        print(f"  匹配结果: {'✅ 匹配' if result else '❌ 不匹配'}")
        print()
    
    print("🎯 分析总结:")
    print("  - 检查权限数据格式是否正确")
    print("  - 检查GRANT OPTION权限是否存在")
    print("  - 检查规则评估逻辑是否正确")

def evaluate_mysql_rule_debug(permissions: dict, rule_expression: dict) -> bool:
    """模拟_evaluate_mysql_rule方法的调试版本（修复后）"""
    try:
        if not permissions:
            print("    ❌ 权限数据为空")
            return False

        operator = rule_expression.get("operator", "OR").upper()
        print(f"    操作符: {operator}")

        # 检查全局权限
        required_global = rule_expression.get("global_privileges", [])
        print(f"    要求的全局权限: {required_global}")
        
        if required_global:
            actual_global = permissions.get("global_privileges", [])
            print(f"    实际的全局权限: {actual_global}")
            
            if actual_global is None:
                actual_global_set = set()
                print(f"    权限集合(None处理): {actual_global_set}")
            elif isinstance(actual_global, list):
                # 处理混合格式：字符串和字典的混合列表
                actual_global_set = set()
                for perm in actual_global:
                    if isinstance(perm, str):
                        actual_global_set.add(perm)
                    elif isinstance(perm, dict) and perm.get("granted", False):
                        actual_global_set.add(perm["privilege"])
                print(f"    权限集合(混合格式): {actual_global_set}")
            else:
                actual_global_set = {p["privilege"] for p in actual_global if p.get("granted", False)}
                print(f"    权限集合(对象格式): {actual_global_set}")

            if operator == "AND":
                match = all(perm in actual_global_set for perm in required_global)
                print(f"    AND匹配: {match}")
                if not match:
                    return False
            else:
                match = any(perm in actual_global_set for perm in required_global)
                print(f"    OR匹配: {match}")
                if not match:
                    return False

        return True

    except Exception as e:
        print(f"    ❌ 评估失败: {e}")
        return False

if __name__ == "__main__":
    debug_grant_option_matching()
