-- 添加聚合同步分类支持
-- 为同步会话管理添加 aggregation 分类

-- 更新同步会话表的约束
ALTER TABLE sync_sessions 
DROP CONSTRAINT IF EXISTS sync_sessions_sync_category_check;

ALTER TABLE sync_sessions 
ADD CONSTRAINT sync_sessions_sync_category_check 
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 更新同步实例记录表的约束
ALTER TABLE sync_instance_records 
DROP CONSTRAINT IF EXISTS sync_instance_records_sync_category_check;

ALTER TABLE sync_instance_records 
ADD CONSTRAINT sync_instance_records_sync_category_check 
CHECK (sync_category IN ('account', 'capacity', 'config', 'aggregation', 'other'));

-- 添加注释
COMMENT ON COLUMN sync_sessions.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
COMMENT ON COLUMN sync_instance_records.sync_category IS '同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)';
