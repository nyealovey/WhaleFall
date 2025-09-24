#!/usr/bin/env python3
"""
测试实际权限匹配过程
"""

def test_actual_permission_matching():
    """测试实际权限匹配过程"""
    print("🔍 实际权限匹配过程测试")
    print("=" * 60)
    
    # 模拟从数据库读取的账户权限数据
    account_permissions = {
        "global_privileges": [
            "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "RELOAD", 
            "SHUTDOWN", "PROCESS", "FILE", "REFERENCES", "INDEX", "ALTER", 
            "SHOW DATABASES", "SUPER", "CREATE TEMPORARY TABLES", "LOCK TABLES", 
            "EXECUTE", "REPLICATION SLAVE", "REPLICATION CLIENT", "CREATE VIEW", 
            "SHOW VIEW", "CREATE ROUTINE", "ALTER ROUTINE", "CREATE USER", 
            "EVENT", "TRIGGER", "CREATE TABLESPACE", "USAGE", "GRANT OPTION"
        ],
        "database_privileges": {},
        "type_specific": {}
    }
    
    # 模拟规则表达式
    test_rules = [
        {
            "name": "SUPER权限规则",
            "rule_expression": {
                "operator": "OR",
                "global_privileges": ["SUPER"]
            }
        },
        {
            "name": "GRANT OPTION权限规则",
            "rule_expression": {
                "operator": "OR",
                "global_privileges": ["GRANT OPTION"]
            }
        },
        {
            "name": "混合权限规则",
            "rule_expression": {
                "operator": "OR",
                "global_privileges": ["SUPER", "GRANT OPTION"]
            }
        }
    ]
    
    def evaluate_mysql_rule(permissions: dict, rule_expression: dict) -> bool:
        """评估MySQL规则"""
        try:
            operator = rule_expression.get("operator", "OR").upper()
            
            # 检查全局权限
            required_global = rule_expression.get("global_privileges", [])
            if required_global:
                actual_global = permissions.get("global_privileges", [])
                if isinstance(actual_global, list):
                    actual_global_set = set(actual_global)
                else:
                    actual_global_set = {p["privilege"] for p in actual_global if p.get("granted", False)}
                
                print(f"  📝 要求的全局权限: {required_global}")
                print(f"  📝 实际的全局权限: {sorted(actual_global_set)}")
                
                # 详细检查每个权限
                for req_perm in required_global:
                    if req_perm in actual_global_set:
                        print(f"    ✅ {req_perm} 权限匹配成功")
                    else:
                        print(f"    ❌ {req_perm} 权限匹配失败")
                
                if operator == "AND":
                    if not all(perm in actual_global_set for perm in required_global):
                        missing = set(required_global) - actual_global_set
                        print(f"  ❌ AND模式：缺少权限 {missing}")
                        return False
                else:
                    if not any(perm in actual_global_set for perm in required_global):
                        print(f"  ❌ OR模式：没有匹配的权限")
                        return False
                
                print(f"  ✅ 全局权限匹配成功")
            
            return True
            
        except Exception as e:
            print(f"  ❌ 评估规则失败: {e}")
            return False
    
    # 测试每个规则
    for rule in test_rules:
        print(f"\n📋 测试规则: {rule['name']}")
        print("-" * 40)
        
        result = evaluate_mysql_rule(account_permissions, rule['rule_expression'])
        
        if result:
            print(f"✅ 规则匹配成功")
        else:
            print(f"❌ 规则匹配失败")
        
        print()
    
    # 测试权限名称的精确比较
    print("🔍 权限名称精确比较测试")
    print("-" * 40)
    
    actual_privileges = account_permissions["global_privileges"]
    
    test_permissions = ["SUPER", "GRANT OPTION", "SELECT", "INSERT"]
    
    for perm in test_permissions:
        print(f"📋 测试权限: '{perm}'")
        print(f"  📝 在权限列表中: {perm in actual_privileges}")
        print(f"  📝 权限长度: {len(perm)}")
        print(f"  📝 权限字节: {[ord(c) for c in perm]}")
        
        # 检查是否有完全匹配的权限
        exact_matches = [p for p in actual_privileges if p == perm]
        print(f"  📝 完全匹配: {exact_matches}")
        
        # 检查包含关系
        contains_matches = [p for p in actual_privileges if perm in p]
        print(f"  📝 包含匹配: {contains_matches}")
        
        print()

if __name__ == "__main__":
    test_actual_permission_matching()
