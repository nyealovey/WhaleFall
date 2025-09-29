-- 更新同步相关常量约束
-- 使用更清晰的英文操作方式描述

-- 1. 更新同步会话表的操作方式约束
ALTER TABLE sync_sessions 
DROP CONSTRAINT IF EXISTS sync_sessions_sync_type_check;

ALTER TABLE sync_sessions 
ADD CONSTRAINT sync_sessions_sync_type_check 
CHECK (sync_type IN ('manual_single', 'manual_batch', 'manual_task', 'scheduled_task'));

-- 2. 更新同步会话表的同步分类约束
ALTER TABLE sync_sessions 
DROP CONSTRAINT IF EXISTS sync_sessions_sync_category_check;

ALTER TABLE sync_sessions 
ADD CONSTRAINT sync_sessions_sync_category_check 
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 3. 更新同步实例记录表的同步分类约束
ALTER TABLE sync_instance_records 
DROP CONSTRAINT IF EXISTS sync_instance_records_sync_category_check;

ALTER TABLE sync_instance_records 
ADD CONSTRAINT sync_instance_records_sync_category_check 
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 4. 添加详细的列注释
COMMENT ON COLUMN sync_sessions.sync_type IS '同步操作方式: manual_single(手动单台), manual_batch(手动批量), manual_task(手动任务), scheduled_task(定时任务)';
COMMENT ON COLUMN sync_sessions.sync_category IS '同步分类: account(账户同步), capacity(容量同步), config(配置同步), aggregation(聚合统计), other(其他)';
COMMENT ON COLUMN sync_instance_records.sync_category IS '同步分类: account(账户同步), capacity(容量同步), config(配置同步), aggregation(聚合统计), other(其他)';

-- 5. 验证约束是否正确应用
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'sync_sessions'::regclass 
AND conname LIKE '%sync_%_check';

SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'sync_instance_records'::regclass 
AND conname LIKE '%sync_%_check';
