#!/usr/bin/env python3
"""
测试修复后的SQL Server同步功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.connection_factory import ConnectionFactory
from app.models.instance import Instance
from app.services.sync_data_manager import SyncDataManager
from app.models.current_account_sync_data import CurrentAccountSyncData

def test_fixed_sync(instance_id: int):
    """测试修复后的同步功能"""
    
    app = create_app()
    with app.app_context():
        instance = Instance.query.get(instance_id)
        if not instance:
            print(f"❌ 实例 {instance_id} 不存在")
            return
        
        print(f"🔍 测试修复后的SQL Server同步功能")
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
            
            # 测试获取所有账户
            print("\n1️⃣ 测试获取所有SQL Server账户...")
            try:
                accounts = sync_manager._get_sqlserver_accounts(conn)
                print(f"✅ 获取到 {len(accounts)} 个账户")
                
                for i, account in enumerate(accounts[:5]):  # 只显示前5个
                    print(f"   {i+1}. {account['username']} (超级用户: {account['is_superuser']})")
                
                if len(accounts) > 5:
                    print(f"   ... 还有 {len(accounts) - 5} 个账户")
                    
            except Exception as e:
                print(f"❌ 获取账户失败: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # 执行同步
            print(f"\n2️⃣ 执行同步过程...")
            try:
                session_id = "test_fixed_sync_123"
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
            
            # 检查数据库中的账户状态
            print(f"\n3️⃣ 检查数据库中的账户状态...")
            try:
                # 查询所有SQL Server账户
                all_accounts = CurrentAccountSyncData.query.filter_by(
                    instance_id=instance_id,
                    db_type="sqlserver"
                ).order_by(CurrentAccountSyncData.last_sync_time.desc()).all()
                
                print(f"✅ 数据库中共有 {len(all_accounts)} 个SQL Server账户")
                
                # 统计状态
                active_count = sum(1 for acc in all_accounts if not acc.is_deleted)
                deleted_count = sum(1 for acc in all_accounts if acc.is_deleted)
                
                print(f"   正常账户: {active_count} 个")
                print(f"   已删除账户: {deleted_count} 个")
                
                # 显示前几个账户的详情
                print(f"\n📋 账户详情 (前10个):")
                for i, account in enumerate(all_accounts[:10]):
                    status = "已删除" if account.is_deleted else "正常"
                    superuser = "是" if account.is_superuser else "否"
                    print(f"   {i+1}. {account.username} - 状态: {status}, 超级用户: {superuser}")
                
                if len(all_accounts) > 10:
                    print(f"   ... 还有 {len(all_accounts) - 10} 个账户")
                    
            except Exception as e:
                print(f"❌ 查询数据库失败: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n" + "="*60)
            print("🎉 修复后的同步测试完成！")
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_fixed_sync.py <instance_id>")
        print("示例: python test_fixed_sync.py 14")
        sys.exit(1)
    
    instance_id = int(sys.argv[1])
    test_fixed_sync(instance_id)
