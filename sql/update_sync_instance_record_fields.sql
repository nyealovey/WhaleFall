-- 更新同步实例记录表字段名，使其更通用
-- 将账户同步专用字段改为通用字段

-- 1. 重命名字段
ALTER TABLE sync_instance_records 
RENAME COLUMN accounts_synced TO items_synced;

ALTER TABLE sync_instance_records 
RENAME COLUMN accounts_created TO items_created;

ALTER TABLE sync_instance_records 
RENAME COLUMN accounts_updated TO items_updated;

ALTER TABLE sync_instance_records 
RENAME COLUMN accounts_deleted TO items_deleted;

-- 2. 添加列注释
COMMENT ON COLUMN sync_instance_records.items_synced IS '同步的项目数量（通用字段，支持账户、容量、聚合等）';
COMMENT ON COLUMN sync_instance_records.items_created IS '创建的项目数量（通用字段，支持账户、容量、聚合等）';
COMMENT ON COLUMN sync_instance_records.items_updated IS '更新的项目数量（通用字段，支持账户、容量、聚合等）';
COMMENT ON COLUMN sync_instance_records.items_deleted IS '删除的项目数量（通用字段，支持账户、容量、聚合等）';

-- 3. 验证字段重命名
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'sync_instance_records' 
AND column_name IN ('items_synced', 'items_created', 'items_updated', 'items_deleted')
ORDER BY column_name;
