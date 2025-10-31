-- 创建历史月份分区脚本
-- 用于为分区表创建历史月份的分区
-- 执行方式: psql -U <username> -d <database> -f create_historical_partitions.sql

-- ============================================================================
-- 创建历史月份分区（从2024年1月到当前月份）
-- ============================================================================

DO $
DECLARE
    start_year INTEGER := 2024;
    start_month INTEGER := 1;
    current_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month INTEGER := EXTRACT(MONTH FROM CURRENT_DATE);
    year INTEGER;
    month INTEGER;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
    partition_count INTEGER := 0;
BEGIN
    RAISE NOTICE '开始创建历史月份分区...';
    RAISE NOTICE '起始日期: %-%, 当前日期: %-%', start_year, start_month, current_year, current_month;
    
    -- 循环创建从起始月份到当前月份的所有分区
    year := start_year;
    month := start_month;
    
    WHILE (year < current_year) OR (year = current_year AND month <= current_month + 1) LOOP
        -- ========================================
        -- 1. database_size_stats 分区
        -- ========================================
        partition_name := 'database_size_stats_' || year || '_' || LPAD(month::TEXT, 2, '0');
        start_date := make_date(year, month, 1);
        
        -- 计算结束日期（下个月的第一天）
        IF month = 12 THEN
            end_date := make_date(year + 1, 1, 1);
        ELSE
            end_date := make_date(year, month + 1, 1);
        END IF;
        
        -- 检查分区是否已存在
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = partition_name
        ) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF database_size_stats FOR VALUES FROM (%L) TO (%L)',
                           partition_name, start_date, end_date);
            RAISE NOTICE '✓ 创建分区: % (% 到 %)', partition_name, start_date, end_date;
            partition_count := partition_count + 1;
        ELSE
            RAISE NOTICE '- 分区已存在: %', partition_name;
        END IF;
        
        -- ========================================
        -- 2. instance_size_stats 分区
        -- ========================================
        partition_name := 'instance_size_stats_' || year || '_' || LPAD(month::TEXT, 2, '0');
        
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = partition_name
        ) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_stats FOR VALUES FROM (%L) TO (%L)',
                           partition_name, start_date, end_date);
            RAISE NOTICE '✓ 创建分区: % (% 到 %)', partition_name, start_date, end_date;
            partition_count := partition_count + 1;
        ELSE
            RAISE NOTICE '- 分区已存在: %', partition_name;
        END IF;
        
        -- ========================================
        -- 3. database_size_aggregations 分区
        -- ========================================
        partition_name := 'database_size_aggregations_' || year || '_' || LPAD(month::TEXT, 2, '0');
        
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = partition_name
        ) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF database_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                           partition_name, start_date, end_date);
            RAISE NOTICE '✓ 创建分区: % (% 到 %)', partition_name, start_date, end_date;
            partition_count := partition_count + 1;
        ELSE
            RAISE NOTICE '- 分区已存在: %', partition_name;
        END IF;
        
        -- ========================================
        -- 4. instance_size_aggregations 分区
        -- ========================================
        partition_name := 'instance_size_aggregations_' || year || '_' || LPAD(month::TEXT, 2, '0');
        
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = partition_name
        ) THEN
            EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                           partition_name, start_date, end_date);
            RAISE NOTICE '✓ 创建分区: % (% 到 %)', partition_name, start_date, end_date;
            partition_count := partition_count + 1;
        ELSE
            RAISE NOTICE '- 分区已存在: %', partition_name;
        END IF;
        
        -- 移动到下一个月
        IF month = 12 THEN
            year := year + 1;
            month := 1;
        ELSE
            month := month + 1;
        END IF;
    END LOOP;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE '分区创建完成！共创建 % 个新分区', partition_count;
    RAISE NOTICE '========================================';
END $;

-- ============================================================================
-- 查看所有已创建的分区
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename LIKE 'database_size_%' 
   OR tablename LIKE 'instance_size_%'
ORDER BY tablename;

-- ============================================================================
-- 统计分区数量
-- ============================================================================

SELECT 
    CASE 
        WHEN tablename LIKE 'database_size_stats_%' THEN 'database_size_stats'
        WHEN tablename LIKE 'instance_size_stats_%' THEN 'instance_size_stats'
        WHEN tablename LIKE 'database_size_aggregations_%' THEN 'database_size_aggregations'
        WHEN tablename LIKE 'instance_size_aggregations_%' THEN 'instance_size_aggregations'
    END as partition_table,
    COUNT(*) as partition_count
FROM pg_tables 
WHERE tablename LIKE 'database_size_%' 
   OR tablename LIKE 'instance_size_%'
GROUP BY partition_table
ORDER BY partition_table;
