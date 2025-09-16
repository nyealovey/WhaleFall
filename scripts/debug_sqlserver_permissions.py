#!/usr/bin/env python3
"""
SQL Server权限查询诊断脚本
用于排查为什么sysadmin权限下仍然无法获取数据库权限
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.connection_factory import ConnectionFactory
from app.models.database_instance import DatabaseInstance
from app.models.database_credential import DatabaseCredential
from app.utils.logger import get_logger

logger = get_logger(__name__)

def test_sqlserver_permissions(instance_id: int):
    """测试SQL Server权限查询"""
    
    # 获取实例信息
    instance = DatabaseInstance.query.get(instance_id)
    if not instance:
        print(f"❌ 实例 {instance_id} 不存在")
        return
    
    print(f"🔍 开始诊断SQL Server实例: {instance.name}")
    print(f"   主机: {instance.host}:{instance.port}")
    print(f"   数据库类型: {instance.db_type}")
    print(f"   凭据: {instance.credential.username if instance.credential else 'None'}")
    print()
    
    # 创建连接
    conn = ConnectionFactory.create_connection(instance)
    
    try:
        # 测试连接
        print("1️⃣ 测试基本连接...")
        if not conn.connect():
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        
        # 测试服务器级权限
        print("\n2️⃣ 测试服务器级权限...")
        test_server_permissions(conn)
        
        # 测试数据库列表查询
        print("\n3️⃣ 测试数据库列表查询...")
        test_database_list(conn)
        
        # 测试跨数据库查询
        print("\n4️⃣ 测试跨数据库查询...")
        test_cross_database_query(conn)
        
        # 测试具体用户权限查询
        print("\n5️⃣ 测试用户权限查询...")
        test_user_permissions(conn)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

def test_server_permissions(conn):
    """测试服务器级权限"""
    try:
        # 测试服务器主体查询
        sql = "SELECT COUNT(*) FROM sys.server_principals"
        result = conn.execute_query(sql)
        print(f"✅ 服务器主体数量: {result[0][0]}")
        
        # 测试服务器权限查询
        sql = "SELECT COUNT(*) FROM sys.server_permissions"
        result = conn.execute_query(sql)
        print(f"✅ 服务器权限数量: {result[0][0]}")
        
    except Exception as e:
        print(f"❌ 服务器级权限测试失败: {e}")

def test_database_list(conn):
    """测试数据库列表查询"""
    try:
        sql = "SELECT name, state_desc FROM sys.databases WHERE state = 0"
        databases = conn.execute_query(sql)
        print(f"✅ 在线数据库数量: {len(databases)}")
        for db in databases:
            print(f"   - {db[0]} ({db[1]})")
            
    except Exception as e:
        print(f"❌ 数据库列表查询失败: {e}")

def test_cross_database_query(conn):
    """测试跨数据库查询"""
    try:
        # 获取数据库列表
        sql = "SELECT name FROM sys.databases WHERE state = 0 AND name NOT IN ('tempdb', 'model', 'msdb')"
        databases = conn.execute_query(sql)
        
        if not databases:
            print("⚠️  没有找到可测试的数据库")
            return
            
        # 测试第一个数据库的跨数据库查询
        db_name = databases[0][0]
        print(f"   测试数据库: {db_name}")
        
        # 测试三部分命名法
        sql = f"SELECT COUNT(*) FROM [{db_name}].sys.database_principals"
        result = conn.execute_query(sql)
        print(f"✅ 数据库 {db_name} 主体数量: {result[0][0]}")
        
        # 测试数据库权限查询
        sql = f"SELECT COUNT(*) FROM [{db_name}].sys.database_permissions"
        result = conn.execute_query(sql)
        print(f"✅ 数据库 {db_name} 权限数量: {result[0][0]}")
        
    except Exception as e:
        print(f"❌ 跨数据库查询失败: {e}")
        import traceback
        traceback.print_exc()

def test_user_permissions(conn):
    """测试用户权限查询"""
    try:
        # 获取数据库列表
        sql = "SELECT name FROM sys.databases WHERE state = 0 AND name NOT IN ('tempdb', 'model', 'msdb')"
        databases = conn.execute_query(sql)
        
        if not databases:
            print("⚠️  没有找到可测试的数据库")
            return
            
        # 测试第一个数据库的用户权限查询
        db_name = databases[0][0]
        print(f"   测试数据库: {db_name}")
        
        # 获取数据库中的用户
        sql = f"""
            SELECT name, type_desc 
            FROM [{db_name}].sys.database_principals 
            WHERE type IN ('S', 'U', 'G')
            ORDER BY name
        """
        users = conn.execute_query(sql)
        
        if not users:
            print(f"⚠️  数据库 {db_name} 中没有找到用户")
            return
            
        print(f"✅ 数据库 {db_name} 用户数量: {len(users)}")
        
        # 测试第一个用户的权限查询
        test_user = users[0][0]
        print(f"   测试用户: {test_user}")
        
        # 查询用户角色
        sql = f"""
            SELECT r.name
            FROM [{db_name}].sys.database_role_members rm
            JOIN [{db_name}].sys.database_principals r ON rm.role_principal_id = r.principal_id
            JOIN [{db_name}].sys.database_principals p ON rm.member_principal_id = p.principal_id
            WHERE p.name = ?
        """
        
        # 根据驱动类型使用不同的参数
        if hasattr(conn, 'driver_type') and conn.driver_type == 'pymssql':
            sql = sql.replace('?', '%s')
        
        roles = conn.execute_query(sql, (test_user,))
        print(f"✅ 用户 {test_user} 角色数量: {len(roles)}")
        for role in roles:
            print(f"   - {role[0]}")
        
        # 查询用户权限
        sql = f"""
            SELECT permission_name
            FROM [{db_name}].sys.database_permissions
            WHERE grantee_principal_id = (
                SELECT principal_id
                FROM [{db_name}].sys.database_principals
                WHERE name = ?
            )
            AND state = 'G'
        """
        
        # 根据驱动类型使用不同的参数
        if hasattr(conn, 'driver_type') and conn.driver_type == 'pymssql':
            sql = sql.replace('?', '%s')
        
        permissions = conn.execute_query(sql, (test_user,))
        print(f"✅ 用户 {test_user} 权限数量: {len(permissions)}")
        for perm in permissions:
            print(f"   - {perm[0]}")
            
    except Exception as e:
        print(f"❌ 用户权限查询失败: {e}")
        import traceback
        traceback.print_exc()

def test_specific_user(conn, username: str):
    """测试特定用户的权限查询"""
    print(f"\n6️⃣ 测试特定用户权限查询: {username}")
    
    try:
        # 获取数据库列表
        sql = "SELECT name FROM sys.databases WHERE state = 0 AND name NOT IN ('tempdb', 'model', 'msdb')"
        databases = conn.execute_query(sql)
        
        if not databases:
            print("⚠️  没有找到可测试的数据库")
            return
            
        for db_name, in databases:
            print(f"\n   测试数据库: {db_name}")
            
            try:
                # 检查用户是否存在
                sql = f"""
                    SELECT name, type_desc 
                    FROM [{db_name}].sys.database_principals 
                    WHERE name = ?
                """
                
                if hasattr(conn, 'driver_type') and conn.driver_type == 'pymssql':
                    sql = sql.replace('?', '%s')
                
                users = conn.execute_query(sql, (username,))
                
                if not users:
                    print(f"   ⚠️  用户 {username} 在数据库 {db_name} 中不存在")
                    continue
                
                print(f"   ✅ 用户 {username} 存在，类型: {users[0][1]}")
                
                # 查询用户角色
                sql = f"""
                    SELECT r.name
                    FROM [{db_name}].sys.database_role_members rm
                    JOIN [{db_name}].sys.database_principals r ON rm.role_principal_id = r.principal_id
                    JOIN [{db_name}].sys.database_principals p ON rm.member_principal_id = p.principal_id
                    WHERE p.name = ?
                """
                
                if hasattr(conn, 'driver_type') and conn.driver_type == 'pymssql':
                    sql = sql.replace('?', '%s')
                
                roles = conn.execute_query(sql, (username,))
                print(f"   ✅ 角色数量: {len(roles)}")
                for role in roles:
                    print(f"      - {role[0]}")
                
                # 查询用户权限
                sql = f"""
                    SELECT permission_name
                    FROM [{db_name}].sys.database_permissions
                    WHERE grantee_principal_id = (
                        SELECT principal_id
                        FROM [{db_name}].sys.database_principals
                        WHERE name = ?
                    )
                    AND state = 'G'
                """
                
                if hasattr(conn, 'driver_type') and conn.driver_type == 'pymssql':
                    sql = sql.replace('?', '%s')
                
                permissions = conn.execute_query(sql, (username,))
                print(f"   ✅ 权限数量: {len(permissions)}")
                for perm in permissions:
                    print(f"      - {perm[0]}")
                    
            except Exception as e:
                print(f"   ❌ 数据库 {db_name} 查询失败: {e}")
                
    except Exception as e:
        print(f"❌ 特定用户权限查询失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_sqlserver_permissions.py <instance_id> [username]")
        print("示例: python debug_sqlserver_permissions.py 1")
        print("示例: python debug_sqlserver_permissions.py 1 sa")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    username = sys.argv[2] if len(sys.argv) > 2 else None
    
    test_sqlserver_permissions(instance_id)
    
    if username:
        # 重新连接测试特定用户
        instance = DatabaseInstance.query.get(instance_id)
        conn = ConnectionFactory.create_connection(instance)
        if conn.connect():
            test_specific_user(conn, username)
            conn.disconnect()
