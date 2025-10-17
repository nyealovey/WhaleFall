-- 验证 global_params 表时区字段修复结果
-- 执行日期: 2025-01-17

-- 1. 检查字段类型是否正确修改
SELECT 
    table_name,
    column_name, 
    data_type,
    datetime_precision,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'global_params' 
AND column_name IN ('created_at', 'updated_at')
ORDER BY column_name;

-- 2. 检查数据完整性
SELECT 
    COUNT(*) as total_records,
    COUNT(created_at) as created_at_not_null,
    COUNT(updated_at) as updated_at_not_null,
    MIN(created_at) as earliest_created,
    MAX(created_at) as latest_created,
    MIN(updated_at) as earliest_updated,
    MAX(updated_at) as latest_updated
FROM global_params;

-- 3. 检查时区信息（PostgreSQL）
SELECT 
    id,
    key,
    created_at,
    updated_at,
    EXTRACT(TIMEZONE FROM created_at) as created_at_tz,
    EXTRACT(TIMEZONE FROM updated_at) as updated_at_tz
FROM global_params 
LIMIT 5;

-- 4. 验证时间字段格式
SELECT 
    id,
    key,
    created_at::text as created_at_text,
    updated_at::text as updated_at_text
FROM global_params 
LIMIT 3;

-- 预期结果：
-- 1. data_type 应该显示为 'timestamp with time zone'
-- 2. 所有现有数据应该保持完整
-- 3. 时区信息应该正确显示（通常为 UTC 或本地时区）