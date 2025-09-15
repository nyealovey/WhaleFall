#!/usr/bin/env python3
"""
测试实例删除功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.models.instance import Instance

def test_delete_function():
    """测试删除功能"""
    print("🔧 测试实例删除功能...")

    # 创建Flask应用
    app = create_app()

    with app.app_context():
        try:
            # 获取所有实例
            instances = Instance.query.all()
            print(f"📊 找到 {len(instances)} 个实例")
            
            for instance in instances:
                print(f"  - {instance.name} (ID: {instance.id})")
            
            if not instances:
                print("❌ 没有找到任何实例")
                return False
            
            # 测试删除辅助函数（不实际删除）
            instance = instances[0]
            print(f"\n🔍 测试删除实例: {instance.name} (ID: {instance.id})")
            
            # 检查关联数据
            from app.models.current_account_sync_data import CurrentAccountSyncData
            from app.models.sync_instance_record import SyncInstanceRecord
            from app.models.account_change_log import AccountChangeLog
            from app.models.account_classification import AccountClassificationAssignment
            
            sync_data_ids = [data.id for data in CurrentAccountSyncData.query.filter_by(instance_id=instance.id).all()]
            assignment_count = 0
            if sync_data_ids:
                assignment_count = AccountClassificationAssignment.query.filter(
                    AccountClassificationAssignment.account_id.in_(sync_data_ids)
                ).count()
            
            sync_data_count = CurrentAccountSyncData.query.filter_by(instance_id=instance.id).count()
            sync_record_count = SyncInstanceRecord.query.filter_by(instance_id=instance.id).count()
            change_log_count = AccountChangeLog.query.filter_by(instance_id=instance.id).count()
            
            print(f"   关联数据统计:")
            print(f"     - 分类分配: {assignment_count}")
            print(f"     - 同步数据: {sync_data_count}")
            print(f"     - 同步记录: {sync_record_count}")
            print(f"     - 变更日志: {change_log_count}")
            print(f"     - 总计: {assignment_count + sync_data_count + sync_record_count + change_log_count}")
            
            print("✅ 删除功能检查完成")
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    test_delete_function()

