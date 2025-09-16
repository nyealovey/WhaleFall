#!/usr/bin/env python3
"""
测试新创建的SQL Server实例的权限同步功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.instance import Instance
from app.services.connection_factory import ConnectionFactory
from app.services.sync_data_manager import SyncDataManager
from app.utils.timezone import now

def test_new_sqlserver_instance():
    """测试新SQL Server实例的权限同步"""
    app = create_app()
    
    with app.app_context():
        # 获取新实例
        instance = Instance.query.get(16)
        if not instance:
            print("❌ 没有找到实例ID 16")
            return
        
        print(f"测试实例: {instance.name} (ID: {instance.id})")
        print(f"类型: {instance.db_type}")
        print(f"主机: {instance.host}:{instance.port}")
        print(f"凭据ID: {instance.credential_id}")
        
        # 创建连接
        print("\n1. 创建数据库连接...")
        conn_factory = ConnectionFactory.create_connection(instance)
        if not conn_factory or not conn_factory.connect():
            print("❌ 连接失败")
            return
        
        print("✅ 连接成功")
        
        # 测试基本查询
        print("\n2. 测试基本查询...")
        try:
            version = conn_factory.get_version()
            print(f"数据库版本: {version}")
        except Exception as e:
            print(f"❌ 版本查询失败: {e}")
            return
        
        # 测试当前用户
        print("\n3. 测试当前用户...")
        try:
            sql = "SELECT SUSER_NAME() as [current_user]"
            result = conn_factory.execute_query(sql)
            current_user = result[0][0] if result else None
            print(f"当前用户: {current_user}")
        except Exception as e:
            print(f"❌ 用户查询失败: {e}")
            return
        
        # 测试sysadmin检查
        print("\n4. 测试sysadmin权限检查...")
        try:
            sql = "SELECT IS_SRVROLEMEMBER('sysadmin', %s) as is_sysadmin"
            result = conn_factory.execute_query(sql, (current_user,))
            is_sysadmin = bool(result[0][0]) if result else False
            print(f"是否为sysadmin: {is_sysadmin}")
        except Exception as e:
            print(f"❌ sysadmin检查失败: {e}")
            return
        
        # 测试数据库列表
        print("\n5. 测试数据库列表...")
        try:
            sql = "SELECT name FROM sys.databases WHERE state = 0"
            databases = conn_factory.execute_query(sql)
            print(f"找到 {len(databases)} 个数据库:")
            for db_row in databases[:5]:  # 只显示前5个
                print(f"  - {db_row[0]}")
            if len(databases) > 5:
                print(f"  ... 还有 {len(databases) - 5} 个数据库")
        except Exception as e:
            print(f"❌ 数据库列表查询失败: {e}")
            return
        
        # 测试权限同步
        print("\n6. 测试权限同步...")
        try:
            sync_manager = SyncDataManager()
            session_id = f"test_{now().strftime('%Y%m%d_%H%M%S')}"
            
            result = sync_manager.sync_sqlserver_accounts(instance, conn_factory, session_id)
            
            if result.get('success'):
                print("✅ 同步成功:")
                print(f"  新增账户: {result.get('added', 0)}")
                print(f"  更新账户: {result.get('updated', 0)}")
                print(f"  删除账户: {result.get('deleted', 0)}")
                print(f"  错误数量: {result.get('errors', 0)}")
                
                # 检查monitor用户的权限
                print("\n7. 检查monitor用户权限...")
                from app.models.current_account_sync_data import CurrentAccountSyncData
                
                monitor_account = CurrentAccountSyncData.query.filter_by(
                    instance_id=instance.id,
                    username='monitor',
                    db_type='sqlserver'
                ).first()
                
                if monitor_account:
                    print(f"monitor用户权限:")
                    print(f"  服务器角色: {monitor_account.server_roles}")
                    print(f"  数据库角色: {monitor_account.database_roles}")
                    print(f"  数据库权限: {monitor_account.database_permissions}")
                else:
                    print("❌ 没有找到monitor用户")
            else:
                print(f"❌ 同步失败: {result.get('error', '未知错误')}")
                
        except Exception as e:
            print(f"❌ 同步测试失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 关闭连接
            conn_factory.disconnect()

if __name__ == "__main__":
    test_new_sqlserver_instance()
