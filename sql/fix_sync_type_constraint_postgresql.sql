-- 修复PostgreSQL中的sync_type约束问题
-- 1. 先备份数据
CREATE TABLE IF NOT EXISTS sync_sessions_backup AS 
SELECT * FROM sync_sessions;

-- 2. 更新现有数据中的sync_type值
UPDATE sync_sessions 
SET sync_type = CASE 
    WHEN sync_type = 'scheduled' THEN 'scheduled_task'
    WHEN sync_type = 'manual_batch' THEN 'manual_batch'
    ELSE sync_type
END;

-- 3. 删除旧的枚举类型
DROP TYPE IF EXISTS sync_type_enum CASCADE;

-- 4. 创建新的枚举类型
CREATE TYPE sync_type_enum AS ENUM (
    'manual_single',
    'manual_batch', 
    'manual_task',
    'scheduled_task'
);

-- 5. 更新sync_sessions表的sync_type列
ALTER TABLE sync_sessions 
ALTER COLUMN sync_type TYPE sync_type_enum 
USING sync_type::sync_type_enum;

-- 6. 更新sync_data表的sync_type列（如果存在）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_data') THEN
        UPDATE sync_data 
        SET sync_type = CASE 
            WHEN sync_type = 'scheduled' THEN 'scheduled_task'
            WHEN sync_type = 'manual' THEN 'manual_single'
            WHEN sync_type = 'batch' THEN 'manual_batch'
            WHEN sync_type = 'task' THEN 'manual_task'
            ELSE sync_type
        END
        WHERE sync_type IN ('scheduled', 'manual', 'batch', 'task');
        
        -- 如果sync_data表有sync_type列，也更新其类型
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name = 'sync_data' AND column_name = 'sync_type') THEN
            ALTER TABLE sync_data 
            ALTER COLUMN sync_type TYPE sync_type_enum 
            USING sync_type::sync_type_enum;
        END IF;
    END IF;
END $$;

-- 7. 验证更新结果
SELECT 'sync_sessions表中的sync_type值:' as info;
SELECT DISTINCT sync_type FROM sync_sessions;

SELECT 'sync_data表中的sync_type值:' as info;
SELECT DISTINCT sync_type FROM sync_data WHERE sync_type IS NOT NULL;

-- 8. 显示统计
SELECT 
    'sync_sessions' as table_name,
    sync_type,
    COUNT(*) as count
FROM sync_sessions 
GROUP BY sync_type
UNION ALL
SELECT 
    'sync_data' as table_name,
    sync_type,
    COUNT(*) as count
FROM sync_data 
WHERE sync_type IS NOT NULL
GROUP BY sync_type;
