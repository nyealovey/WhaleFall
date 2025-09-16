-- 更新同步类型枚举 - SQLite版本
-- 将原有的 sync_type 枚举值更新为新的4个类型

-- 1. 备份现有数据
CREATE TABLE IF NOT EXISTS sync_sessions_backup AS 
SELECT * FROM sync_sessions;

-- 2. 更新sync_sessions表中的sync_type值
UPDATE sync_sessions 
SET sync_type = CASE 
    WHEN sync_type = 'scheduled' THEN 'scheduled_task'
    WHEN sync_type = 'manual_batch' THEN 'manual_batch'
    ELSE sync_type
END;

-- 3. 更新sync_data表中的sync_type值（如果存在）
UPDATE sync_data 
SET sync_type = CASE 
    WHEN sync_type = 'scheduled' THEN 'scheduled_task'
    WHEN sync_type = 'manual' THEN 'manual_single'
    WHEN sync_type = 'batch' THEN 'manual_batch'
    WHEN sync_type = 'task' THEN 'manual_task'
    ELSE sync_type
END
WHERE sync_type IN ('scheduled', 'manual', 'batch', 'task');

-- 4. 验证更新结果
SELECT 'sync_sessions表中的sync_type值:' as table_name;
SELECT DISTINCT sync_type FROM sync_sessions;

SELECT 'sync_data表中的sync_type值:' as table_name;
SELECT DISTINCT sync_type FROM sync_data WHERE sync_type IS NOT NULL;

-- 5. 显示更新统计
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
