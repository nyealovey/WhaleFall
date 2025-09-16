#!/usr/bin/env python3
"""
更新PostgreSQL中的同步类型枚举脚本
将原有的sync_type枚举值更新为新的4个类型
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.models.sync_session import SyncSession
from app.utils.structlog_config import get_system_logger
from sqlalchemy import text

logger = get_system_logger()


def update_postgresql_sync_type_enum():
    """更新PostgreSQL中的同步类型枚举值"""
    try:
        logger.info("开始更新PostgreSQL中的同步类型枚举值")
        
        # 1. 备份数据
        logger.info("备份现有数据")
        db.session.execute(text("CREATE TABLE IF NOT EXISTS sync_sessions_backup AS SELECT * FROM sync_sessions"))
        
        # 2. 更新sync_sessions表中的数据
        logger.info("更新sync_sessions表中的sync_type值")
        result = db.session.execute(text("""
            UPDATE sync_sessions 
            SET sync_type = CASE 
                WHEN sync_type = 'scheduled' THEN 'scheduled_task'
                WHEN sync_type = 'manual_batch' THEN 'manual_batch'
                ELSE sync_type
            END
        """))
        logger.info(f"更新了 {result.rowcount} 条sync_sessions记录")
        
        # 3. 删除旧的枚举类型
        logger.info("删除旧的枚举类型")
        db.session.execute(text("DROP TYPE IF EXISTS sync_type_enum CASCADE"))
        
        # 4. 创建新的枚举类型
        logger.info("创建新的枚举类型")
        db.session.execute(text("""
            CREATE TYPE sync_type_enum AS ENUM (
                'manual_single',
                'manual_batch', 
                'manual_task',
                'scheduled_task'
            )
        """))
        
        # 5. 更新sync_sessions表的sync_type列
        logger.info("更新sync_sessions表的sync_type列类型")
        db.session.execute(text("""
            ALTER TABLE sync_sessions 
            ALTER COLUMN sync_type TYPE sync_type_enum 
            USING sync_type::sync_type_enum
        """))
        
        # 6. 检查并更新sync_data表（如果存在）
        logger.info("检查sync_data表")
        result = db.session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'sync_data'
            )
        """))
        sync_data_exists = result.scalar()
        
        if sync_data_exists:
            logger.info("更新sync_data表")
            # 更新数据
            db.session.execute(text("""
                UPDATE sync_data 
                SET sync_type = CASE 
                    WHEN sync_type = 'scheduled' THEN 'scheduled_task'
                    WHEN sync_type = 'manual' THEN 'manual_single'
                    WHEN sync_type = 'batch' THEN 'manual_batch'
                    WHEN sync_type = 'task' THEN 'manual_task'
                    ELSE sync_type
                END
                WHERE sync_type IN ('scheduled', 'manual', 'batch', 'task')
            """))
            
            # 检查是否有sync_type列
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'sync_data' AND column_name = 'sync_type'
                )
            """))
            has_sync_type_column = result.scalar()
            
            if has_sync_type_column:
                logger.info("更新sync_data表的sync_type列类型")
                db.session.execute(text("""
                    ALTER TABLE sync_data 
                    ALTER COLUMN sync_type TYPE sync_type_enum 
                    USING sync_type::sync_type_enum
                """))
        
        # 7. 提交更改
        db.session.commit()
        
        # 8. 验证更新结果
        logger.info("验证更新结果")
        result = db.session.execute(text("SELECT DISTINCT sync_type FROM sync_sessions"))
        sync_types = [row[0] for row in result.fetchall()]
        logger.info(f"sync_sessions表中的sync_type值: {sync_types}")
        
        if sync_data_exists:
            result = db.session.execute(text("SELECT DISTINCT sync_type FROM sync_data WHERE sync_type IS NOT NULL"))
            data_types = [row[0] for row in result.fetchall()]
            logger.info(f"sync_data表中的sync_type值: {data_types}")
        
        logger.info("PostgreSQL同步类型枚举值更新完成")
        return True
        
    except Exception as e:
        logger.error(f"更新PostgreSQL同步类型枚举值时出错: {e}")
        db.session.rollback()
        return False


def main():
    """主函数"""
    app = create_app()
    
    with app.app_context():
        success = update_postgresql_sync_type_enum()
        
        if success:
            print("✅ PostgreSQL同步类型枚举值更新成功")
            sys.exit(0)
        else:
            print("❌ PostgreSQL同步类型枚举值更新失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
