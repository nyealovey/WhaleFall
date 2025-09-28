-- 简单修复聚合同步分类约束问题
-- 专门处理约束已存在的情况

-- 1. 检查现有约束内容
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'sync_sessions'::regclass 
AND conname LIKE '%sync_category%';

-- 2. 强制删除现有约束（如果存在）
DO $$ 
BEGIN
    -- 删除 sync_sessions 表的约束
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conrelid = 'sync_sessions'::regclass 
        AND conname = 'sync_sessions_sync_category_check'
    ) THEN
        ALTER TABLE sync_sessions DROP CONSTRAINT sync_sessions_sync_category_check;
        RAISE NOTICE '已删除 sync_sessions 表的现有约束';
    END IF;
    
    -- 删除 sync_instance_records 表的约束
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conrelid = 'sync_instance_records'::regclass 
        AND conname = 'sync_instance_records_sync_category_check'
    ) THEN
        ALTER TABLE sync_instance_records DROP CONSTRAINT sync_instance_records_sync_category_check;
        RAISE NOTICE '已删除 sync_instance_records 表的现有约束';
    END IF;
END $$;

-- 3. 添加包含 aggregation 的新约束
ALTER TABLE sync_sessions
ADD CONSTRAINT sync_sessions_sync_category_check
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

ALTER TABLE sync_instance_records
ADD CONSTRAINT sync_instance_records_sync_category_check
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 4. 添加列注释
COMMENT ON COLUMN sync_sessions.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
COMMENT ON COLUMN sync_instance_records.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';

-- 5. 验证新约束
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'sync_sessions'::regclass 
AND conname LIKE '%sync_category%';

SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'sync_instance_records'::regclass 
AND conname LIKE '%sync_category%';

-- 6. 测试插入 aggregation 分类
INSERT INTO sync_sessions (
    session_id, sync_type, sync_category, status, 
    started_at, total_instances, successful_instances, failed_instances,
    created_at, updated_at
) VALUES (
    'test-aggregation-' || extract(epoch from now())::text, 
    'scheduled_task', 'aggregation', 'running',
    NOW(), 0, 0, 0, NOW(), NOW()
);

-- 清理测试数据
DELETE FROM sync_sessions WHERE session_id LIKE 'test-aggregation-%';

RAISE NOTICE '约束修复完成，aggregation 分类已支持！';
