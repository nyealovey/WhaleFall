#!/usr/bin/env python3
"""
SQL Server sysadmin权限测试脚本
专门测试sysadmin用户的数据库权限查询
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.connection_factory import ConnectionFactory
from app.models.database_instance import DatabaseInstance
from app.services.sync_data_manager import SyncDataManager

def test_sysadmin_permissions(instance_id: int):
    """测试sysadmin用户的权限查询"""
    
    instance = DatabaseInstance.query.get(instance_id)
    if not instance:
        print(f"❌ 实例 {instance_id} 不存在")
        return
    
    print(f"🔍 测试SQL Server实例 (sysadmin权限): {instance.name}")
    print(f"   主机: {instance.host}:{instance.port}")
    print(f"   凭据: {instance.credential.username if instance.credential else 'None'}")
    print()
    
    conn = ConnectionFactory.create_connection(instance)
    
    try:
        if not conn.connect():
            print("❌ 连接失败")
            return
        print("✅ 连接成功")
        print(f"   驱动类型: {conn.driver_type}")
        
        # 测试1: 检查sysadmin权限
        print("\n1️⃣ 检查sysadmin权限...")
        try:
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
            
            if not is_sysadmin:
                print("⚠️  当前用户不是sysadmin，将使用普通权限查询方式")
            else:
                print("✅ 当前用户是sysadmin，将使用特殊权限查询方式")
                
        except Exception as e:
            print(f"❌ 权限检查失败: {e}")
        
        # 测试2: 获取数据库列表
        print("\n2️⃣ 获取数据库列表...")
        try:
            sql = "SELECT name FROM sys.databases WHERE state = 0"
            databases = conn.execute_query(sql)
            db_names = [row[0] for row in databases]
            print(f"✅ 在线数据库数量: {len(db_names)}")
            for db in db_names[:5]:  # 只显示前5个
                print(f"   - {db}")
        except Exception as e:
            print(f"❌ 数据库列表查询失败: {e}")
            return
        
        # 测试3: 使用SyncDataManager测试权限查询
        print("\n3️⃣ 使用SyncDataManager测试权限查询...")
        try:
            sync_manager = SyncDataManager()
            username = instance.credential.username if instance.credential else "monitor"
            
            # 测试数据库权限查询
            database_roles, database_permissions = sync_manager._get_sqlserver_database_permissions(conn, username)
            
            print(f"✅ 数据库角色查询结果:")
            if database_roles:
                for db_name, roles in database_roles.items():
                    print(f"   - {db_name}: {len(roles)} 个角色")
                    for role in roles[:3]:  # 只显示前3个角色
                        print(f"     * {role}")
                    if len(roles) > 3:
                        print(f"     ... 还有 {len(roles) - 3} 个角色")
            else:
                print("   - 没有找到数据库角色")
            
            print(f"✅ 数据库权限查询结果:")
            if database_permissions:
                for db_name, perms in database_permissions.items():
                    print(f"   - {db_name}: {len(perms)} 个权限")
                    for perm in perms[:3]:  # 只显示前3个权限
                        print(f"     * {perm}")
                    if len(perms) > 3:
                        print(f"     ... 还有 {len(perms) - 3} 个权限")
            else:
                print("   - 没有找到数据库权限")
                
        except Exception as e:
            print(f"❌ SyncDataManager权限查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试4: 直接测试跨数据库查询
        print("\n4️⃣ 直接测试跨数据库查询...")
        if db_names:
            test_db = db_names[0]
            print(f"   测试数据库: {test_db}")
            
            try:
                # 测试查询数据库角色
                sql = f"""
                    SELECT r.name
                    FROM [{test_db}].sys.database_principals r
                    WHERE r.type = 'R' AND r.is_fixed_role = 1
                    ORDER BY r.name
                """
                roles = conn.execute_query(sql)
                print(f"✅ 数据库 {test_db} 固定角色数量: {len(roles)}")
                for role in roles[:5]:  # 只显示前5个
                    print(f"   - {role[0]}")
                
                # 测试查询数据库权限
                sql = f"""
                    SELECT DISTINCT permission_name
                    FROM [{test_db}].sys.database_permissions
                    WHERE state = 'G'
                    ORDER BY permission_name
                """
                permissions = conn.execute_query(sql)
                print(f"✅ 数据库 {test_db} 权限数量: {len(permissions)}")
                for perm in permissions[:5]:  # 只显示前5个
                    print(f"   - {perm[0]}")
                    
            except Exception as e:
                print(f"❌ 跨数据库查询失败: {e}")
                print(f"   错误详情: {str(e)}")
        
        print("\n" + "="*50)
        print("🎉 sysadmin权限测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_sysadmin_permissions.py <instance_id>")
        print("示例: python test_sysadmin_permissions.py 1")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    test_sysadmin_permissions(instance_id)
