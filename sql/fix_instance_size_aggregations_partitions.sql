-- 修复 instance_size_aggregations 表的分区问题
-- 手动创建 9月和10月的分区

-- 检查表是否存在
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'instance_size_aggregations') THEN
        RAISE EXCEPTION 'Table instance_size_aggregations does not exist!';
    END IF;
    
    RAISE NOTICE 'Table instance_size_aggregations exists. Creating missing partitions...';
END $$;

-- 创建 2025年9月分区
DO $$
DECLARE
    partition_name TEXT := 'instance_size_aggregations_2025_09';
    start_date DATE := '2025-09-01';
    end_date DATE := '2025-10-01';
BEGIN
    -- 检查分区是否已存在
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created partition: % (from % to %)', partition_name, start_date, end_date;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
END $$;

-- 创建 2025年10月分区
DO $$
DECLARE
    partition_name TEXT := 'instance_size_aggregations_2025_10';
    start_date DATE := '2025-10-01';
    end_date DATE := '2025-11-01';
BEGIN
    -- 检查分区是否已存在
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created partition: % (from % to %)', partition_name, start_date, end_date;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
END $$;

-- 创建 2025年11月分区（下个月）
DO $$
DECLARE
    partition_name TEXT := 'instance_size_aggregations_2025_11';
    start_date DATE := '2025-11-01';
    end_date DATE := '2025-12-01';
BEGIN
    -- 检查分区是否已存在
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created partition: % (from % to %)', partition_name, start_date, end_date;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
END $$;

-- 创建 2025年12月分区（下下个月）
DO $$
DECLARE
    partition_name TEXT := 'instance_size_aggregations_2025_12';
    start_date DATE := '2025-12-01';
    end_date DATE := '2026-01-01';
BEGIN
    -- 检查分区是否已存在
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created partition: % (from % to %)', partition_name, start_date, end_date;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
END $$;

-- 验证分区创建结果
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename LIKE 'instance_size_aggregations_%'
ORDER BY tablename;

-- 显示分区信息
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename LIKE 'instance_size_aggregations_%'
ORDER BY tablename;
