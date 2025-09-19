-- 数据库迁移脚本：添加缺失的字段
-- 鲸落 (Whalefall) 数据库字段补丁
-- 修复 current_account_sync_data 表缺失的字段
-- 执行时间：2025-09-19

-- 设置时区和字符集
SET timezone = 'Asia/Shanghai';
SET client_encoding = 'UTF8';

-- 开始事务
BEGIN;

-- ============================================================================
-- 修复 current_account_sync_data 表缺失字段
-- ============================================================================

-- 添加 last_sync_time 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'current_account_sync_data' 
        AND column_name = 'last_sync_time'
    ) THEN
        ALTER TABLE current_account_sync_data 
        ADD COLUMN last_sync_time TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        
        -- 为现有记录设置默认值
        UPDATE current_account_sync_data 
        SET last_sync_time = COALESCE(sync_time, NOW()) 
        WHERE last_sync_time IS NULL;
        
        RAISE NOTICE 'Added last_sync_time column to current_account_sync_data table';
    ELSE
        RAISE NOTICE 'last_sync_time column already exists in current_account_sync_data table';
    END IF;
END $$;

-- 添加 last_change_type 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'current_account_sync_data' 
        AND column_name = 'last_change_type'
    ) THEN
        ALTER TABLE current_account_sync_data 
        ADD COLUMN last_change_type VARCHAR(20) DEFAULT 'add';
        
        -- 为现有记录设置默认值
        UPDATE current_account_sync_data 
        SET last_change_type = 'add' 
        WHERE last_change_type IS NULL;
        
        RAISE NOTICE 'Added last_change_type column to current_account_sync_data table';
    ELSE
        RAISE NOTICE 'last_change_type column already exists in current_account_sync_data table';
    END IF;
END $$;

-- 添加 last_change_time 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'current_account_sync_data' 
        AND column_name = 'last_change_time'
    ) THEN
        ALTER TABLE current_account_sync_data 
        ADD COLUMN last_change_time TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        
        -- 为现有记录设置默认值
        UPDATE current_account_sync_data 
        SET last_change_time = COALESCE(sync_time, NOW()) 
        WHERE last_change_time IS NULL;
        
        RAISE NOTICE 'Added last_change_time column to current_account_sync_data table';
    ELSE
        RAISE NOTICE 'last_change_time column already exists in current_account_sync_data table';
    END IF;
END $$;

-- 添加 deleted_time 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'current_account_sync_data' 
        AND column_name = 'deleted_time'
    ) THEN
        ALTER TABLE current_account_sync_data 
        ADD COLUMN deleted_time TIMESTAMP WITH TIME ZONE;
        
        RAISE NOTICE 'Added deleted_time column to current_account_sync_data table';
    ELSE
        RAISE NOTICE 'deleted_time column already exists in current_account_sync_data table';
    END IF;
END $$;

-- ============================================================================
-- 添加新字段的索引
-- ============================================================================

-- 添加 last_sync_time 索引（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'current_account_sync_data' 
        AND indexname = 'idx_last_sync_time'
    ) THEN
        CREATE INDEX idx_last_sync_time ON current_account_sync_data(last_sync_time);
        RAISE NOTICE 'Added idx_last_sync_time index';
    ELSE
        RAISE NOTICE 'idx_last_sync_time index already exists';
    END IF;
END $$;

-- 添加 last_change_time 索引（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'current_account_sync_data' 
        AND indexname = 'idx_last_change_time'
    ) THEN
        CREATE INDEX idx_last_change_time ON current_account_sync_data(last_change_time);
        RAISE NOTICE 'Added idx_last_change_time index';
    ELSE
        RAISE NOTICE 'idx_last_change_time index already exists';
    END IF;
END $$;

-- 添加 deleted_time 索引（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'current_account_sync_data' 
        AND indexname = 'idx_deleted_time'
    ) THEN
        CREATE INDEX idx_deleted_time ON current_account_sync_data(deleted_time);
        RAISE NOTICE 'Added idx_deleted_time index';
    ELSE
        RAISE NOTICE 'idx_deleted_time index already exists';
    END IF;
END $$;

-- ============================================================================
-- 验证修复结果
-- ============================================================================

-- 验证字段是否存在
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'current_account_sync_data' 
AND column_name IN ('last_sync_time', 'last_change_type', 'last_change_time', 'deleted_time')
ORDER BY column_name;

-- 验证索引是否存在
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'current_account_sync_data' 
AND indexname IN ('idx_last_sync_time', 'idx_last_change_time', 'idx_deleted_time')
ORDER BY indexname;

-- 提交事务
COMMIT;

-- 输出完成信息
\echo '========================================'
\echo '数据库字段修复完成！'
\echo '已添加以下字段到 current_account_sync_data 表：'
\echo '- last_sync_time: 最后同步时间'
\echo '- last_change_type: 最后变更类型'
\echo '- last_change_time: 最后变更时间'
\echo '- deleted_time: 删除时间'
\echo '========================================'
