-- 将现有数据库表转换为分区表
-- 简化版本：直接删除重建，避免复杂的数据迁移

-- 开始事务
BEGIN;

-- 1. 删除现有的数据库大小相关表（数据不重要，可以重新采集）
DROP TABLE IF EXISTS database_size_aggregations CASCADE;
DROP TABLE IF EXISTS database_size_stats CASCADE;

-- 2. 创建数据库大小统计表（按月分区）
CREATE TABLE database_size_stats (
    id BIGSERIAL,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    database_name VARCHAR(255) NOT NULL,
    size_mb BIGINT NOT NULL,
    data_size_mb BIGINT,
    log_size_mb BIGINT,
    collected_date DATE NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (collected_date);

-- 3. 创建数据库大小聚合统计表（按月分区）
CREATE TABLE database_size_aggregations (
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
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
) PARTITION BY RANGE (period_start);

-- 4. 创建当前月份和下个月的分区（统计表）
DO $$
DECLARE
    current_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month INTEGER := EXTRACT(MONTH FROM CURRENT_DATE);
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 当前月份分区
    partition_name := 'database_size_stats_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := DATE_TRUNC('month', CURRENT_DATE)::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    
    EXECUTE format('CREATE TABLE %I PARTITION OF database_size_stats FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
    
    -- 下个月分区
    partition_name := 'database_size_stats_' || current_year || '_' || LPAD((current_month + 1)::TEXT, 2, '0');
    start_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::DATE;
    
    EXECUTE format('CREATE TABLE %I PARTITION OF database_size_stats FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
END $$;

-- 5. 创建当前月份和下个月的分区（聚合表）
DO $$
DECLARE
    current_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month INTEGER := EXTRACT(MONTH FROM CURRENT_DATE);
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    -- 当前月份分区
    partition_name := 'database_size_aggregations_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    start_date := DATE_TRUNC('month', CURRENT_DATE)::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    
    EXECUTE format('CREATE TABLE %I PARTITION OF database_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
    
    -- 下个月分区
    partition_name := 'database_size_aggregations_' || current_year || '_' || LPAD((current_month + 1)::TEXT, 2, '0');
    start_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month')::DATE;
    end_date := (DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '2 months')::DATE;
    
    EXECUTE format('CREATE TABLE %I PARTITION OF database_size_aggregations FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
END $$;

-- 6. 创建索引和约束
-- 统计表索引
CREATE INDEX ix_database_size_stats_instance_db ON database_size_stats (instance_id, database_name);
CREATE INDEX ix_database_size_stats_collected_date ON database_size_stats (collected_date);
CREATE INDEX ix_database_size_stats_instance_date ON database_size_stats (instance_id, collected_date);
CREATE INDEX ix_database_size_stats_deleted ON database_size_stats (is_deleted);

-- 聚合表索引
CREATE INDEX ix_database_size_aggregations_instance_period ON database_size_aggregations (instance_id, period_type, period_start);
CREATE INDEX ix_database_size_aggregations_period_type ON database_size_aggregations (period_type, period_start);
CREATE INDEX ix_database_size_aggregations_id ON database_size_aggregations (id);

-- 聚合表唯一约束
ALTER TABLE database_size_aggregations ADD CONSTRAINT uq_database_size_aggregation UNIQUE (instance_id, database_name, period_type, period_start);

-- 7. 添加表注释
COMMENT ON TABLE database_size_stats IS '数据库大小统计表（按月分区）';
COMMENT ON TABLE database_size_aggregations IS '数据库大小聚合统计表（按月分区）';

-- 8. 为分区创建索引
-- 统计表分区索引
DO $$
DECLARE
    current_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month INTEGER := EXTRACT(MONTH FROM CURRENT_DATE);
    partition_name TEXT;
BEGIN
    -- 当前月份分区索引
    partition_name := 'database_size_stats_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    EXECUTE format('CREATE INDEX idx_%s_instance_db ON %I (instance_id, database_name)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_date ON %I (collected_date)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_instance_date ON %I (instance_id, collected_date)', partition_name, partition_name);
    
    -- 下个月分区索引
    partition_name := 'database_size_stats_' || current_year || '_' || LPAD((current_month + 1)::TEXT, 2, '0');
    EXECUTE format('CREATE INDEX idx_%s_instance_db ON %I (instance_id, database_name)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_date ON %I (collected_date)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_instance_date ON %I (instance_id, collected_date)', partition_name, partition_name);
END $$;

-- 聚合表分区索引
DO $$
DECLARE
    current_year INTEGER := EXTRACT(YEAR FROM CURRENT_DATE);
    current_month INTEGER := EXTRACT(MONTH FROM CURRENT_DATE);
    partition_name TEXT;
BEGIN
    -- 当前月份分区索引
    partition_name := 'database_size_aggregations_' || current_year || '_' || LPAD(current_month::TEXT, 2, '0');
    EXECUTE format('CREATE INDEX idx_%s_instance_db ON %I (instance_id, database_name)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_period ON %I (period_start, period_end)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_type ON %I (period_type, period_start)', partition_name, partition_name);
    
    -- 下个月分区索引
    partition_name := 'database_size_aggregations_' || current_year || '_' || LPAD((current_month + 1)::TEXT, 2, '0');
    EXECUTE format('CREATE INDEX idx_%s_instance_db ON %I (instance_id, database_name)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_period ON %I (period_start, period_end)', partition_name, partition_name);
    EXECUTE format('CREATE INDEX idx_%s_type ON %I (period_type, period_start)', partition_name, partition_name);
END $$;

-- 9. 提交事务
COMMIT;

-- 10. 验证分区表创建
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename LIKE 'database_size_%'
ORDER BY tablename;

-- 完成提示
SELECT '数据库表已成功转换为分区表！' as message,
       '统计表和聚合表都已按月分区，便于数据清理' as description,
       NOW() as completed_at;
