#!/usr/bin/env python3
"""
更新同步类型枚举脚本
将原有的sync_type枚举值更新为新的4个类型
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.models.sync_session import SyncSession
from app.models.sync_data import SyncData
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


def update_sync_type_enum():
    """更新同步类型枚举值"""
    try:
        logger.info("开始更新同步类型枚举值")
        
        # 更新sync_sessions表
        sessions_updated = db.session.query(SyncSession).filter(
            SyncSession.sync_type.in_(['scheduled'])
        ).update({
            SyncSession.sync_type: 'scheduled_task'
        }, synchronize_session=False)
        
        logger.info(f"更新了 {sessions_updated} 条sync_sessions记录")
        
        # 更新sync_data表（如果存在）
        try:
            sync_data_updated = db.session.query(SyncData).filter(
                SyncData.sync_type.in_(['scheduled', 'manual', 'batch', 'task'])
            ).update({
                SyncData.sync_type: db.case(
                    [
                        (SyncData.sync_type == 'scheduled', 'scheduled_task'),
                        (SyncData.sync_type == 'manual', 'manual_single'),
                        (SyncData.sync_type == 'batch', 'manual_batch'),
                        (SyncData.sync_type == 'task', 'manual_task'),
                    ],
                    else_=SyncData.sync_type
                )
            }, synchronize_session=False)
            
            logger.info(f"更新了 {sync_data_updated} 条sync_data记录")
        except Exception as e:
            logger.warning(f"更新sync_data表时出错: {e}")
        
        # 提交更改
        db.session.commit()
        
        # 验证更新结果
        sync_types = db.session.query(SyncSession.sync_type).distinct().all()
        logger.info(f"sync_sessions表中的sync_type值: {[t[0] for t in sync_types]}")
        
        try:
            data_types = db.session.query(SyncData.sync_type).distinct().all()
            logger.info(f"sync_data表中的sync_type值: {[t[0] for t in data_types]}")
        except Exception as e:
            logger.warning(f"查询sync_data表时出错: {e}")
        
        logger.info("同步类型枚举值更新完成")
        return True
        
    except Exception as e:
        logger.error(f"更新同步类型枚举值时出错: {e}")
        db.session.rollback()
        return False


def main():
    """主函数"""
    app = create_app()
    
    with app.app_context():
        success = update_sync_type_enum()
        
        if success:
            print("✅ 同步类型枚举值更新成功")
            sys.exit(0)
        else:
            print("❌ 同步类型枚举值更新失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
