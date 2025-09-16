#!/usr/bin/env python3
"""
强制更新monitor用户的数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.connection_factory import ConnectionFactory
from app.models.instance import Instance
from app.services.sync_data_manager import SyncDataManager
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.utils.timezone import now

def force_update_monitor(instance_id: int):
    """强制更新monitor用户的数据"""
    
    app = create_app()
    with app.app_context():
        instance = Instance.query.get(instance_id)
        if not instance:
            print(f"❌ 实例 {instance_id} 不存在")
            return
        
        print(f"🔍 强制更新monitor用户数据")
        print(f"   实例: {instance.name}")
        print(f"   主机: {instance.host}:{instance.port}")
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
            
            # 1. 获取monitor用户的最新权限数据
            print("\n1️⃣ 获取monitor用户的最新权限数据...")
            try:
                accounts = sync_manager._get_sqlserver_accounts(conn)
                monitor_account = None
                for account in accounts:
                    if account['username'] == 'monitor':
                        monitor_account = account
                        break
                
                if not monitor_account:
                    print("❌ 没有找到monitor用户")
                    return
                
                print(f"✅ 获取到monitor用户权限数据:")
                print(f"   数据库角色数量: {len(monitor_account['permissions']['database_roles'])}")
                print(f"   数据库权限数量: {len(monitor_account['permissions']['database_permissions'])}")
                
            except Exception as e:
                print(f"❌ 获取权限数据失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 2. 查找数据库中的monitor用户记录
            print(f"\n2️⃣ 查找数据库中的monitor用户记录...")
            try:
                account = CurrentAccountSyncData.query.filter_by(
                    instance_id=instance_id,
                    db_type="sqlserver",
                    username="monitor"
                ).order_by(CurrentAccountSyncData.last_sync_time.desc()).first()
                
                if account:
                    print(f"✅ 找到monitor用户记录:")
                    print(f"   ID: {account.id}")
                    print(f"   当前数据库角色数量: {len(account.database_roles) if account.database_roles else 0}")
                    print(f"   当前数据库权限数量: {len(account.database_permissions) if account.database_permissions else 0}")
                else:
                    print("❌ 没有找到monitor用户记录")
                    return
                    
            except Exception as e:
                print(f"❌ 查询数据库失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 3. 强制更新数据
            print(f"\n3️⃣ 强制更新monitor用户数据...")
            try:
                # 直接更新数据库记录
                account.server_roles = monitor_account['permissions']['server_roles']
                account.server_permissions = monitor_account['permissions']['server_permissions']
                account.database_roles = monitor_account['permissions']['database_roles']
                account.database_permissions = monitor_account['permissions']['database_permissions']
                account.type_specific = monitor_account['permissions']['type_specific']
                account.is_superuser = monitor_account['is_superuser']
                account.is_deleted = False
                account.deleted_time = None
                account.last_change_type = "modify_privilege"
                account.last_change_time = now()
                account.last_sync_time = now()
                
                # 提交更改
                from app import db
                db.session.commit()
                
                print(f"✅ 数据更新成功")
                
            except Exception as e:
                print(f"❌ 数据更新失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 4. 验证更新结果
            print(f"\n4️⃣ 验证更新结果...")
            try:
                # 重新查询数据
                updated_account = CurrentAccountSyncData.query.filter_by(
                    instance_id=instance_id,
                    db_type="sqlserver",
                    username="monitor"
                ).order_by(CurrentAccountSyncData.last_sync_time.desc()).first()
                
                if updated_account:
                    print(f"✅ 更新后的数据:")
                    print(f"   数据库角色数量: {len(updated_account.database_roles) if updated_account.database_roles else 0}")
                    print(f"   数据库权限数量: {len(updated_account.database_permissions) if updated_account.database_permissions else 0}")
                    
                    if updated_account.database_roles:
                        print(f"   数据库角色详情 (前3个):")
                        for i, (db_name, roles) in enumerate(updated_account.database_roles.items()):
                            if i >= 3:
                                break
                            print(f"     - {db_name}: {roles}")
                    
                    if updated_account.database_permissions:
                        print(f"   数据库权限详情 (前3个):")
                        for i, (db_name, perms) in enumerate(updated_account.database_permissions.items()):
                            if i >= 3:
                                break
                            print(f"     - {db_name}: {perms[:3]}{'...' if len(perms) > 3 else ''}")
                else:
                    print("❌ 没有找到更新后的记录")
                    
            except Exception as e:
                print(f"❌ 验证失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "="*60)
            print("🎉 强制更新monitor用户数据完成！")
            
        except Exception as e:
            print(f"❌ 更新过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python force_update_monitor.py <instance_id>")
        print("示例: python force_update_monitor.py 14")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    force_update_monitor(instance_id)
