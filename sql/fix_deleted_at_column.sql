-- 修复分区表缺失的 deleted_at 字段
-- 此脚本为现有的 database_size_stats 分区表添加 deleted_at 字段

BEGIN;

-- 为 database_size_stats 主表添加 deleted_at 字段
ALTER TABLE database_size_stats ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- 为所有现有的 database_size_stats 分区添加 deleted_at 字段
DO $$
DECLARE
    partition_name TEXT;
    partition_record RECORD;
BEGIN
    -- 查找所有 database_size_stats 分区
    FOR partition_record IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE tablename LIKE 'database_size_stats_%'
        ORDER BY tablename
    LOOP
        partition_name := partition_record.tablename;
        
        -- 为每个分区添加 deleted_at 字段
        EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE', partition_name);
        
        RAISE NOTICE 'Added deleted_at column to partition: %', partition_name;
    END LOOP;
END $$;

-- 为 database_size_aggregations 主表添加 updated_at 字段（如果不存在）
ALTER TABLE database_size_aggregations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW();

-- 为所有现有的 database_size_aggregations 分区添加 updated_at 字段
DO $$
DECLARE
    partition_name TEXT;
    partition_record RECORD;
BEGIN
    -- 查找所有 database_size_aggregations 分区
    FOR partition_record IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE tablename LIKE 'database_size_aggregations_%'
        ORDER BY tablename
    LOOP
        partition_name := partition_record.tablename;
        
        -- 为每个分区添加 updated_at 字段
        EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()', partition_name);
        
        RAISE NOTICE 'Added updated_at column to partition: %', partition_name;
    END LOOP;
END $$;

COMMIT;

-- 显示修复结果
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename LIKE 'database_size_stats_%' OR tablename LIKE 'database_size_aggregations_%'
ORDER BY tablename;
