-- 修复聚合同步分类约束问题
-- 这个脚本用于更新现有数据库的约束，添加 'aggregation' 支持

-- 1. 检查现有约束内容
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'sync_sessions'::regclass 
AND conname LIKE '%sync_category%';

-- 2. 更新 sync_sessions 表的约束
-- 先删除现有约束
ALTER TABLE sync_sessions
DROP CONSTRAINT sync_sessions_sync_category_check;

-- 添加包含 aggregation 的新约束
ALTER TABLE sync_sessions
ADD CONSTRAINT sync_sessions_sync_category_check
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 2. 更新 sync_instance_records 表的约束
ALTER TABLE sync_instance_records
DROP CONSTRAINT IF EXISTS sync_instance_records_sync_category_check;

ALTER TABLE sync_instance_records
ADD CONSTRAINT sync_instance_records_sync_category_check
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 3. 添加列注释
COMMENT ON COLUMN sync_sessions.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
COMMENT ON COLUMN sync_instance_records.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';

-- 4. 验证约束是否正确应用
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
