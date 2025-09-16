-- 更新同步类型枚举
-- 将原有的 sync_type 枚举值更新为新的4个类型

-- 对于PostgreSQL，需要先删除旧的枚举类型，然后创建新的
-- 注意：这个操作会删除所有使用该枚举的数据，需要谨慎执行

-- 1. 备份现有数据
CREATE TABLE IF NOT EXISTS sync_sessions_backup AS 
SELECT * FROM sync_sessions;

-- 2. 更新现有数据中的sync_type值
UPDATE sync_sessions 
SET sync_type = CASE 
    WHEN sync_type = 'scheduled' THEN 'scheduled_task'
    WHEN sync_type = 'manual_batch' THEN 'manual_batch'
    ELSE sync_type
END;

-- 3. 对于PostgreSQL，需要重新创建枚举类型
-- 注意：这需要先删除所有使用该枚举的列，然后重新创建

-- 4. 更新sync_data表中的sync_type值（如果存在）
UPDATE sync_data 
SET sync_type = CASE 
    WHEN sync_type = 'scheduled' THEN 'scheduled_task'
    WHEN sync_type = 'manual' THEN 'manual_single'
    WHEN sync_type = 'batch' THEN 'manual_batch'
    WHEN sync_type = 'task' THEN 'manual_task'
    ELSE sync_type
END
WHERE sync_type IN ('scheduled', 'manual', 'batch', 'task');

-- 5. 验证更新结果
SELECT DISTINCT sync_type FROM sync_sessions;
SELECT DISTINCT sync_type FROM sync_data WHERE sync_type IS NOT NULL;
