-- 回滚 global_params 表时区字段修改
-- 执行日期: 2025-01-17
-- 目的: 将时区字段回滚为普通 TIMESTAMP 类型

-- 警告：执行此脚本前请确保已备份数据！

-- 开始事务
BEGIN;

-- 备份当前数据状态
SELECT 
    'Before rollback' as status,
    COUNT(*) as total_records,
    COUNT(created_at) as created_at_count,
    COUNT(updated_at) as updated_at_count
FROM global_params;

-- 回滚 created_at 字段为普通 TIMESTAMP
ALTER TABLE global_params 
ALTER COLUMN created_at TYPE TIMESTAMP;

-- 回滚 updated_at 字段为普通 TIMESTAMP
ALTER TABLE global_params 
ALTER COLUMN updated_at TYPE TIMESTAMP;

-- 验证回滚结果
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'global_params' 
AND column_name IN ('created_at', 'updated_at')
ORDER BY column_name;

-- 验证数据完整性
SELECT 
    'After rollback' as status,
    COUNT(*) as total_records,
    COUNT(created_at) as created_at_count,
    COUNT(updated_at) as updated_at_count
FROM global_params;

-- 提交事务
COMMIT;

-- 预期结果：
-- 1. data_type 应该显示为 'timestamp without time zone'
-- 2. 所有数据应该保持完整