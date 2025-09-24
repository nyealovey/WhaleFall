#!/usr/bin/env python3
"""
测试数据库规则匹配过程
"""

def test_database_rule_matching():
    """测试数据库规则匹配过程"""
    print("🔍 数据库规则匹配过程测试")
    print("=" * 60)
    
    # 模拟从数据库读取的规则数据
    rule_data = {
        "id": 9,
        "classification_id": 2,
        "db_type": "mysql",
        "rule_name": "mysql_grant_rule",
        "rule_expression": '{"type": "mysql_permissions", "global_privileges": ["GRANT OPTION"], "database_privileges": [], "operator": "OR"}',
        "is_active": True
    }
    
    # 模拟从数据库读取的账户数据
    account_data = {
        "id": 1,
        "username": "jinxj",
        "db_type": "mysql",
        "global_privileges": [
            "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "RELOAD", 
            "SHUTDOWN", "PROCESS", "FILE", "REFERENCES", "INDEX", "ALTER", 
            "SHOW DATABASES", "SUPER", "CREATE TEMPORARY TABLES", "LOCK TABLES", 
            "EXECUTE", "REPLICATION SLAVE", "REPLICATION CLIENT", "CREATE VIEW", 
            "SHOW VIEW", "CREATE ROUTINE", "ALTER ROUTINE", "CREATE USER", 
            "EVENT", "TRIGGER", "CREATE TABLESPACE", "USAGE", "GRANT OPTION"
        ],
        "database_privileges": {},
        "type_specific": {
            "host": "localhost",
            "can_grant": True,
            "is_locked": False
        }
    }
    
    print(f"📋 规则数据: {rule_data}")
    print(f"📋 账户数据: {account_data}")
    
    # 解析规则表达式
    import json
    try:
        rule_expression = json.loads(rule_data["rule_expression"])
        print(f"✅ 规则表达式解析成功: {rule_expression}")
    except Exception as e:
        print(f"❌ 规则表达式解析失败: {e}")
        return
    
    # 模拟账户对象的get_permissions_by_db_type方法
    def get_permissions_by_db_type():
        return {
            "global_privileges": account_data["global_privileges"],
            "database_privileges": account_data["database_privileges"],
            "type_specific": account_data["type_specific"]
        }
    
    # 模拟规则评估
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
    
    # 执行规则匹配
    print(f"\n🔍 执行规则匹配")
    print("-" * 40)
    
    permissions = get_permissions_by_db_type()
    result = evaluate_mysql_rule(permissions, rule_expression)
    
    print(f"\n📋 最终匹配结果: {'✅ 匹配' if result else '❌ 不匹配'}")
    
    # 检查规则类型
    rule_type = rule_expression.get("type", "")
    print(f"\n🔍 规则类型检查")
    print("-" * 40)
    print(f"📋 规则类型: {rule_type}")
    
    if rule_type == "mysql_permissions":
        print(f"✅ 规则类型正确")
    else:
        print(f"❌ 规则类型不正确，期望: mysql_permissions，实际: {rule_type}")
    
    # 检查权限数据格式
    print(f"\n🔍 权限数据格式检查")
    print("-" * 40)
    
    global_privs = permissions.get("global_privileges", [])
    print(f"📋 全局权限类型: {type(global_privs)}")
    print(f"📋 全局权限长度: {len(global_privs)}")
    
    if isinstance(global_privs, list):
        print(f"✅ 全局权限是列表格式")
    else:
        print(f"❌ 全局权限不是列表格式")
    
    # 检查GRANT OPTION权限
    if "GRANT OPTION" in global_privs:
        print(f"✅ 包含GRANT OPTION权限")
    else:
        print(f"❌ 不包含GRANT OPTION权限")
    
    # 检查SUPER权限
    if "SUPER" in global_privs:
        print(f"✅ 包含SUPER权限")
    else:
        print(f"❌ 不包含SUPER权限")

if __name__ == "__main__":
    test_database_rule_matching()
