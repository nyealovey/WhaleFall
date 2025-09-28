-- 修复 instance_size_aggregations 表的分区问题
-- 确保表是分区表并创建缺失的分区

-- 1. 检查表是否存在并删除（如果存在但不是分区表）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'instance_size_aggregations') THEN
        -- 检查是否是分区表
        IF NOT EXISTS (
            SELECT 1 FROM pg_class 
            WHERE relname = 'instance_size_aggregations' 
            AND relkind = 'p'
        ) THEN
            RAISE NOTICE 'Table instance_size_aggregations exists but is not partitioned. Dropping and recreating...';
            DROP TABLE IF EXISTS instance_size_aggregations CASCADE;
        ELSE
            RAISE NOTICE 'Table instance_size_aggregations is already partitioned.';
        END IF;
    ELSE
        RAISE NOTICE 'Table instance_size_aggregations does not exist.';
    END IF;
END $$;

-- 2. 创建分区表（如果不存在）
CREATE TABLE IF NOT EXISTS instance_size_aggregations (
    id BIGSERIAL,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    period_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_size_mb BIGINT NOT NULL,
    avg_size_mb BIGINT NOT NULL,
    max_size_mb BIGINT NOT NULL,
    min_size_mb BIGINT NOT NULL,
    data_count INTEGER NOT NULL,
    database_count INTEGER NOT NULL,
    avg_database_count NUMERIC(10, 2),
    max_database_count INTEGER,
    min_database_count INTEGER,
    total_size_change_mb BIGINT,
    total_size_change_percent NUMERIC(10, 2),
    database_count_change INTEGER,
    database_count_change_percent NUMERIC(10, 2),
    growth_rate NUMERIC(10, 2),
    trend_direction VARCHAR(20),
    calculated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id, period_start)
) PARTITION BY RANGE (period_start);

-- 3. 创建索引
CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_instance_period ON instance_size_aggregations (instance_id, period_type, period_start);
CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_period_type ON instance_size_aggregations (period_type, period_start);
CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_id ON instance_size_aggregations (id);

-- 4. 创建唯一约束
ALTER TABLE instance_size_aggregations 
ADD CONSTRAINT uq_instance_size_aggregation 
UNIQUE (instance_id, period_type, period_start);

-- 5. 添加注释
COMMENT ON TABLE instance_size_aggregations IS '实例大小聚合统计表（按月分区）';

-- 6. 创建分区函数
CREATE OR REPLACE FUNCTION create_instance_size_aggregations_partitions()
RETURNS void AS $$
DECLARE
    current_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month INTEGER := EXTRACT(MONTH FROM CURRENT_DATE);
    next_year INTEGER;
    next_month INTEGER;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 当前月份分区
    partition_name := 'instance_size_aggregations_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := DATE_TRUNC('month', CURRENT_DATE)::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
    
    -- 计算下个月
    IF current_month = 12 THEN
        next_year := current_year + 1;
        next_month := 1;
    ELSE
        next_year := current_year;
        next_month := current_month + 1;
    END IF;
    
    -- 下个月分区
    partition_name := 'instance_size_aggregations_' || next_year || '_' || LPAD(next_month::TEXT, 2, '0');
    start_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::DATE;
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
    
    RAISE NOTICE 'Created instance_size_aggregations partitions for % and %', 
        (current_year || '-' || LPAD(current_month::TEXT, 2, '0')), 
        (next_year || '-' || LPAD(next_month::TEXT, 2, '0'));
END;
$$ LANGUAGE plpgsql;

-- 7. 执行分区创建
SELECT create_instance_size_aggregations_partitions();

-- 8. 手动创建 9月和10月分区
DO $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 创建 2025年9月分区
    partition_name := 'instance_size_aggregations_2025_09';
    start_date := '2025-09-01';
    end_date := '2025-10-01';
    
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created partition: % (from % to %)', partition_name, start_date, end_date;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
    
    -- 创建 2025年10月分区
    partition_name := 'instance_size_aggregations_2025_10';
    start_date := '2025-10-01';
    end_date := '2025-11-01';
    
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created partition: % (from % to %)', partition_name, start_date, end_date;
    ELSE
        RAISE NOTICE 'Partition % already exists', partition_name;
    END IF;
END $$;

-- 9. 验证分区创建结果
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename LIKE 'instance_size_aggregations_%'
ORDER BY tablename;

-- 10. 显示分区信息
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename LIKE 'instance_size_aggregations_%'
ORDER BY tablename;
