#!/usr/bin/env python3
"""
SQL Server当前用户权限测试脚本
测试使用当前连接用户凭据查询权限
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.connection_factory import ConnectionFactory
from app.models.database_instance import DatabaseInstance
from app.services.sync_data_manager import SyncDataManager

def test_current_user_permissions(instance_id: int):
    """测试当前用户的权限查询"""
    
    instance = DatabaseInstance.query.get(instance_id)
    if not instance:
        print(f"❌ 实例 {instance_id} 不存在")
        return
    
    print(f"🔍 测试SQL Server实例 (当前用户权限): {instance.name}")
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
        
        # 测试1: 获取当前用户信息
        print("\n1️⃣ 获取当前用户信息...")
        try:
            sync_manager = SyncDataManager()
            current_user_info = sync_manager._get_current_user_info(conn)
            
            if current_user_info:
                print(f"✅ 当前用户信息:")
                print(f"   - 用户名: {current_user_info['username']}")
                print(f"   - 登录类型: {current_user_info['login_type']}")
                print(f"   - 是否禁用: {current_user_info['is_disabled']}")
                print(f"   - 类型: {current_user_info['type']}")
            else:
                print("❌ 无法获取当前用户信息")
                return
                
        except Exception as e:
            print(f"❌ 获取当前用户信息失败: {e}")
            return
        
        # 测试2: 检查sysadmin权限
        print("\n2️⃣ 检查sysadmin权限...")
        try:
            is_sysadmin = sync_manager._check_sysadmin_user(conn, current_user_info['username'])
            print(f"✅ 是否为sysadmin: {is_sysadmin}")
        except Exception as e:
            print(f"❌ 检查sysadmin权限失败: {e}")
        
        # 测试3: 获取服务器角色
        print("\n3️⃣ 获取服务器角色...")
        try:
            server_roles = sync_manager._get_sqlserver_server_roles(conn, current_user_info['username'])
            print(f"✅ 服务器角色数量: {len(server_roles)}")
            for role in server_roles:
                print(f"   - {role}")
        except Exception as e:
            print(f"❌ 获取服务器角色失败: {e}")
        
        # 测试4: 获取服务器权限
        print("\n4️⃣ 获取服务器权限...")
        try:
            server_permissions = sync_manager._get_sqlserver_server_permissions(conn, current_user_info['username'])
            print(f"✅ 服务器权限数量: {len(server_permissions)}")
            for perm in server_permissions:
                print(f"   - {perm}")
        except Exception as e:
            print(f"❌ 获取服务器权限失败: {e}")
        
        # 测试5: 获取数据库权限（关键测试）
        print("\n5️⃣ 获取数据库权限...")
        try:
            database_roles, database_permissions = sync_manager._get_sqlserver_database_permissions(conn, current_user_info['username'])
            
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
            print(f"❌ 获取数据库权限失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 测试6: 使用完整的账户同步方法
        print("\n6️⃣ 使用完整的账户同步方法...")
        try:
            accounts = sync_manager._get_sqlserver_accounts(conn)
            print(f"✅ 账户同步结果: {len(accounts)} 个账户")
            
            if accounts:
                account = accounts[0]
                print(f"   - 用户名: {account['username']}")
                print(f"   - 是否超级用户: {account['is_superuser']}")
                print(f"   - 服务器角色: {len(account['permissions']['server_roles'])} 个")
                print(f"   - 服务器权限: {len(account['permissions']['server_permissions'])} 个")
                print(f"   - 数据库角色: {len(account['permissions']['database_roles'])} 个数据库")
                print(f"   - 数据库权限: {len(account['permissions']['database_permissions'])} 个数据库")
                
                # 显示数据库角色详情
                if account['permissions']['database_roles']:
                    print("   数据库角色详情:")
                    for db_name, roles in account['permissions']['database_roles'].items():
                        print(f"     - {db_name}: {', '.join(roles)}")
                
                # 显示数据库权限详情
                if account['permissions']['database_permissions']:
                    print("   数据库权限详情:")
                    for db_name, perms in account['permissions']['database_permissions'].items():
                        print(f"     - {db_name}: {', '.join(perms[:3])}{'...' if len(perms) > 3 else ''}")
                        
        except Exception as e:
            print(f"❌ 账户同步失败: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*50)
        print("🎉 当前用户权限测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_current_user_permissions.py <instance_id>")
        print("示例: python test_current_user_permissions.py 1")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    test_current_user_permissions(instance_id)
