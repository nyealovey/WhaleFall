#!/usr/bin/env python3
"""
调试monitor用户的权限查询
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.connection_factory import ConnectionFactory
from app.models.instance import Instance
from app.services.sync_data_manager import SyncDataManager

def debug_monitor_permissions(instance_id: int):
    """调试monitor用户的权限查询"""
    
    app = create_app()
    with app.app_context():
        instance = Instance.query.get(instance_id)
        if not instance:
            print(f"❌ 实例 {instance_id} 不存在")
            return
        
        print(f"🔍 调试monitor用户权限查询")
        print(f"   实例: {instance.name}")
        print(f"   主机: {instance.host}:{instance.port}")
        print(f"   凭据: {instance.credential.username if instance.credential else 'None'}")
        print("="*60)
        
        # 创建连接
        conn = ConnectionFactory.create_connection(instance)
        
        try:
            if not conn.connect():
                print("❌ 连接失败")
                return
            print("✅ 连接成功")
            
            # 创建同步管理器
            sync_manager = SyncDataManager()
            
            # 1. 检查monitor用户是否在查询结果中
            print("\n1️⃣ 检查monitor用户是否在查询结果中...")
            try:
                accounts = sync_manager._get_sqlserver_accounts(conn)
                monitor_account = None
                for account in accounts:
                    if account['username'] == 'monitor':
                        monitor_account = account
                        break
                
                if monitor_account:
                    print("✅ 找到monitor用户")
                    print(f"   用户名: {monitor_account['username']}")
                    print(f"   是否超级用户: {monitor_account['is_superuser']}")
                    print(f"   服务器角色: {monitor_account['permissions']['server_roles']}")
                    print(f"   服务器权限: {monitor_account['permissions']['server_permissions']}")
                    print(f"   数据库角色数量: {len(monitor_account['permissions']['database_roles'])}")
                    print(f"   数据库权限数量: {len(monitor_account['permissions']['database_permissions'])}")
                else:
                    print("❌ 没有找到monitor用户")
                    print("   查询到的用户:")
                    for account in accounts:
                        print(f"     - {account['username']}")
                    return
                    
            except Exception as e:
                print(f"❌ 查询账户失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 2. 单独测试monitor用户的权限查询
            print(f"\n2️⃣ 单独测试monitor用户的权限查询...")
            try:
                username = 'monitor'
                
                # 检查sysadmin
                print(f"   - 检查sysadmin权限...")
                is_sysadmin = sync_manager._check_sysadmin_user(conn, username)
                print(f"     结果: {is_sysadmin}")
                
                # 获取数据库权限
                print(f"   - 获取数据库权限...")
                database_roles, database_permissions = sync_manager._get_sqlserver_database_permissions(conn, username)
                print(f"     数据库角色数量: {len(database_roles)}")
                print(f"     数据库权限数量: {len(database_permissions)}")
                
                if database_roles:
                    print(f"     数据库角色详情:")
                    for db_name, roles in database_roles.items():
                        print(f"       - {db_name}: {roles}")
                else:
                    print(f"     ❌ 没有数据库角色")
                
                if database_permissions:
                    print(f"     数据库权限详情:")
                    for db_name, perms in database_permissions.items():
                        print(f"       - {db_name}: {perms[:3]}{'...' if len(perms) > 3 else ''}")
                else:
                    print(f"     ❌ 没有数据库权限")
                    
            except Exception as e:
                print(f"❌ 权限查询失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 3. 测试特定数据库的权限查询
            print(f"\n3️⃣ 测试特定数据库的权限查询...")
            try:
                # 测试BrandResourceManages数据库（从SSMS截图看到的）
                db_name = 'BrandResourceManages'
                print(f"   测试数据库: {db_name}")
                
                # 检查用户是否在数据库中
                user_check_sql = f"""
                    SELECT name, type_desc
                    FROM [{db_name}].sys.database_principals
                    WHERE name = %s
                """
                result = conn.execute_query(user_check_sql, ('monitor',))
                if result:
                    print(f"   ✅ 用户在数据库中: {result[0]}")
                else:
                    print(f"   ❌ 用户不在数据库中")
                
                # 查询数据库角色
                roles_sql = f"""
                    SELECT r.name
                    FROM [{db_name}].sys.database_role_members rm
                    JOIN [{db_name}].sys.database_principals r ON rm.role_principal_id = r.principal_id
                    JOIN [{db_name}].sys.database_principals p ON rm.member_principal_id = p.principal_id
                    WHERE p.name = %s
                """
                result = conn.execute_query(roles_sql, ('monitor',))
                if result:
                    print(f"   ✅ 数据库角色: {[row[0] for row in result]}")
                else:
                    print(f"   ❌ 没有数据库角色")
                
                # 查询数据库权限
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
                result = conn.execute_query(perms_sql, ('monitor',))
                if result:
                    print(f"   ✅ 数据库权限: {[row[0] for row in result]}")
                else:
                    print(f"   ❌ 没有数据库权限")
                    
            except Exception as e:
                print(f"❌ 特定数据库查询失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "="*60)
            print("🎉 monitor用户权限调试完成！")
            
        except Exception as e:
            print(f"❌ 调试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python debug_monitor_permissions.py <instance_id>")
        print("示例: python debug_monitor_permissions.py 14")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    debug_monitor_permissions(instance_id)
