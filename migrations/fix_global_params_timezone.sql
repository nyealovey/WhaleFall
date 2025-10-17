-- 修复 global_params 表时间字段时区信息
-- 执行日期: 2025-01-17
-- 目的: 将 created_at 和 updated_at 字段改为支持时区的类型

-- 开始事务
BEGIN;

-- 备份当前数据（可选，用于验证）
-- SELECT created_at, updated_at FROM global_params LIMIT 5;

-- 修改 created_at 字段为 TIMESTAMP WITH TIME ZONE
ALTER TABLE global_params 
ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE;

-- 修改 updated_at 字段为 TIMESTAMP WITH TIME ZONE  
ALTER TABLE global_params 
ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE;

-- 验证修改结果
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'global_params' 
AND column_name IN ('created_at', 'updated_at')
ORDER BY column_name;

-- 验证数据完整性（检查是否有数据丢失）
SELECT 
    COUNT(*) as total_records,
    COUNT(created_at) as created_at_count,
    COUNT(updated_at) as updated_at_count
FROM global_params;

-- 提交事务
COMMIT;

-- 如果需要回滚，执行以下语句：
-- BEGIN;
-- ALTER TABLE global_params ALTER COLUMN created_at TYPE TIMESTAMP;
-- ALTER TABLE global_params ALTER COLUMN updated_at TYPE TIMESTAMP;
-- COMMIT;