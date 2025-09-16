#!/usr/bin/env python3
"""
SQL Server简单权限测试脚本
快速诊断sysadmin权限下的数据库权限查询问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.connection_factory import ConnectionFactory
from app.models.database_instance import DatabaseInstance

def test_sqlserver_simple(instance_id: int):
    """简单测试SQL Server权限"""
    
    instance = DatabaseInstance.query.get(instance_id)
    if not instance:
        print(f"❌ 实例 {instance_id} 不存在")
        return
    
    print(f"🔍 测试SQL Server实例: {instance.name}")
    print(f"   主机: {instance.host}:{instance.port}")
    print(f"   凭据: {instance.credential.username if instance.credential else 'None'}")
    print()
    
    conn = ConnectionFactory.create_connection(instance)
    
    try:
        if not conn.connect():
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        
        # 测试1: 基本查询
        print("\n1️⃣ 测试基本查询...")
        try:
            result = conn.execute_query("SELECT @@VERSION")
            print(f"✅ 版本查询成功: {result[0][0][:50]}...")
        except Exception as e:
            print(f"❌ 版本查询失败: {e}")
        
        # 测试2: 服务器级权限
        print("\n2️⃣ 测试服务器级权限...")
        try:
            result = conn.execute_query("SELECT COUNT(*) FROM sys.server_principals")
            print(f"✅ 服务器主体数量: {result[0][0]}")
        except Exception as e:
            print(f"❌ 服务器主体查询失败: {e}")
        
        # 测试3: 数据库列表
        print("\n3️⃣ 测试数据库列表...")
        try:
            result = conn.execute_query("SELECT name FROM sys.databases WHERE state = 0")
            databases = [row[0] for row in result]
            print(f"✅ 在线数据库数量: {len(databases)}")
            for db in databases[:5]:  # 只显示前5个
                print(f"   - {db}")
        except Exception as e:
            print(f"❌ 数据库列表查询失败: {e}")
        
        # 测试4: 跨数据库查询（关键测试）
        print("\n4️⃣ 测试跨数据库查询...")
        if databases:
            test_db = databases[0]
            print(f"   测试数据库: {test_db}")
            
            try:
                # 测试三部分命名法
                sql = f"SELECT COUNT(*) FROM [{test_db}].sys.database_principals"
                result = conn.execute_query(sql)
                print(f"✅ 跨数据库查询成功: {test_db} 主体数量 {result[0][0]}")
            except Exception as e:
                print(f"❌ 跨数据库查询失败: {e}")
                print(f"   错误详情: {str(e)}")
                
                # 尝试其他方法
                print("\n   尝试替代方法...")
                try:
                    # 方法1: 使用USE语句
                    conn.execute_query(f"USE [{test_db}]")
                    result = conn.execute_query("SELECT COUNT(*) FROM sys.database_principals")
                    print(f"✅ USE语句方法成功: {test_db} 主体数量 {result[0][0]}")
                except Exception as e2:
                    print(f"❌ USE语句方法也失败: {e2}")
                
                try:
                    # 方法2: 使用OPENROWSET
                    sql = f"""
                        SELECT COUNT(*) 
                        FROM OPENROWSET('SQLNCLI', 'Server=localhost;Trusted_Connection=yes;',
                            'SELECT COUNT(*) FROM [{test_db}].sys.database_principals')
                    """
                    result = conn.execute_query(sql)
                    print(f"✅ OPENROWSET方法成功: {test_db} 主体数量 {result[0][0]}")
                except Exception as e3:
                    print(f"❌ OPENROWSET方法也失败: {e3}")
        
        # 测试5: 具体用户权限查询
        print("\n5️⃣ 测试用户权限查询...")
        if databases:
            test_db = databases[0]
            try:
                # 获取数据库中的用户
                sql = f"SELECT name FROM [{test_db}].sys.database_principals WHERE type IN ('S', 'U', 'G')"
                users = conn.execute_query(sql)
                
                if users:
                    test_user = users[0][0]
                    print(f"   测试用户: {test_user}")
                    
                    # 查询用户角色
                    sql = f"""
                        SELECT r.name
                        FROM [{test_db}].sys.database_role_members rm
                        JOIN [{test_db}].sys.database_principals r ON rm.role_principal_id = r.principal_id
                        JOIN [{test_db}].sys.database_principals p ON rm.member_principal_id = p.principal_id
                        WHERE p.name = ?
                    """
                    
                    # 使用pymssql的%s占位符
                    sql = sql.replace('?', '%s')
                    
                    roles = conn.execute_query(sql, (test_user,))
                    print(f"✅ 用户 {test_user} 角色数量: {len(roles)}")
                    for role in roles:
                        print(f"   - {role[0]}")
                else:
                    print("⚠️  没有找到用户")
                    
            except Exception as e:
                print(f"❌ 用户权限查询失败: {e}")
                print(f"   错误详情: {str(e)}")
        
        # 测试6: 检查当前用户权限
        print("\n6️⃣ 检查当前用户权限...")
        try:
            # 检查是否为sysadmin
            sql = """
                SELECT 
                    IS_SRVROLEMEMBER('sysadmin') as is_sysadmin,
                    IS_SRVROLEMEMBER('serveradmin') as is_serveradmin,
                    IS_SRVROLEMEMBER('dbcreator') as is_dbcreator
            """
            result = conn.execute_query(sql)
            is_sysadmin, is_serveradmin, is_dbcreator = result[0]
            print(f"✅ 当前用户权限:")
            print(f"   - sysadmin: {bool(is_sysadmin)}")
            print(f"   - serveradmin: {bool(is_serveradmin)}")
            print(f"   - dbcreator: {bool(is_dbcreator)}")
            
        except Exception as e:
            print(f"❌ 权限检查失败: {e}")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_sqlserver_simple.py <instance_id>")
        print("示例: python test_sqlserver_simple.py 1")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    test_sqlserver_simple(instance_id)
