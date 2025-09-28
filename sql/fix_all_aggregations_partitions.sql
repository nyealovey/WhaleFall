-- 修复所有聚合表的分区问题
-- 确保表是分区表并创建缺失的分区

-- ============================================================================
-- 1. 修复 database_size_aggregations 表
-- ============================================================================

-- 检查并重新创建 database_size_aggregations 表
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'database_size_aggregations') THEN
        -- 检查是否是分区表
        IF NOT EXISTS (
            SELECT 1 FROM pg_class 
            WHERE relname = 'database_size_aggregations' 
            AND relkind = 'p'
        ) THEN
            RAISE NOTICE 'Table database_size_aggregations exists but is not partitioned. Dropping and recreating...';
            DROP TABLE IF EXISTS database_size_aggregations CASCADE;
        ELSE
            RAISE NOTICE 'Table database_size_aggregations is already partitioned.';
        END IF;
    ELSE
        RAISE NOTICE 'Table database_size_aggregations does not exist.';
    END IF;
END $$;

-- 创建 database_size_aggregations 分区表
CREATE TABLE IF NOT EXISTS database_size_aggregations (
    id BIGSERIAL,
    instance_id INTEGER NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    period_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    avg_size_mb BIGINT NOT NULL,
    max_size_mb BIGINT NOT NULL,
    min_size_mb BIGINT NOT NULL,
    data_count INTEGER NOT NULL,
    avg_data_size_mb BIGINT,
    max_data_size_mb BIGINT,
    min_data_size_mb BIGINT,
    avg_log_size_mb BIGINT,
    max_log_size_mb BIGINT,
    min_log_size_mb BIGINT,
    size_change_mb BIGINT DEFAULT 0 NOT NULL,
    size_change_percent NUMERIC(5, 2) DEFAULT 0 NOT NULL,
    data_size_change_mb BIGINT,
    data_size_change_percent NUMERIC(5, 2),
    log_size_change_mb BIGINT,
    log_size_change_percent NUMERIC(5, 2),
    growth_rate NUMERIC(5, 2) DEFAULT 0 NOT NULL,
    calculated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id, period_start)
) PARTITION BY RANGE (period_start);

-- 创建 database_size_aggregations 索引
CREATE INDEX IF NOT EXISTS ix_database_size_aggregations_instance_period ON database_size_aggregations (instance_id, period_type, period_start);
CREATE INDEX IF NOT EXISTS ix_database_size_aggregations_period_type ON database_size_aggregations (period_type, period_start);
CREATE INDEX IF NOT EXISTS ix_database_size_aggregations_id ON database_size_aggregations (id);

-- ============================================================================
-- 2. 修复 instance_size_aggregations 表
-- ============================================================================

-- 检查并重新创建 instance_size_aggregations 表
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

-- 创建 instance_size_aggregations 分区表
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

-- 创建 instance_size_aggregations 索引
CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_instance_period ON instance_size_aggregations (instance_id, period_type, period_start);
CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_period_type ON instance_size_aggregations (period_type, period_start);
CREATE INDEX IF NOT EXISTS ix_instance_size_aggregations_id ON instance_size_aggregations (id);

-- 创建唯一约束
ALTER TABLE instance_size_aggregations 
ADD CONSTRAINT uq_instance_size_aggregation 
UNIQUE (instance_id, period_type, period_start);

-- ============================================================================
-- 3. 创建分区函数
-- ============================================================================

-- 创建 database_size_aggregations 分区函数
CREATE OR REPLACE FUNCTION create_database_size_aggregations_partitions()
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
    partition_name := 'database_size_aggregations_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := DATE_TRUNC('month', CURRENT_DATE)::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF database_size_aggregations FOR VALUES FROM (%L) TO (%L)',
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
    partition_name := 'database_size_aggregations_' || next_year || '_' || LPAD(next_month::TEXT, 2, '0');
    start_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::DATE;
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF database_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
    
    RAISE NOTICE 'Created database_size_aggregations partitions for % and %', 
        (current_year || '-' || LPAD(current_month::TEXT, 2, '0')), 
        (next_year || '-' || LPAD(next_month::TEXT, 2, '0'));
END;
$$ LANGUAGE plpgsql;

-- 创建 instance_size_aggregations 分区函数
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

-- ============================================================================
-- 4. 执行分区创建
-- ============================================================================

-- 创建当前月份和下个月份的分区
SELECT create_database_size_aggregations_partitions();
SELECT create_instance_size_aggregations_partitions();

-- ============================================================================
-- 5. 手动创建 9月和10月分区
-- ============================================================================

-- 创建 database_size_aggregations 的 9月和10月分区
DO $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 2025年9月
    partition_name := 'database_size_aggregations_2025_09';
    start_date := '2025-09-01';
    end_date := '2025-10-01';
    
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF database_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created database_size_aggregations partition: %', partition_name;
    END IF;
    
    -- 2025年10月
    partition_name := 'database_size_aggregations_2025_10';
    start_date := '2025-10-01';
    end_date := '2025-11-01';
    
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF database_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created database_size_aggregations partition: %', partition_name;
    END IF;
END $$;

-- 创建 instance_size_aggregations 的 9月和10月分区
DO $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 2025年9月
    partition_name := 'instance_size_aggregations_2025_09';
    start_date := '2025-09-01';
    end_date := '2025-10-01';
    
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created instance_size_aggregations partition: %', partition_name;
    END IF;
    
    -- 2025年10月
    partition_name := 'instance_size_aggregations_2025_10';
    start_date := '2025-10-01';
    end_date := '2025-11-01';
    
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format('CREATE TABLE %I PARTITION OF instance_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                       partition_name, start_date, end_date);
        RAISE NOTICE 'Created instance_size_aggregations partition: %', partition_name;
    END IF;
END $$;

-- ============================================================================
-- 6. 验证结果
-- ============================================================================

-- 显示所有聚合表分区
SELECT 
    'database_size_aggregations' as table_name,
    tablename as partition_name
FROM pg_tables 
WHERE tablename LIKE 'database_size_aggregations_%'
UNION ALL
SELECT 
    'instance_size_aggregations' as table_name,
    tablename as partition_name
FROM pg_tables 
WHERE tablename LIKE 'instance_size_aggregations_%'
ORDER BY table_name, partition_name;

-- 显示分区大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE tablename LIKE '%_aggregations_%'
ORDER BY tablename;
