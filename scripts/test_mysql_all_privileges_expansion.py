#!/usr/bin/env python3
"""
测试MySQL ALL PRIVILEGES展开功能
"""

def _expand_all_privileges():
    """将ALL PRIVILEGES展开为MySQL 5.7的具体权限列表"""
    # MySQL 5.7 全局权限的完整列表
    return [
        "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "RELOAD", 
        "SHUTDOWN", "PROCESS", "FILE", "REFERENCES", "INDEX", "ALTER", 
        "SHOW DATABASES", "SUPER", "CREATE TEMPORARY TABLES", "LOCK TABLES", 
        "EXECUTE", "REPLICATION SLAVE", "REPLICATION CLIENT", "CREATE VIEW", 
        "SHOW VIEW", "CREATE ROUTINE", "ALTER ROUTINE", "CREATE USER", 
        "EVENT", "TRIGGER", "CREATE TABLESPACE", "USAGE"
    ]

def _extract_privileges_from_string(privileges_str: str) -> list[str]:
    """从权限字符串中提取权限列表"""
    # 移除ON子句，只保留权限部分
    privileges_part = privileges_str.split(" ON ")[0].strip()
    
    # ALL PRIVILEGES 需要拆分成具体的权限列表
    if "ALL PRIVILEGES" in privileges_part.upper():
        return _expand_all_privileges()
    
    # 分割权限并清理
    privileges = []
    for priv in privileges_part.split(","):
        priv = priv.strip().upper()
        if priv and not priv.startswith("ON "):
            privileges.append(priv)
    
    return privileges

def test_grant_permission_handling():
    """测试GRANT权限处理功能"""
    print("\n🔐 MySQL GRANT权限处理测试")
    print("=" * 60)
    
    # 模拟解析GRANT语句的过程
    test_grant_statements = [
        "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION",
        "GRANT SELECT, INSERT, UPDATE ON `testdb`.* TO 'user'@'%' WITH GRANT OPTION",
        "GRANT SELECT, INSERT ON `testdb`.* TO 'user'@'%'",
        "GRANT ALL PRIVILEGES ON *.* TO 'admin'@'localhost'",
    ]
    
    for i, grant_statement in enumerate(test_grant_statements, 1):
        print(f"\n📋 GRANT语句 {i}: {grant_statement}")
        print("-" * 50)
        
        # 检查是否有WITH GRANT OPTION
        has_grant_option = "WITH GRANT OPTION" in grant_statement.upper()
        print(f"🎯 检测到WITH GRANT OPTION: {has_grant_option}")
        
        # 模拟解析权限
        simple_grant = grant_statement.upper().replace("GRANT ", "").replace(" WITH GRANT OPTION", "")
        
        # 匹配全局权限
        import re
        global_match = re.match(r"(.+?) ON \*\.\*", simple_grant)
        if global_match:
            privileges_str = global_match.group(1)
            privileges = _extract_privileges_from_string(privileges_str)
            print(f"✅ 全局权限: {privileges}")
            if has_grant_option and "GRANT" not in privileges:
                privileges.append("GRANT")
                print(f"🔑 添加GRANT权限: {privileges}")
        
        # 匹配数据库权限
        db_match = re.match(r"(.+?) ON `(.+?)`\.\*", simple_grant)
        if db_match:
            privileges_str = db_match.group(1)
            db_name = db_match.group(2)
            privileges = _extract_privileges_from_string(privileges_str)
            print(f"✅ 数据库权限 [{db_name}]: {privileges}")
            if has_grant_option:
                print(f"🔑 检测到GRANT OPTION，应添加到全局权限")

def test_all_privileges_expansion():
    """测试ALL PRIVILEGES展开功能"""
    
    # 测试用例
    test_cases = [
        # 旧版本MySQL格式 (ALL PRIVILEGES)
        "ALL PRIVILEGES ON *.*",
        "ALL PRIVILEGES ON `testdb`.*",
        
        # 新版本MySQL格式 (具体权限列表)
        "SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, RELOAD, SHUTDOWN, PROCESS, FILE, REFERENCES, INDEX, ALTER, SHOW DATABASES, SUPER, CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, REPLICATION SLAVE, REPLICATION CLIENT, CREATE VIEW, SHOW VIEW, CREATE ROUTINE, ALTER ROUTINE, CREATE USER, EVENT, TRIGGER, CREATE TABLESPACE ON *.*",
        
        # 混合格式
        "SELECT, INSERT, ALL PRIVILEGES ON `testdb`.*",
        
        # 部分权限
        "SELECT, INSERT, UPDATE ON `testdb`.*",
        
        # 带WITH GRANT OPTION的权限
        "ALL PRIVILEGES ON *.* WITH GRANT OPTION",
        "SELECT, INSERT, UPDATE ON `testdb`.* WITH GRANT OPTION",
    ]
    
    print("🔍 MySQL权限展开测试")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case}")
        print("-" * 40)
        
        try:
            # 模拟解析过程
            privileges_str = test_case.split(" ON ")[0].strip()
            privileges = _extract_privileges_from_string(privileges_str)
            
            print(f"✅ 解析结果: {len(privileges)} 个权限")
            print(f"📝 权限列表: {privileges}")
            
            # 检查是否包含ALL PRIVILEGES
            if "ALL PRIVILEGES" in test_case.upper():
                print("🎯 检测到ALL PRIVILEGES，已展开为具体权限")
            else:
                print("📋 具体权限列表，直接解析")
                
        except Exception as e:
            print(f"❌ 解析失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")

if __name__ == "__main__":
    test_grant_permission_handling()
    test_all_privileges_expansion()
