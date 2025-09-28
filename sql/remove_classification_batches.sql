-- 移除分类批次功能
-- 删除 classification_batches 表及其相关索引和触发器

-- 删除触发器
DROP TRIGGER IF EXISTS update_classification_batches_updated_at ON classification_batches;

-- 删除索引
DROP INDEX IF EXISTS idx_classification_batches_batch_id;
DROP INDEX IF EXISTS idx_classification_batches_batch_type;
DROP INDEX IF EXISTS idx_classification_batches_status;
DROP INDEX IF EXISTS idx_classification_batches_started_at;
DROP INDEX IF EXISTS idx_classification_batches_created_by;

-- 删除表
DROP TABLE IF EXISTS classification_batches;

-- 输出确认信息
SELECT 'Classification batches table and related objects have been removed successfully.' as message;
