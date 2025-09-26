-- 将 database_size_aggregations 表转换为分区表
-- 简化版本：直接删除重建，避免复杂的数据迁移

-- 1. 删除现有的聚合表（数据不重要，可以重新采集）
DROP TABLE IF EXISTS database_size_aggregations CASCADE;

-- 2. 创建新的分区主表
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

-- 3. 创建索引和约束
-- 唯一约束
ALTER TABLE database_size_aggregations ADD CONSTRAINT uq_database_size_aggregation UNIQUE (instance_id, database_name, period_type, period_start);

-- 索引
CREATE INDEX ix_database_size_aggregations_instance_period ON database_size_aggregations (instance_id, period_type, period_start);
CREATE INDEX ix_database_size_aggregations_period_type ON database_size_aggregations (period_type, period_start);
CREATE INDEX ix_database_size_aggregations_id ON database_size_aggregations (id);

-- 4. 创建分区（2024年1月到2026年3月）
-- 2024年
CREATE TABLE database_size_aggregations_2024_01 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE database_size_aggregations_2024_02 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE database_size_aggregations_2024_03 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE database_size_aggregations_2024_04 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE database_size_aggregations_2024_05 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE database_size_aggregations_2024_06 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE database_size_aggregations_2024_07 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE database_size_aggregations_2024_08 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE database_size_aggregations_2024_09 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE database_size_aggregations_2024_10 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE database_size_aggregations_2024_11 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE database_size_aggregations_2024_12 PARTITION OF database_size_aggregations FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

-- 2025年
CREATE TABLE database_size_aggregations_2025_01 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE database_size_aggregations_2025_02 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE database_size_aggregations_2025_03 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE database_size_aggregations_2025_04 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE database_size_aggregations_2025_05 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE database_size_aggregations_2025_06 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE database_size_aggregations_2025_07 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE database_size_aggregations_2025_08 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE database_size_aggregations_2025_09 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE database_size_aggregations_2025_10 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE database_size_aggregations_2025_11 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE database_size_aggregations_2025_12 PARTITION OF database_size_aggregations FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- 2026年（未来3个月）
CREATE TABLE database_size_aggregations_2026_01 PARTITION OF database_size_aggregations FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE database_size_aggregations_2026_02 PARTITION OF database_size_aggregations FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE database_size_aggregations_2026_03 PARTITION OF database_size_aggregations FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- 5. 添加分区注释
COMMENT ON TABLE database_size_aggregations IS '数据库大小聚合统计表（按月分区）';
COMMENT ON TABLE database_size_aggregations_2024_01 IS '聚合表分区 - 2024年1月';
COMMENT ON TABLE database_size_aggregations_2024_02 IS '聚合表分区 - 2024年2月';
COMMENT ON TABLE database_size_aggregations_2024_03 IS '聚合表分区 - 2024年3月';
COMMENT ON TABLE database_size_aggregations_2024_04 IS '聚合表分区 - 2024年4月';
COMMENT ON TABLE database_size_aggregations_2024_05 IS '聚合表分区 - 2024年5月';
COMMENT ON TABLE database_size_aggregations_2024_06 IS '聚合表分区 - 2024年6月';
COMMENT ON TABLE database_size_aggregations_2024_07 IS '聚合表分区 - 2024年7月';
COMMENT ON TABLE database_size_aggregations_2024_08 IS '聚合表分区 - 2024年8月';
COMMENT ON TABLE database_size_aggregations_2024_09 IS '聚合表分区 - 2024年9月';
COMMENT ON TABLE database_size_aggregations_2024_10 IS '聚合表分区 - 2024年10月';
COMMENT ON TABLE database_size_aggregations_2024_11 IS '聚合表分区 - 2024年11月';
COMMENT ON TABLE database_size_aggregations_2024_12 IS '聚合表分区 - 2024年12月';

COMMENT ON TABLE database_size_aggregations_2025_01 IS '聚合表分区 - 2025年1月';
COMMENT ON TABLE database_size_aggregations_2025_02 IS '聚合表分区 - 2025年2月';
COMMENT ON TABLE database_size_aggregations_2025_03 IS '聚合表分区 - 2025年3月';
COMMENT ON TABLE database_size_aggregations_2025_04 IS '聚合表分区 - 2025年4月';
COMMENT ON TABLE database_size_aggregations_2025_05 IS '聚合表分区 - 2025年5月';
COMMENT ON TABLE database_size_aggregations_2025_06 IS '聚合表分区 - 2025年6月';
COMMENT ON TABLE database_size_aggregations_2025_07 IS '聚合表分区 - 2025年7月';
COMMENT ON TABLE database_size_aggregations_2025_08 IS '聚合表分区 - 2025年8月';
COMMENT ON TABLE database_size_aggregations_2025_09 IS '聚合表分区 - 2025年9月';
COMMENT ON TABLE database_size_aggregations_2025_10 IS '聚合表分区 - 2025年10月';
COMMENT ON TABLE database_size_aggregations_2025_11 IS '聚合表分区 - 2025年11月';
COMMENT ON TABLE database_size_aggregations_2025_12 IS '聚合表分区 - 2025年12月';

COMMENT ON TABLE database_size_aggregations_2026_01 IS '聚合表分区 - 2026年1月';
COMMENT ON TABLE database_size_aggregations_2026_02 IS '聚合表分区 - 2026年2月';
COMMENT ON TABLE database_size_aggregations_2026_03 IS '聚合表分区 - 2026年3月';

-- 6. 为每个分区创建索引
-- 2024年分区索引
CREATE INDEX idx_database_size_aggregations_2024_01_instance_db ON database_size_aggregations_2024_01 (instance_id, database_name);
CREATE INDEX idx_database_size_aggregations_2024_01_period ON database_size_aggregations_2024_01 (period_start, period_end);
CREATE INDEX idx_database_size_aggregations_2024_01_type ON database_size_aggregations_2024_01 (period_type, period_start);

-- 2025年分区索引
CREATE INDEX idx_database_size_aggregations_2025_01_instance_db ON database_size_aggregations_2025_01 (instance_id, database_name);
CREATE INDEX idx_database_size_aggregations_2025_01_period ON database_size_aggregations_2025_01 (period_start, period_end);
CREATE INDEX idx_database_size_aggregations_2025_01_type ON database_size_aggregations_2025_01 (period_type, period_start);

-- 2026年分区索引
CREATE INDEX idx_database_size_aggregations_2026_01_instance_db ON database_size_aggregations_2026_01 (instance_id, database_name);
CREATE INDEX idx_database_size_aggregations_2026_01_period ON database_size_aggregations_2026_01 (period_start, period_end);
CREATE INDEX idx_database_size_aggregations_2026_01_type ON database_size_aggregations_2026_01 (period_type, period_start);

-- 7. 验证分区表创建
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename LIKE 'database_size_aggregations%'
ORDER BY tablename;

-- 完成提示
SELECT 'database_size_aggregations 表已成功转换为分区表！' as message,
       '所有历史分区和未来3个月的分区已创建' as description,
       NOW() as completed_at;