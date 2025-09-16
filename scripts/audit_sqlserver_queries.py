#!/usr/bin/env python3
"""
SQL Server查询权限功能全面审计脚本
测试所有SQL Server查询功能，诊断问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.connection_factory import ConnectionFactory
from app.models.instance import Instance
from app.services.sync_data_manager import SyncDataManager

def test_basic_connection(conn):
    """测试基本连接功能"""
    print("1️⃣ 测试基本连接功能...")
    
    try:
        # 测试1: 基本查询
        print("   - 测试基本查询...")
        result = conn.execute_query("SELECT 1 as test")
        print(f"   ✅ 基本查询成功: {result}")
        
        # 测试2: 获取版本
        print("   - 测试版本查询...")
        result = conn.execute_query("SELECT @@VERSION")
        print(f"   ✅ 版本查询成功: {result[0][0][:100]}...")
        
        # 测试3: 获取当前用户
        print("   - 测试当前用户查询...")
        result = conn.execute_query("SELECT SUSER_NAME() as [current_user]")
        print(f"   ✅ 当前用户: {result[0][0]}")
        
        # 测试4: 获取数据库列表
        print("   - 测试数据库列表查询...")
        result = conn.execute_query("SELECT name FROM sys.databases WHERE state = 0")
        print(f"   ✅ 数据库列表: {[row[0] for row in result]}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 基本连接测试失败: {e}")
        return False

def test_server_queries(conn, username):
    """测试服务器级别查询"""
    print(f"\n2️⃣ 测试服务器级别查询 (用户: {username})...")
    
    try:
        # 测试1: 服务器角色查询
        print("   - 测试服务器角色查询...")
        sql = """
            SELECT r.name
            FROM sys.server_role_members rm
            JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
            JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
            WHERE p.name = %s
        """
        result = conn.execute_query(sql, (username,))
        print(f"   ✅ 服务器角色: {[row[0] for row in result]}")
        
        # 测试2: 服务器权限查询
        print("   - 测试服务器权限查询...")
        sql = """
            SELECT permission_name
            FROM sys.server_permissions
            WHERE grantee_principal_id = (
                SELECT principal_id
                FROM sys.server_principals
                WHERE name = %s
            )
            AND state = 'G'
        """
        result = conn.execute_query(sql, (username,))
        print(f"   ✅ 服务器权限: {[row[0] for row in result]}")
        
        # 测试3: sysadmin检查
        print("   - 测试sysadmin检查...")
        sql = "SELECT IS_SRVROLEMEMBER('sysadmin', %s) as is_sysadmin"
        result = conn.execute_query(sql, (username,))
        is_sysadmin = bool(result[0][0]) if result else False
        print(f"   ✅ 是否为sysadmin: {is_sysadmin}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 服务器级别查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_queries(conn, username):
    """测试数据库级别查询"""
    print(f"\n3️⃣ 测试数据库级别查询 (用户: {username})...")
    
    try:
        # 获取数据库列表
        databases_sql = "SELECT name FROM sys.databases WHERE state = 0"
        databases = conn.execute_query(databases_sql)
        print(f"   - 找到 {len(databases)} 个数据库")
        
        for db_row in databases[:3]:  # 只测试前3个数据库
            db_name = db_row[0]
            print(f"\n   🔍 测试数据库: {db_name}")
            
            try:
                # 测试1: 数据库角色查询
                print(f"     - 测试数据库角色查询...")
                roles_sql = f"""
                    SELECT r.name
                    FROM [{db_name}].sys.database_role_members rm
                    JOIN [{db_name}].sys.database_principals r ON rm.role_principal_id = r.principal_id
                    JOIN [{db_name}].sys.database_principals p ON rm.member_principal_id = p.principal_id
                    WHERE p.name = %s
                """
                result = conn.execute_query(roles_sql, (username,))
                print(f"     ✅ 数据库角色: {[row[0] for row in result]}")
                
                # 测试2: 数据库权限查询
                print(f"     - 测试数据库权限查询...")
                perms_sql = f"""
                    SELECT permission_name
                    FROM [{db_name}].sys.database_permissions
                    WHERE grantee_principal_id = (
                        SELECT principal_id
                        FROM [{db_name}].sys.database_principals
                        WHERE name = %s
                    )
                    AND state = 'G'
                """
                result = conn.execute_query(perms_sql, (username,))
                print(f"     ✅ 数据库权限: {[row[0] for row in result]}")
                
                # 测试3: 检查用户是否在数据库中
                print(f"     - 检查用户是否在数据库中...")
                user_check_sql = f"""
                    SELECT name, type_desc
                    FROM [{db_name}].sys.database_principals
                    WHERE name = %s
                """
                result = conn.execute_query(user_check_sql, (username,))
                if result:
                    print(f"     ✅ 用户在数据库中: {result[0]}")
                else:
                    print(f"     ⚠️  用户不在数据库中")
                
            except Exception as e:
                error_msg = str(e)
                print(f"     ❌ 数据库 {db_name} 查询失败: {error_msg}")
                
                # 详细错误分析
                if "Statement not executed" in error_msg:
                    print(f"       - 错误类型: 语句未执行")
                elif "permission" in error_msg.lower():
                    print(f"       - 错误类型: 权限不足")
                elif "not found" in error_msg.lower():
                    print(f"       - 错误类型: 对象未找到")
                elif "invalid" in error_msg.lower():
                    print(f"       - 错误类型: 无效操作")
                else:
                    print(f"       - 错误类型: 其他错误")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 数据库级别查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sysadmin_queries(conn, username):
    """测试sysadmin特殊查询"""
    print(f"\n4️⃣ 测试sysadmin特殊查询 (用户: {username})...")
    
    try:
        # 获取数据库列表
        databases_sql = "SELECT name FROM sys.databases WHERE state = 0"
        databases = conn.execute_query(databases_sql)
        
        for db_row in databases[:2]:  # 只测试前2个数据库
            db_name = db_row[0]
            print(f"\n   🔍 测试sysadmin查询数据库: {db_name}")
            
            try:
                # 测试1: 查询所有固定数据库角色
                print(f"     - 查询所有固定数据库角色...")
                roles_sql = f"""
                    SELECT r.name
                    FROM [{db_name}].sys.database_principals r
                    WHERE r.type = 'R' AND r.is_fixed_role = 1
                    ORDER BY r.name
                """
                result = conn.execute_query(roles_sql)
                print(f"     ✅ 固定数据库角色: {[row[0] for row in result]}")
                
                # 测试2: 查询所有数据库权限
                print(f"     - 查询所有数据库权限...")
                perms_sql = f"""
                    SELECT DISTINCT permission_name
                    FROM [{db_name}].sys.database_permissions
                    WHERE state = 'G'
                    ORDER BY permission_name
                """
                result = conn.execute_query(perms_sql)
                print(f"     ✅ 数据库权限: {[row[0] for row in result]}")
                
            except Exception as e:
                print(f"     ❌ sysadmin查询失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ sysadmin特殊查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_manager_methods(conn, username):
    """测试同步管理器方法"""
    print(f"\n5️⃣ 测试同步管理器方法 (用户: {username})...")
    
    try:
        sync_manager = SyncDataManager()
        
        # 测试1: 当前用户信息获取
        print("   - 测试当前用户信息获取...")
        current_user_info = sync_manager._get_current_user_info(conn)
        if current_user_info:
            print(f"   ✅ 当前用户信息: {current_user_info}")
        else:
            print("   ❌ 无法获取当前用户信息")
            return False
        
        # 测试2: sysadmin检查
        print("   - 测试sysadmin检查...")
        is_sysadmin = sync_manager._check_sysadmin_user(conn, username)
        print(f"   ✅ 是否为sysadmin: {is_sysadmin}")
        
        # 测试3: 服务器角色
        print("   - 测试服务器角色获取...")
        server_roles = sync_manager._get_sqlserver_server_roles(conn, username)
        print(f"   ✅ 服务器角色: {server_roles}")
        
        # 测试4: 服务器权限
        print("   - 测试服务器权限获取...")
        server_permissions = sync_manager._get_sqlserver_server_permissions(conn, username)
        print(f"   ✅ 服务器权限: {server_permissions}")
        
        # 测试5: 数据库权限（关键测试）
        print("   - 测试数据库权限获取...")
        database_roles, database_permissions = sync_manager._get_sqlserver_database_permissions(conn, username)
        print(f"   ✅ 数据库角色: {len(database_roles)} 个数据库")
        print(f"   ✅ 数据库权限: {len(database_permissions)} 个数据库")
        
        # 显示详细信息
        for db_name, roles in database_roles.items():
            print(f"     - {db_name}: {roles}")
        
        for db_name, perms in database_permissions.items():
            print(f"     - {db_name}: {perms[:3]}{'...' if len(perms) > 3 else ''}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 同步管理器方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def audit_sqlserver_queries(instance_id: int):
    """全面审计SQL Server查询功能"""
    
    instance = Instance.query.get(instance_id)
    if not instance:
        print(f"❌ 实例 {instance_id} 不存在")
        return
    
    print(f"🔍 SQL Server查询权限功能全面审计")
    print(f"   实例: {instance.name}")
    print(f"   主机: {instance.host}:{instance.port}")
    print(f"   凭据: {instance.credential.username if instance.credential else 'None'}")
    print("="*60)
    
    conn = ConnectionFactory.create_connection(instance)
    
    try:
        if not conn.connect():
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        print(f"   驱动类型: {conn.driver_type}")
        
        # 获取当前用户名
        current_user_result = conn.execute_query("SELECT SUSER_NAME() as [current_user]")
        current_user = current_user_result[0][0] if current_user_result else None
        print(f"   当前用户: {current_user}")
        print()
        
        # 执行各项测试
        tests = [
            ("基本连接功能", lambda: test_basic_connection(conn)),
            ("服务器级别查询", lambda: test_server_queries(conn, current_user)),
            ("数据库级别查询", lambda: test_database_queries(conn, current_user)),
            ("sysadmin特殊查询", lambda: test_sysadmin_queries(conn, current_user)),
            ("同步管理器方法", lambda: test_sync_manager_methods(conn, current_user)),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} 测试异常: {e}")
                results.append((test_name, False))
        
        # 输出测试结果摘要
        print("\n" + "="*60)
        print("📊 测试结果摘要:")
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name}: {status}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
        
        if passed == total:
            print("🎉 所有测试通过！SQL Server查询功能正常")
        else:
            print("⚠️  部分测试失败，需要进一步调试")
        
    except Exception as e:
        print(f"❌ 审计过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python audit_sqlserver_queries.py <instance_id>")
        print("示例: python audit_sqlserver_queries.py 1")
        sys.exit(1)
    
    # 创建Flask应用上下文
    app = create_app()
    with app.app_context():
        instance_id = int(sys.argv[1])
        audit_sqlserver_queries(instance_id)
