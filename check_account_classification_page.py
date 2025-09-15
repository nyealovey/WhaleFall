#!/usr/bin/env python3
"""
检查账户分类页面中的Oracle账户显示
"""

from app import create_app, db
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.models.instance import Instance

def check_account_classification_display():
    app = create_app()
    with app.app_context():
        print("检查账户分类页面中的Oracle账户显示")
        print("=" * 50)
        
        # 查询Oracle实例
        oracle_instances = Instance.query.filter_by(db_type='oracle').all()
        
        for instance in oracle_instances:
            print(f"\n🔍 实例: {instance.name} (ID: {instance.id})")
            
            # 查询该实例下的所有Oracle账户
            oracle_accounts = CurrentAccountSyncData.query.filter_by(
                instance_id=instance.id, 
                db_type='oracle'
            ).all()
            
            print(f"   总账户数: {len(oracle_accounts)}")
            
            # 按用户名排序显示
            sorted_accounts = sorted(oracle_accounts, key=lambda x: x.username)
            
            for i, account in enumerate(sorted_accounts, 1):
                print(f"   {i:2d}. {account.username}")
                print(f"       角色数: {len(account.oracle_roles)}")
                print(f"       系统权限数: {len(account.system_privileges)}")
                print(f"       是否超级用户: {account.is_superuser}")
                print(f"       最后同步: {account.last_sync_time}")
                
                # 如果是SYS账户，显示详细信息
                if account.username.upper() == 'SYS':
                    print(f"       🔍 SYS账户详细信息:")
                    print(f"          角色: {account.oracle_roles[:5]}{'...' if len(account.oracle_roles) > 5 else ''}")
                    print(f"          系统权限: {account.system_privileges[:5]}{'...' if len(account.system_privileges) > 5 else ''}")
                    print(f"          表空间权限: {account.tablespace_privileges_oracle}")

if __name__ == "__main__":
    check_account_classification_display()
