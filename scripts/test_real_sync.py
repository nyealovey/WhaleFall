#!/usr/bin/env python3
"""
测试真实的同步过程并检查数据库中的数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.connection_factory import ConnectionFactory
from app.models.instance import Instance
from app.services.sync_data_manager import SyncDataManager
from app.models.current_account_sync_data import CurrentAccountSyncData

def test_real_sync(instance_id: int):
    """测试真实的同步过程"""
    
    app = create_app()
    with app.app_context():
        instance = Instance.query.get(instance_id)
        if not instance:
            print(f"❌ 实例 {instance_id} 不存在")
            return
        
        print(f"🔍 测试真实同步过程")
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
            
            # 执行真实的同步过程
            print("\n1️⃣ 执行真实同步过程...")
            try:
                session_id = "test_session_123"
                result = sync_manager.sync_sqlserver_accounts(instance, conn, session_id)
                print(f"✅ 同步完成:")
                print(f"   同步账户数: {result['synced_count']}")
                print(f"   新增账户数: {result['added_count']}")
                print(f"   修改账户数: {result['modified_count']}")
                print(f"   删除账户数: {result['removed_count']}")
                
            except Exception as e:
                print(f"❌ 同步失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 检查数据库中的数据
            print(f"\n2️⃣ 检查数据库中的数据...")
            try:
                # 查询最新的账户数据
                account = CurrentAccountSyncData.query.filter_by(
                    instance_id=instance_id,
                    db_type="sqlserver",
                    username="monitor"
                ).order_by(CurrentAccountSyncData.last_sync_time.desc()).first()
                
                if account:
                    print(f"✅ 找到账户数据:")
                    print(f"   用户名: {account.username}")
                    print(f"   是否超级用户: {account.is_superuser}")
                    print(f"   服务器角色: {account.server_roles}")
                    print(f"   服务器权限: {account.server_permissions}")
                    print(f"   数据库角色数量: {len(account.database_roles) if account.database_roles else 0}")
                    print(f"   数据库权限数量: {len(account.database_permissions) if account.database_permissions else 0}")
                    
                    # 显示数据库角色详情
                    if account.database_roles:
                        print(f"\n📊 数据库角色详情:")
                        for db_name, roles in account.database_roles.items():
                            print(f"   - {db_name}: {', '.join(roles)}")
                    else:
                        print(f"\n⚠️  数据库中没有角色信息")
                    
                    # 显示数据库权限详情
                    if account.database_permissions:
                        print(f"\n📊 数据库权限详情:")
                        for db_name, perms in account.database_permissions.items():
                            print(f"   - {db_name}: {', '.join(perms[:3])}{'...' if len(perms) > 3 else ''}")
                    else:
                        print(f"\n⚠️  数据库中没有权限信息")
                        
                else:
                    print(f"❌ 没有找到账户数据")
                    
            except Exception as e:
                print(f"❌ 查询数据库失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "="*60)
            print("🎉 真实同步测试完成！")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_real_sync.py <instance_id>")
        print("示例: python test_real_sync.py 14")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    test_real_sync(instance_id)
